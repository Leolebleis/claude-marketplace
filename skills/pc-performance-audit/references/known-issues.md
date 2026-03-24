# Known Issues Pattern Catalog

Detection patterns, impact ratings, and fix commands for common Windows PC performance issues.

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
