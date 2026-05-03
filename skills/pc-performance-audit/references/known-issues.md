# Known Issues Pattern Catalog

Detection patterns, impact ratings, and fix commands for common Windows PC performance issues.

---

# Diagnostic Traps & Gotchas

**Read this section BEFORE forming hypotheses.** Each entry is a trap that produces false readings or wasted debugging time.

## WMI `MaxClockSpeed` Returns Rated Clock, NOT Boost

`Win32_Processor.MaxClockSpeed` and `wmic cpu get MaxClockSpeed` return the SMBIOS rated/base speed, NOT actual boost frequency. Reading `CurrentClockSpeed = MaxClockSpeed = 3300 MHz` on an i7-11370H (whose real single-core boost is 4.8 GHz) does NOT mean boost is locked — it means WMI cannot tell you the live frequency. Same trap on most Intel and AMD laptop CPUs.

**Always verify CPU boost via PerfMon (locale-aware names):**
- `\Processor Information(_Total)\% Processor Performance` — values >100 = boosting (e.g. 110 = 10% above base)
- `\Processor Information(_Total)\Processor Frequency` — actual MHz
- `\Processor Information(_Total)\% Performance Limit` — 100 = no Windows-level cap
- `\Processor Information(_Total)\Performance Limit Flags` — bitfield identifying which limit is firing (PROCHOT/PL1/PL2/Thermal/EDP). Value 0 = nothing throttling.

Per-core variant: `\Processor Information(*)\Pourcentage de performances du processeur` (or English equivalent), exclude `_Total`.

If Performance Limit Flags = 0 and % Processor Performance > 100, the CPU is boosting fine. **Don't chase Intel DTT / DPTF throttle theories** without this evidence first.

## PerfMon Counter Names Are Localized

On non-English Windows, PerfMon counter sets and counter names are translated. Examples for French:

| English | French |
|---|---|
| `\Processor Information(*)\Processor Frequency` | `\Informations sur le processeur(*)\Fréquence du processeur` |
| `\Processor Information(*)\% Processor Performance` | `\Informations sur le processeur(*)\Pourcentage de performances du processeur` |
| `\Processor Information(*)\Performance Limit Flags` | `\Informations sur le processeur(*)\Indicateurs de limite de performances` |
| `\Processor(*)\% Processor Time` | `\Processeur(*)\% temps processeur` (varies — sometimes `Pourcentage du temps processeur`) |

**Discovery pattern:** `(Get-Counter -ListSet *).CounterSetName` returns localized names. Filter by `-match` against translation candidates (e.g. `'rocesseur|rocessor'`), then enumerate `.Counter` to find the localized counter you need. Build queries dynamically rather than hardcoding English names.

A single failing counter in a parallel batch (exit 1) cancels the whole batch. Run counter queries one at a time or wrap in `try/catch`.

## Built-in Windows 11 `sudo` Doesn't Work Over SSH

`sudo <cmd>` over an OpenSSH session returns "You are not authorized to run sudo" / "Vous n'êtes pas autorisé à exécuter sudo" even for local administrators. Reason: UAC elevation requires an interactive desktop to display the consent prompt; SSH is non-interactive.

**Fix:** Have the user install `gsudo` once on the target: `winget install gerardog.gsudo`. It uses a service to pipe elevation through to non-interactive sessions. All admin commands then work via `gsudo <cmd>`.

`gsudo` itself needs admin to install — chicken-and-egg. The user must run `winget install gerardog.gsudo` from an admin PowerShell on the target machine (right-click Start → Terminal (Administrator)).

## Per-app GPU Preference Lives in Registry, Not NVIDIA Control Panel

Since Win10 20H1, **Windows Graphics Settings overrides NVCP.** Setting "High Performance" in NVIDIA Control Panel alone may not apply if the registry key is unset or contradicts.

**Source of truth:** `HKCU\Software\Microsoft\DirectX\UserGpuPreferences`, format `GpuPreference=2;` per full-exe-path value (1 = power saving / iGPU, 2 = high perf / dGPU). An entry like `AppStatus=4096` means the app has not been explicitly assigned and Windows defaults to iGPU on Optimus laptops.

**Set for an app:**
```
reg add "HKCU\Software\Microsoft\DirectX\UserGpuPreferences" /v "<full exe path>" /t REG_SZ /d "GpuPreference=2;" /f
```

For UE games, the target is usually the `*-Win64-Shipping.exe` under `<game>\Binaries\Win64\`, NOT the launcher exe.

## "GPU 70-90% util but FPS is mid" = Render Thread Bottleneck

Specific signature for UE4/UE5 on small CPUs (4c/8t H35 chips, older 6-core laptops). UE's render thread is single-threaded but bounces across cores rapidly, so per-core load looks "balanced" (e.g. 60% on top core, 30-40% on others) — total CPU% looks low (40-50%) yet the game IS CPU-limited. Won't show as a single core pegged at 100%.

**Diagnosis:** Use the in-game `stat unit` UE console command — shows `Game / Draw / GPU` thread times in ms. The largest number names the bottleneck. If `Draw` >> `GPU`, render thread is the limiter — no amount of GPU side tweaks will help.

**Important corollary:** On a 4-core CPU (i7-11370H, i7-11375H), UE5 Lumen+Nanite games hit a foundational hardware ceiling regardless of how aggressively the system is tuned. The skill should call this out when auditing this CPU class for UE5 titles, rather than chase tweaks that won't move the needle.

## `Get-WindowsDriver -Online` Misses DriverStore Duplicates

`Get-WindowsDriver -Online | Group-Object OriginalFileName | Where-Object Count -gt 1` returns 0 results even when DriverStore obviously has multiple versions of the same driver. Reason: Windows can have multiple FileRepository folders for the same source INF (different package hashes, different metadata) that the cmdlet groups separately.

**Better duplicate scan via folder pattern:**
```powershell
Get-ChildItem 'C:\Windows\System32\DriverStore\FileRepository' -Directory |
  Group-Object { ($_.Name -split '\.inf_')[0] + '.inf' } |
  Where-Object Count -gt 1
```

Then map back to `oemNN.inf` via `pnputil /enum-drivers` for safe deletion with `pnputil /delete-driver oemNN.inf /uninstall` (NEVER `/force` blindly).

## SystemRestore is Throttled to One Point per 24h

Calling `Checkpoint-Computer` more than once per 24h silently no-ops by default. The skill needs to override before creating a safety-net restore point during an audit:

```powershell
New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore' -Name 'SystemRestorePointCreationFrequency' -Value 0 -PropertyType DWord -Force | Out-Null
Checkpoint-Computer -Description 'Pre-audit safety' -RestorePointType 'MODIFY_SETTINGS'
```

`Get-ComputerRestorePoint` lists existing points to verify creation succeeded.

## Use PowerShell `-EncodedCommand` for Complex Remote Scripts

SSH + cmd + PowerShell quoting with `$variables`, nested quotes, and special chars is a nightmare — backslashes get eaten, `$` gets interpreted by bash, French locale outputs garble. Encode the script locally to UTF-16LE base64 and ship it as a single argument:

```powershell
$script = @'
... your multi-line script with $vars and "quotes" ...
'@
$encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($script))
```

Then run: `ssh host "gsudo powershell -EncodedCommand <base64>"`. Sidesteps all escaping problems.

Note: response from `Invoke-CimMethod` over SSH gets wrapped in CLIXML tags — the actual `Write-Host` output is interleaved but readable.

## `findstr` and `where` Return Exit 1 on No Match — Cancels Parallel Batches

In a parallel batch of SSH commands, a single `findstr /I windrose` (or `where nvidia-smi`) returning exit 1 because the search produced no results will cancel ALL other commands in the batch. Wrap with `& exit 0` or use PowerShell `Where-Object` (returns 0 even if empty).

## DLAA in DLSS-Supporting Games is NOT an Upscaler

`UpscalerQuality=DLAA` renders at the panel's NATIVE resolution and uses DLSS only for anti-aliasing — it ignores the game's resolution scale settings entirely. If a player has all `sg.X=0` (lowest quality) but still gets low FPS, check `UpscalerQuality` in `GameUserSettings.ini` first — DLAA is a silent FPS killer that overrides every quality reduction.

For low-end GPUs: `UpscalerQuality=Performance` or `Quality` to enable real upscaling. For high-end GPUs at 144Hz monitors with FrameGen: DLAA is fine.

---

# Issue Pattern Catalog

## Power Plan on Balanced

**Detection:** `powercfg /getactivescheme` returns a GUID that is NOT the "High Performance" or "Ultimate Performance" plan. The plan name varies by OS language (e.g., "Balanced", "Utilisation normale", "Ausgeglichen").

**Impact:** CRITICAL — CPU stays at base clock even under heavy load. On laptops this can mean 40-60% less single-thread performance. Desktops are less affected but still lose boost headroom.

**Why it happens:** Windows defaults to Balanced. On laptops, users often confuse the OEM fan/performance profile (keyboard shortcut or vendor software) with the Windows power plan — they're independent settings.

**Apply:**
```bash
# First find the performance plan GUID
"powercfg /list"
# Then activate it (common GUID for "High Performance"):
"powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
# Or "Ultimate Performance" if available:
"powercfg /setactive e9a42b02-d5df-448d-aa00-03f14749eb61"
# Note: GUIDs vary by system — always check /list first
```

**Verify:** `powercfg /getactivescheme` — should show performance plan active.

**Rollback:** `powercfg /setactive <original-GUID>`

---

## Games on HDD Instead of SSD

**Detection:** Cross-reference `wmic diskdrive` (identify which disk is SSD vs HDD by model — look for "SSD", "NVMe", or known SSD model names like Samsung MZ*, WD SN*, etc. Seagate ST* and WD WD10* are usually HDDs) with `wmic logicaldisk` (drive letters) and Steam game locations.

**Impact:** HIGH — HDD sequential reads ~100-150 MB/s vs NVMe SSD ~3500 MB/s. Affects map load times, texture streaming, and stutter during gameplay. Swap/page file on HDD makes RAM pressure even worse.

**Fix:** Can only be done by the user through Steam (Properties > Installed Files > Move Install Folder). Calculate if SSD has enough free space for the game.

---

## Nahimic (OEM Audio Bloatware)

**Detection:** `sc query NahimicService` returns RUNNING. Typically 5 processes: Nahimic3.exe, NahimicSvc64.exe, NahimicSvc32.exe, nahimicNotifSys.exe, NahimicAPO4Volume.exe. Total ~70-80 MB.

**Impact:** HIGH — Known to cause DPC latency spikes and microstutters. Ships on MSI, Lenovo, Dell, and other OEM systems. The audio "3D surround" processing hooks into the Windows audio pipeline and interferes with game audio timing. Disabling it actually improves audio quality for real audio production work.

**Apply:**
```bash
"sc stop NahimicService & sc config NahimicService start=disabled & taskkill /F /IM Nahimic3.exe /IM NahimicSvc64.exe /IM NahimicSvc32.exe /IM nahimicNotifSys.exe /IM NahimicAPO4Volume.exe"
```

**Verify:** `sc query NahimicService` → STATE: 1 STOPPED. `tasklist | findstr /I nahimic` → no output.

**Rollback:** `sc config NahimicService start=auto` + reboot.

**Note:** Audio continues working through Realtek driver. Only the fake surround effect is lost.

---

## Game DVR / Xbox Game Bar

**Detection:** `reg query "HKCU\System\GameConfigStore" /v GameDVR_Enabled` returns `0x1`. Processes: GameBar.exe, GameBarFTServer.exe, XboxGameBarWidgets.exe — typically 200-300 MB combined.

**Impact:** HIGH — Hooks into the render pipeline for background recording capability. Causes 5-10% FPS loss and microstutters even when not actively recording.

**Apply:**
```bash
"reg add \"HKCU\System\GameConfigStore\" /v GameDVR_Enabled /t REG_DWORD /d 0 /f & reg add \"HKCU\Software\Microsoft\GameBar\" /v AllowAutoGameMode /t REG_DWORD /d 1 /f & reg add \"HKCU\Software\Microsoft\GameBar\" /v AutoGameModeEnabled /t REG_DWORD /d 1 /f & reg add \"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR\" /v AppCaptureEnabled /t REG_DWORD /d 0 /f"
```

**Verify:** `reg query "HKCU\System\GameConfigStore" /v GameDVR_Enabled` → `0x0`

**Rollback:** `reg add "HKCU\System\GameConfigStore" /v GameDVR_Enabled /t REG_DWORD /d 1 /f & reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR" /v AppCaptureEnabled /t REG_DWORD /d 1 /f`

**Note:** Full effect requires reboot. Processes persist until then but hooks are neutered by registry change. Loses Win+G overlay.

---

## Startup Bloat

**Detection:** `Get-CimInstance Win32_StartupCommand` — look for programs that aren't needed at boot. Common offenders:

| Category | Examples |
|----------|----------|
| Music/media | Spotify, iTunes |
| Game launchers | Epic Games, GOG Galaxy, Battle.net |
| Browsers | CCleaner Browser, Opera GX |
| Torrent clients | uTorrent, qBittorrent |
| Updaters | Google Updater, Adobe Updater |
| Audio production | Waves servers, Overbridge, Softube, Ableton panels |
| Cloud storage | OneDrive (if not used) |

**Impact:** MEDIUM — Each saves 30-200 MB at boot. Cumulative effect of 5-10 disabled entries is 500-1000 MB freed.

**Apply (per entry):**
```bash
"reg add \"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run\" /v \"<ENTRY_NAME>\" /t REG_BINARY /d 0300000000000000000000000000000000 /f"
```
The `03` prefix means disabled. `02` means enabled.

**Verify:** `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" /v "<ENTRY_NAME>"` — should show `03...` prefix.

**Rollback (per entry):**
```bash
"reg add \"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run\" /v \"<ENTRY_NAME>\" /t REG_BINARY /d 0200000000000000000000000000000000 /f"
```

**Important:** Always ask which programs the user actually needs at boot. Common keepers: Steam, Discord, game anti-cheats (FACEIT, Vanguard), peripheral software (Logitech, Razer). Everything else can usually be launched on demand.

---

## DiagTrack (Windows Telemetry)

**Detection:** `sc query DiagTrack` → RUNNING, StartType: Automatic.

**Impact:** MEDIUM — Background telemetry doing I/O and CPU work. Worse on systems with HDDs since it writes logs to disk.

**Apply:** `sc stop DiagTrack & sc config DiagTrack start=disabled`

**Verify:** `sc query DiagTrack` → STATE: 1 STOPPED

**Rollback:** `sc config DiagTrack start=auto & net start DiagTrack`

---

## NVIDIA GeForce Experience Overlay

**Detection:** `tasklist | findstr /I "NVIDIA Overlay"` — typically 3-5 processes, 300-500 MB total. Also check `nvcontainer.exe` processes.

**Impact:** MEDIUM — Injects into game render pipeline similarly to Game DVR. Significant memory footprint for overlay functionality most gamers don't use.

**Fix:** Must be done by user: GeForce Experience > Settings > General > In-Game Overlay OFF. Alternative: uninstall GFE entirely and install driver standalone from nvidia.com.

**Verify:** `tasklist | findstr /I "NVIDIA Overlay"` — fewer or no processes.

---

## Windows Search Indexer

**Detection:** `sc query WSearch` → RUNNING.

**Impact:** LOW-MEDIUM — Background disk I/O for indexing. Mainly matters on HDD systems. Once games move to SSD, impact is negligible.

**Apply:** `sc stop WSearch & sc config WSearch start=demand`

**Verify:** `sc query WSearch` → STATE: 1 STOPPED

**Rollback:** `sc config WSearch start=auto & net start WSearch`

**Note:** Search still works, just slower on first query until service auto-starts.

---

## High Swap / Page File Usage

**Detection:** Compare `FreePhysicalMemory` with `TotalVisibleMemorySize` from `wmic OS`. Check `Win32_PageFileUsage` for current and peak swap usage. Swap > 1 GB active during gaming = problem. Also check WHERE the page file lives — `Get-CimInstance Win32_PageFileUsage | Select-Object Name` — and how much free space that drive has.

**Impact:** Varies — Causes random hitches when pages swap to/from disk. Especially bad if page file is on a drive with low free space (can't grow) or on an HDD. A page file on a nearly-full drive can cause multi-second freezes when Windows can't allocate swap fast enough.

**Fixes:**
1. Move page file to the drive with the most free space (if it's on a cramped OS drive)
2. Reduce memory pressure (disable bloat, reduce game settings)
3. Long-term: RAM upgrade

**Moving the page file via PowerShell (requires admin):**
```powershell
# Save as .ps1 and run with: gsudo powershell -ExecutionPolicy Bypass -File script.ps1

# Disable automatic management
$cs = Get-CimInstance Win32_ComputerSystem
$cs | Set-CimInstance -Property @{AutomaticManagedPagefile = $false}

# Remove page file from old drive (replace <OLD> with actual drive letter)
$pf = Get-CimInstance -Query "SELECT * FROM Win32_PageFileSetting WHERE Name = '<OLD>:\\pagefile.sys'"
if ($pf) { $pf | Remove-CimInstance }

# Create on new drive (replace <NEW> with target drive letter)
# Must create first, then set size separately — New-CimInstance has a type bug with InitialSize
New-CimInstance -ClassName Win32_PageFileSetting -Property @{Name = '<NEW>:\pagefile.sys'}
$pf = Get-CimInstance -Query "SELECT * FROM Win32_PageFileSetting WHERE Name = '<NEW>:\\pagefile.sys'"
$pf | Set-CimInstance -Property @{InitialSize = [uint32]8192; MaximumSize = [uint32]8192}
```

**Sizing:** For 16 GB RAM: 8 GB page file. For 32 GB RAM: 8 GB. Fixed size (min=max) is better on SSDs — avoids constant resize writes.

**Verify:** `Get-CimInstance Win32_PageFileSetting | Format-List Name, InitialSize, MaximumSize`

**Reboot required** for changes to take effect.

**Rollback:**
```powershell
# Re-enable automatic management
$cs = Get-CimInstance Win32_ComputerSystem
$cs | Set-CimInstance -Property @{AutomaticManagedPagefile = $true}
# Reboot — Windows recreates system-managed page file
```

---

## SysMain (Superfetch)

**Detection:** `sc query SysMain` → RUNNING.

**Impact:** LOW — Prefetches frequently used apps into RAM. Can cause disk I/O spikes on HDDs. On SSD-only systems, generally harmless. On mixed SSD+HDD systems, can cause HDD thrashing.

**Apply:** `sc stop SysMain & sc config SysMain start=disabled`

**Rollback:** `sc config SysMain start=auto & net start SysMain`

---

## Minecraft JVM Flags

**Detection:** Check `wmic process where "name='javaw.exe'" get CommandLine`.

**Known bad patterns:**
| Pattern | Problem |
|---------|---------|
| ZGC on client | FPS penalty vs Shenandoah/G1GC |
| Aikar's flags on client | Server-tuned G1GC, causes client stutters |
| `-Xmx` much larger than needed | Longer GC pauses |
| `-Xms` != `-Xmx` | Heap resizing causes pauses |
| Missing `-XX:+AlwaysPreTouch` | Page faults on first access |

**Recommended client GC (Shenandoah):**
```
-XX:+UseShenandoahGC -XX:ShenandoahGCMode=iu -XX:ShenandoahGuaranteedGCInterval=1000000 -XX:AllocatePrefetchStyle=1
```

**Recommended client GC (G1GC, Java 21):**
```
-XX:+UseG1GC -XX:MaxGCPauseMillis=37 -XX:G1HeapRegionSize=16M -XX:G1NewSizePercent=23 -XX:G1ReservePercent=20 -XX:SurvivorRatio=32 -XX:G1MixedGCCountTarget=3 -XX:G1HeapWastePercent=20 -XX:InitiatingHeapOccupancyPercent=10 -XX:G1RSetUpdatingPauseTimePercent=0 -XX:MaxTenuringThreshold=1 -XX:G1SATBBufferEnqueueingThresholdPercent=30 -XX:G1ConcMarkStepDurationMillis=5.0 -XX:GCTimeRatio=99
```

**Heap sizing:** `-Xms` = `-Xmx`. Use 4-8 GB for modded, no more than needed.

---

## Known Software Conflicts

| Software | Issue |
|----------|-------|
| RivaTuner (RTSS) v7.3.3 or older | Extreme FPS drops with Sodium |
| ASUS GPU Tweak III | Injects into Java process, severe slowdown |
| Malwarebytes Anti-Ransomware | Conflicts with FACEIT anti-cheat |
| OptiFine | Conflicts with Sodium, outdated rendering |

---

## HVCI / Memory Integrity (Windows 11 24H2)

**Detection:**
```powershell
(Get-CimInstance -Namespace root/Microsoft/Windows/DeviceGuard -ClassName Win32_DeviceGuard).SecurityServicesRunning
```
Result containing `2` = HVCI is active. Win11 24H2 default-enables HVCI on supported hardware.

**Impact:** HIGH for gaming on weaker CPUs — 5-15% throughput tax on every kernel transition (interrupts, syscalls, GPU command submissions). Disproportionately bad for UE5 games on 4-core CPUs because of UE's command-buffer churn.

**Trap:** The registry workaround (`HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity\Enabled = 0`) does NOT survive reboot on 24H2. The marker is `WasEnabledBy = 2` in that key — Windows auto-re-enabled it via default policy.

**Three ways to actually disable:**

1. **GUI toggle (preferred, persists across reboots, requires user's hands):**
   Settings → Windows Security → Device Security → Core Isolation → Memory Integrity OFF → reboot. Toggle may be hidden or greyed if Windows detected incompatible drivers; click "Review incompatible drivers" if present.

2. **`bcdedit` nuclear option (works when GUI toggle is hidden/locked):**
   ```
   gsudo bcdedit /set hypervisorlaunchtype off
   ```
   Reboot. Disables the entire VBS stack at boot.

   **Trade-off:** also disables Hyper-V, WSL2, Docker Desktop, Windows Sandbox.

3. **Disable Smart App Control** (when SAC is forcing MI to stay on):
   Settings → Privacy & Security → Windows Security → App & browser control → Smart App Control → Off.

   **WARNING: ONE-WAY** — once SAC is off, can only re-enable via Windows reinstall.

**Verify after reboot:**
```powershell
(Get-CimInstance -Namespace root/Microsoft/Windows/DeviceGuard -ClassName Win32_DeviceGuard).SecurityServicesRunning
```
Should not contain `2`.

**Rollback:** GUI toggle back on, OR `gsudo bcdedit /set hypervisorlaunchtype auto` + reboot.

---

## ASUS Armoury Crate Modes (WMI-Scriptable)

ASUS ROG/TUF laptops expose performance modes via WMI — same interface that G-Helper drives. Skill should use this rather than asking the user to press FN+F5 or open the Armoury Crate UI.

**WMI class:** `AsusAtkWmi_WMNB` in `root/wmi`.
**Methods:** `DSTS` (read), `DEVS` (write).
**Verify class is exposed** (most ASUS gaming laptops have it):
```powershell
Get-CimClass -Namespace root/wmi | Where-Object CimClassName -match 'AsusAtk'
```

**Device IDs:**
- `0x00120075` — Performance mode

**Mode values for `0x00120075`:**
- 0 = Windows
- 1 = Silent
- 2 = Performance
- 3 = Turbo
- 4 = Manual

**Read current mode:**
```powershell
$cim = Get-CimInstance -Namespace root/wmi -ClassName AsusAtkWmi_WMNB
$raw = (Invoke-CimMethod -InputObject $cim -MethodName DSTS -Arguments @{Device_ID=0x00120075}).device_status
$mode = $raw - 65536  # high 16 bits = "supported" flag (0x10000), low 16 = value
```

**Returned field is `device_status` (NOT `Output1` like older docs claim).** Format: high 16 bits = supported flag (`0x10000`), low 16 bits = actual value. Subtract 65536 to get the mode value directly.

**Set mode (e.g. Turbo):**
```powershell
Invoke-CimMethod -InputObject $cim -MethodName DEVS -Arguments @{Device_ID=0x00120075; Control_status=3}
```

**Important:** Armoury Crate firmware mode is INDEPENDENT of Windows power plan. Both must align: Windows plan = High Performance / Ultimate / ASUS Turbo, AND firmware mode = 3 (Turbo). The Windows Power Mode slider (Settings → System → Power) ALSO overrides plan choices — verify `ActiveOverlayAcPowerScheme` is empty in `HKLM\SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes`.

**G-Helper alternative:** If user is interested, suggest replacing Armoury Crate (~4 GB footprint, 20+ background processes) with `seerge/g-helper` (5 MB, single tray app, drives same WMI interface). `winget install seerge.g-helper`. Caveat: don't run both simultaneously — they conflict on ACPI access.

**ASUS service triage** (for cleanup pass):
| KEEP | DISABLE (safe) |
|---|---|
| ArmouryCrateService | AsusAppService |
| ArmouryCrateControlInterface | AsusCertService |
| ASUSOptimization | ASUSSoftwareManager |
| ArmourySocketServer (sched task) | ASUSSwitch |
| AcPowerNotification (sched task) | ASUSSystemAnalysis |
| ASUS Hotplug Controller (sched task) | ASUSSystemDiagnosis |
| | ROG Live Service |

Tray app bloat to disable via `HKCU\...\StartupApproved\Run`: `AsusSoftwareManagerAgent`, `AppActions`, `ArmouryCrate.DenoiseAI` (only if user doesn't use mic noise cancellation in calls).

---

## Optimus Laptop Framebuffer Copy Ceiling (No-MUX)

**Detection:** Laptop has both Intel iGPU + NVIDIA dGPU but no MUX switch. Common on FX516PR (TUF Dash F15), Strix G15 11th-gen, many Optimus-only Strix/TUF/Zephyrus models. Confirm via `Get-CimInstance Win32_VideoController` showing both adapters AND no `MuxSwitch` setting in Armoury Crate.

**Impact:** ~10-17% FPS loss on dGPU rendering vs MUX-enabled (Anandtech's original Optimus testing, repeated by Jarrod's Tech, multiple ASUS forum threads). Mechanism: dGPU renders frame → frame copies over PCIe to iGPU → iGPU presents to internal panel. The copy adds latency and bandwidth pressure regardless of dGPU power.

**Bypass (no software fix exists):** Plug an external monitor into the **HDMI port** on the laptop. On most ASUS Strix/TUF laptops, HDMI is wired directly to the dGPU and bypasses the iGPU framebuffer copy entirely. USB-C / Thunderbolt typically routes through iGPU. Game on the external display = full dGPU performance.

**Hardware ceiling for the i7-11370H/i7-11375H + RTX 30 Mobile combo:** Foundationally CPU-bottlenecked for UE5 Lumen+Nanite titles. Multiple expert reviews flagged this at launch:
- Notebookcheck FX516PR review titled **"Ampere with one foot on the brake"**
- TechSpot i7-11370H review titled **"Quad-Cores Aren't Enough in 2021"**
- Ultrabookreview FX516PR identified CPU bottleneck in Cyberpunk 2077, Far Cry 5, RDR2

When auditing this hardware class for UE5 games, set expectations honestly: 40-50 FPS at low settings on this combo IS the hardware ceiling, not a tuning failure. For comparison, a Steam Deck (15W APU, 1/5 the GPU power) gets 30-40 FPS in Windrose at low settings — same range as a Mobile 3070 here, because both are render-thread CPU-bound.

---

## Discord Go Live / Screen Share GPU Tax

**Detection:**
```powershell
Get-Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -MaxSamples 2
```
Look for Discord with sustained ~20-30% on `engtype_videoencode` (NVENC). If game is also showing 3D engine load, both processes are on the same GPU and Discord is encoding the stream output.

**Impact:** ~15-20% FPS loss in many configs. Discord uses the GPU's video encoder for the Go Live stream, competing with the game.

**Fix:** User stops the Discord Go Live stream / screen share (clicks Stop in Discord). No software way to do this remotely — needs user's hands.

**Verify:** Re-run the GPU engine counter — Discord `videoencode` should drop to 0.

---

## TiWorker / Windows Update Killing Game Perf

**Detection:**
```powershell
Get-Process TiWorker -ErrorAction SilentlyContinue
Get-Service wuauserv, TrustedInstaller
```
TiWorker active with high RAM (>500 MB) and accumulating CPU time = Windows Update is installing pending updates, hammering disk I/O. Particularly common after a reboot where queued updates start installing.

**Impact:** Game gets disk-stalled — frametime spikes, FPS drops 30-50%, low GPU utilization despite headroom on CPU/GPU.

**Trap — what NOT to do:**
- **DO NOT kill TiWorker, TrustedInstaller, or msiserver mid-install.** Mid-install termination = corrupted component store. Recovery requires `dism /Online /Cleanup-Image /RestoreHealth`, possibly worse (feature update reinstall, in-place upgrade).

**Safe mitigation:**
```
gsudo sc stop wuauserv
```
Stops NEW install jobs from queuing. Does NOT abort current TiWorker (it's spawned by TrustedInstaller, runs independently). Wait 5-10 min for current job to finish naturally — TiWorker RAM dropping (e.g. 1 GB → 200 MB) signals it's wrapping up.

**Long-term fix:** Settings → Windows Update → Pause for 1 week, OR set Active Hours to cover gaming time, OR Group Policy "Notify download, notify install" so updates wait for confirmation.

**Restart later:** `gsudo sc start wuauserv` or just reboot.

---

## HAGS (Hardware-Accelerated GPU Scheduling) on RTX 30+/40+/50

**Detection:**
```powershell
(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers' -Name HwSchMode -ErrorAction SilentlyContinue).HwSchMode
```
Value 2 = on, 1 = off, missing = default off.

**Impact / 2026 consensus:** Should be ON for RTX 30-series and newer, especially when DLSS Frame Generation is in use (FG explicitly requires HAGS for best results on RTX 40+/50). Net-zero or small positive impact in most non-FG titles. Reserves a small chunk of VRAM (~500 MB).

**Apply:**
```
gsudo reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 2 /f
```
Reboot to activate.

**Rollback:**
```
gsudo reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 1 /f
```
Reboot.

**Optimus caveat:** On no-MUX Optimus laptops, HAGS interaction with the dGPU→iGPU framebuffer copy can occasionally regress perf in specific games. If FPS drops after enabling HAGS on an Optimus laptop, toggle off and re-test.

---

## NVIDIA App "Game Filters and Photo Mode" Tax

**Detection:** NVIDIA App is installed (replaces GeForce Experience). The "Game Filters and Photo Mode" feature is enabled by default.

**Impact:** Tom's Hardware tested + NVIDIA officially acknowledged: up to 15% FPS loss in games due to filter injection layer loaded into every render pipeline, even when filters aren't being used. NVIDIA App also uses 200-300 MB at idle vs GeForce Experience's 80-150 MB.

**Fix (user's hands):** NVIDIA App → Settings → uncheck "Enable Game Filters and Photo Mode". Or uninstall NVIDIA App entirely and use bare driver via [nvcleanstall](https://www.techpowerup.com/nvcleanstall/) — saves ~250 MB and removes the filter layer completely.

**Verify:** `tasklist | findstr /I "NVIDIA App Container"` — should be fewer/no processes after disabling.

---

## NVIDIA Driver KB5066835 Regression (Win11 24H2/25H2)

**Detection:** Windows 11 24H2 or 25H2 build, NVIDIA driver version older than 581.94. KB5066835 (Oct 2025) caused up to 50% FPS drops on NVIDIA cards.

**Driver version decoder for `Get-CimInstance Win32_VideoController`:** Format `32.0.15.NNNNN` — public version is the last 5 digits as `WWN.NN`. Example `32.0.15.9636` → `596.36`.

**Fix:** Install NVIDIA Hotfix Driver 581.94 or any newer release. Direct download:
```
https://international.download.nvidia.com/Windows/581.94hf/581.94-desktop-notebook-win10-win11-64bit-international-dch.hf.exe
```

Most current Game Ready drivers (2026+) include the fix.
