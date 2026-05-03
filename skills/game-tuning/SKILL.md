---
name: game-tuning
description: Use when a user wants to optimize specific games (FPS, latency, frame pacing, screen tearing) on Windows — per-game NVCP profiles, DLSS/Frame Gen setup, Reflex, V-Sync + G-Sync stack, launch options, in-game video settings. Distinct from system-wide audit (use pc-performance-audit for HVCI/HAGS/Armoury/disk).
---

# Game Tuning

Per-game optimization on Windows: G-Sync stack, DLSS/Frame Gen, Reflex, per-app NVCP profiles, launch options, in-game settings. Pairs with `leo-skills:pc-performance-audit` (which handles system-level concerns: HVCI, HAGS, services, ASUS bloat, disk).

**Core principle:** The Blur Busters G-Sync 101 stack (G-Sync ON + V-Sync ON in NVCP + FPS cap at refresh−3 + Reflex in-game) is the canonical zero-tearing low-latency config for any G-Sync-compatible setup in 2026. Most "FPS tweaks" online are CSGO-era folklore that's harmful in 2026 driver branches.

## When to Use

- User reports screen tearing despite G-Sync-capable monitor
- "First-round stutter" / brief stutters after alt-tab (P-state oscillation)
- DLSS / Frame Generation feels slow or wrong
- User asks about CS2 launch options or in-game settings
- Any "is my [game] configured right?" question
- Setting up a fresh GPU/monitor for gaming

**Don't use for:** system-wide audit (memory, services, disk, bloatware) — that's `pc-performance-audit`. HVCI / HAGS toggle, Armoury Crate, Optimus dGPU framebuffer are also pc-performance-audit territory.

## Step 1: Detect rig class

```powershell
# Monitor refresh + GPU model
Get-CimInstance Win32_VideoController | Select-Object Name, CurrentRefreshRate

# RAM speed (use ConfiguredClockSpeed, NOT Speed — Speed lies, returns SPD rated)
Get-CimInstance Win32_PhysicalMemory | Format-Table Manufacturer, PartNumber, Speed, ConfiguredClockSpeed

# Per-app GPU preferences (Win10 20H1+ overrides NVCP)
Get-ItemProperty 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' -ErrorAction SilentlyContinue
```

Note the actual refresh rate of the gaming monitor (could differ from primary). Cap target = refresh − 3 (e.g., 144→141, 240→237).

## Step 2: Apply universal G-Sync 101 stack (NVCP global)

Open NVCP → **Manage 3D Settings → Global Settings**. Set:

| Setting | Value | Why |
|---|---|---|
| **Vertical Sync** | **On** | Tear-prevention safety net. Zero latency cost when paired with G-Sync + cap |
| **Max Frame Rate** | **refresh − 3** (e.g., 141 / 237) | Stays inside G-Sync window |
| **Low Latency Mode** | **On** (NOT Ultra) | "Ultra" caps FPS itself at ~refresh−3 and double-caps with manual cap |
| **Shader Cache Size** | **Unlimited** | Massive for UE5 / Lumen / Nanite stutter |
| **Texture Filtering – Quality** | **High Quality** | Modern GPUs have headroom; old "High Performance" advice is from GTX 1060 era |
| **Preferred Refresh Rate** | **Highest available** | Forces monitor's native rate even if game requests 60 |
| **Power Management Mode** | **Normal** (do NOT change) | "Prefer max performance" GLOBALLY is obsolete on Ada/Blackwell. Set per-app instead |

Plus **NVCP → Display → Set up G-SYNC** → "Enable G-SYNC, G-SYNC Compatible" → "Enable for full screen mode" (or windowed if borderless games are common).

**DLSS Override** (NVIDIA App, not NVCP): Settings → Graphics → DLSS Override – Model Presets → click **Recommended** (NOT "Latest" — that label doesn't exist; the option is "Recommended"). This forces older DLSS games to use the modern Transformer model.

## Step 3: Apply per-app NVCP profile for fast-paced / competitive games

NVCP → Program Settings → Add `<game>.exe`:

| Setting | Per-app value | Why |
|---|---|---|
| **Power Management Mode** | **Prefer maximum performance** | Forces P0 — fixes "first round stutter" / alt-tab wakeup hitches |
| **Background Application Max Frame Rate** | **30** or **60** | Stops alt-tabbed game from burning GPU at 1000 FPS in menus |
| Max Frame Rate | inherit global (refresh − 3) | One source of truth — don't double-cap |
| Vertical Sync | inherit global (On) | Same |

For Cyberpunk-class single-player titles, `Background Max Frame Rate = 30` is enough; you don't need Prefer Max Performance unless you see stutters.

## Step 4: Per-app GPU preference (Optimus laptops + multi-GPU)

`HKCU\Software\Microsoft\DirectX\UserGpuPreferences` overrides NVIDIA Control Panel since Win10 20H1. For UE games, target the actual `<game>-Win64-Shipping.exe` under `<game>\Binaries\Win64\` — NOT the launcher exe.

```
reg add "HKCU\Software\Microsoft\DirectX\UserGpuPreferences" /v "<full exe path>" /t REG_SZ /d "GpuPreference=2;" /f
```

Values: `1` = power saving / iGPU, `2` = high performance / dGPU. Entries showing `AppStatus=4096` are unset and default to iGPU on Optimus.

## Step 5: Game-specific cookbook

**For CS2:** see `references/cs2-cookbook.md` — file paths, convars, launch options, in-game settings, pro comparison.

**For UE games (UE4/UE5):**
- DLSS: pick **Quality** at 1080p, **Quality** or **Balanced** at 1440p, **Balanced** or **Performance** at 4K.
- **DLAA renders at NATIVE resolution** — it's NOT an upscaler. If FPS feels low and DLAA is on, that's why.
- Frame Generation: enable if base FPS ≥ 50. Below 50 base, FG adds stutter and latency (frame gen amplifies frametime variance).
- Reflex: always **On + Boost** when game supports it (CS2, Cyberpunk, most UE5 titles do).
- HAGS must be on for FG to work properly (HAGS toggle is in `pc-performance-audit`).
- UE5 + 4-core CPUs (i7-11370H, i7-11375H) hit a foundational render-thread bottleneck — see `pc-performance-audit` Optimus framebuffer ceiling note.
- If GPU at 70-90% util but FPS is mid-range with both CPU and GPU showing headroom, that's the UE5 single-threaded render thread bouncing across cores. Use in-game `stat unit` console command — if `Draw` is the largest number, render thread is the limit.

## Step 6: Common WRONG advice to actively reject

| Bad advice | Why wrong |
|---|---|
| "Set Power Management Mode = Prefer Max Performance globally" | Obsolete on Ada/Blackwell. Heat for nothing. Per-app only. |
| "Low Latency Mode Ultra" (with manual cap) | Ultra imposes its own ~refresh−3 cap → conflicts with manual cap |
| "DLSS Override = Latest" | This option doesn't exist. The label is **"Recommended"**. |
| "fps_max in launch options + NVCP cap" | Stacking caps causes frame pacing artifacts. One source of truth. |
| "Image Sharpening with DLSS Transformer" | Conflicts with DLSS 4 internal sharpening, produces shimmer |
| "FXAA forced from NVCP" | Blurs over modern game AA (TAA, DLAA) |
| "Anisotropic Filtering forced 16x" | Modern engines do AF correctly per-material; forcing causes shimmer |
| "DSR globally" | Old non-AI; use **DLDSR per-app** for older AA-poor games (Skyrim, Witcher 3) only |
| "Prefer maximum performance" power plan + force max GPU | Cargo cult. Disables core parking on idle, no FPS gain on modern CPUs |
| "Disable Memory Integrity for FPS" | Real (~5-15% on weak CPUs) but document tradeoff. See `pc-performance-audit` HVCI section for how (24H2 auto-re-enables; needs GUI toggle or `bcdedit /set hypervisorlaunchtype off`). |

## Step 7: Verification

After changes that touch NVCP DRS profile:
1. Re-export `.nip` from NVIDIA Profile Inspector (PI → Export → save)
2. Diff against pre-change baseline — confirm only intended settings differ from default
3. PI export only includes settings that DIFFER from driver defaults — small file = vanilla config

For CS2 file edits: see cookbook for backup + close-game-first protocol.

## Hardware-specific gotchas

- **Optimus laptops without MUX**: ~10-17% FPS ceiling from dGPU→iGPU framebuffer copy. Bypass: plug external monitor into HDMI port (HDMI typically wired direct to dGPU on ASUS Strix/TUF). Detail in `pc-performance-audit`.
- **DDR5 reading**: WMI `Win32_PhysicalMemory.Speed` returns SPD JEDEC rated speed (e.g., 4800), NOT actual operating speed. Use `ConfiguredClockSpeed` for what RAM is REALLY running at. EXPO/XMP active = ConfiguredClockSpeed > Speed.
- **WMI `MaxClockSpeed`** for CPUs always returns rated/base speed, NOT boost. `CurrentClockSpeed = MaxClockSpeed` is NOT proof of throttling — it's evidence WMI can't tell you. Use PerfMon `\Processor Information(_Total)\% Processor Performance` (>100 = boosting). Detail in `pc-performance-audit`.

## Quick reference: known-good launch options

| Game | Launch options | Notes |
|---|---|---|
| **CS2** (Valve MM) | `-novid -language english` | See cookbook for full FACEIT vs MM matrix |
| **CS2** (FACEIT) | `-novid -language english` | DROP `-allow_third_party_software` for FACEIT (incompatible with FACEIT AC) |
| **Cyberpunk 2077** | (none needed) | Game's launcher handles everything |
| **Generic UE5** | (none needed) | Source 2 / UE5 self-tune |

**Universally OBSOLETE / harmful in 2026:**
- `-high` — causes Win11 24H2 scheduler stutter
- `-tickrate 128` — does nothing in CS2 sub-tick
- `-threads N` — UE/Source 2 self-tune; hardcoding hurts X3D and other modern CPUs
- `-d3d9ex` — DX9 doesn't exist in CS2/UE5
- `-noreflex` — costs 10-35ms latency for ~2% FPS gain
- `-vulkan` on NVIDIA Win11 — DX11 path is faster + Reflex works better

## Common Mistakes

| Mistake | Fix |
|---|---|
| Setting in-game V-Sync ON when NVCP V-Sync is also On | NVCP only — in-game adds latency, breaks G-Sync stack |
| Capping FPS in both NVCP AND in-game | One source. NVCP preferred (more accurate, applied later in pipeline) |
| Forcing Power Mgmt = Max Performance globally | Per-app only. Globally raises temps for nothing on modern GPUs |
| Editing CS2 `.vcfg` while CS2 is open | Game overwrites on exit. Close game first, backup, edit, verify |
| Recommending "DLSS Override = Latest" | Doesn't exist. **"Recommended"** is the option |
| Telling FACEIT user to add `-allow_third_party_software` | FACEIT AC incompatible. Drop the flag for FACEIT play |
| Trusting WMI for CPU/RAM clock readings | `MaxClockSpeed` is base, `Speed` is rated. Use PerfMon and `ConfiguredClockSpeed` |
