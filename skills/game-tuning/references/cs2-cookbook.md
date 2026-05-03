# CS2 Cookbook

CS2-specific optimization. Distilled from a real session with a 5080 / 9800X3D / 144Hz QD-OLED rig. References ProSettings.net, Blur Busters, and pro player configs.

## File locations

| Purpose | Path |
|---|---|
| Video / GPU settings | `<Steam>\userdata\<steamid>\730\local\cfg\cs2_video.txt` |
| Machine convars (fps_max, snd_*, network) | `<Steam>\userdata\<steamid>\730\local\cfg\cs2_machine_convars.vcfg` |
| User convars (crosshair, sensitivity, viewmodel) | `<Steam>\userdata\<steamid>\730\local\cfg\cs2_user_convars_0_slot0.vcfg` |
| Steam libraries enumeration | `C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf` |

To find user steamid: `Get-ChildItem "C:\Program Files (x86)\Steam\userdata" -Directory` — the numeric folder name is the SteamID3.

## ⚠ Edit protocol (ALWAYS)

CS2 owns these files. Editing while CS2 is open → game overwrites changes on exit.

```powershell
# 1. Verify CS2 closed
Get-Process cs2 -ErrorAction SilentlyContinue
# 2. Backup
$cfg = "<Steam>\userdata\<steamid>\730\local\cfg"
$bak = "$cfg\backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory $bak -Force
Copy-Item "$cfg\cs2_video.txt", "$cfg\cs2_machine_convars.vcfg", "$cfg\cs2_user_convars_0_slot0.vcfg" $bak
# 3. Edit
# 4. Verify with grep
```

## Launch options

Steam Library → CS2 → Properties → Launch Options.

```
-novid -language english
```

That's it. Notably **OBSOLETE/HARMFUL** (DO NOT add):

| Flag | Why bad |
|---|---|
| `-high` | Win11 24H2 scheduler hitch (3-5ms frame stutter) |
| `-tickrate 128` | Does nothing — CS2 is sub-tick. Only affects local offline practice. |
| `-threads N` | Source 2 self-tunes. Hardcoding hurts 7800X3D / 9800X3D scheduler. |
| `-d3d9ex` | DX9 doesn't exist in CS2 |
| `-vulkan` on NVIDIA Win11 | DX11 path 5-20% faster + Reflex works better |
| `-noreflex` | Loses 10-35ms latency for ~2% FPS |
| `+fps_max X` in launch | Use NVCP cap as single source of truth |
| `-insecure` | Disables VAC — can't play matchmaking |

**`-allow_third_party_software`** — conditional:
- **Add** if you only play Valve MM and want overlays (RTSS, MSI Afterburner, GeForce Experience overlay) to hook
- **REMOVE** if you play FACEIT — FACEIT Anti-Cheat is incompatible. FACEIT enforces its own Trusted Mode and the flag will be rejected/cause issues.

## In-game video settings (`cs2_video.txt`)

For a high-end rig at 1080p / 144 Hz (image quality + competitive visibility, NOT max-FPS):

| Setting | Convar | Value | Why |
|---|---|---|---|
| Display Mode | `setting.fullscreen` | **1** (exclusive) | Lower input lag than borderless. Pro standard. |
| Resolution | `setting.defaultres` / `defaultresheight` | **1920 x 1080** | Native (some pros use 1280x960 stretched for muscle memory; on native panel use native) |
| Refresh Rate | `setting.refreshrate_numerator` | **144** (or panel native) | |
| In-game V-Sync | `setting.mat_vsync` | **0** | NVCP V-Sync handles it (G-Sync 101 stack). In-game V-Sync would double-buffer. |
| MSAA | `setting.msaa_samples` | **8** | Pro standard (m0nesy, NiKo, donk). 5080-class GPU has headroom. |
| Shadow Quality | `setting.videocfg_shadow_quality` | **3** (High) | Critical info — enemy shadows reveal angles |
| Dynamic Shadows | `setting.videocfg_dynamic_shadows` | **1** | Same reason |
| Texture Detail | `setting.videocfg_texture_detail` | **2-3** (Medium-High) | Preference; pros split |
| **Particle Detail** | `setting.videocfg_particle_detail` | **0** (Low) | **CRITICAL** — High makes smokes thicker, hides enemies inside |
| **Ambient Occlusion** | `setting.videocfg_ao_detail` | **0** (Disabled) | **CRITICAL** — High darkens corners, hides enemy silhouettes |
| HDR | `setting.videocfg_hdr_detail` | **-1** (Quality) | OK |
| FSR | `setting.videocfg_fsr_detail` | **0** (off) | At 1080p on a 5080 — useless |
| **Reflex** | `setting.r_low_latency` | **2** (Enabled+Boost) | Always |
| Aspect Ratio | `setting.aspectratiomode` | **1** (16:9) | |

## Machine convars (`cs2_machine_convars.vcfg`)

| Convar | Value | Why |
|---|---|---|
| `fps_max` | **0** | NVCP caps at refresh−3. Stacking caps causes pacing artifacts. |
| `snd_mixahead` | **0.025** | Default 0.05 too high; **0.001 too aggressive** (causes audio crackle on Win11). 0.025 is sweet spot. |
| `mm_dedicated_search_maxping` | **65** for EU, **50** for US-East, **75** for ANZ/SA | Cuts garbage matchmaking. Default 150 is too permissive. |
| `snd_use_hrtf` | **1** | CS2 spatial audio. Required when Windows Spatial Sound is OFF (which it should be). |
| `cl_interp` | **0** | Sub-tick optimal — server uses your timestamps |
| `cl_interp_ratio` | **1** | Pair with `cl_interp 0` |
| `rate` | **786432** | Max bandwidth (CS2 default; verify) |

These can also be set via in-game console after enabling it (Settings → Game → Enable Developer Console).

## NVCP per-app for `cs2.exe`

Add `cs2.exe` to NVCP → Manage 3D Settings → Program Settings:

- Browse to: `C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\cs2.exe`
- **Power management mode**: **Prefer maximum performance** (per-app, NOT global) — fixes alt-tab P-state hitch
- **Background Application Max Frame Rate**: **30** or **60** (was 0/uncapped) — stops menu burning GPU
- Inherit: V-Sync On, Max Frame Rate (refresh−3), Low Latency Mode On, Texture Filtering High Quality

## Audio — Windows side

⚠ **Disable Windows Spatial Sound** for CS2's audio device:
- Right-click speaker icon → Sound Settings → click your output device → **Spatial sound: Off**
- Verify via PowerShell:
  ```powershell
  $render = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
  Get-ChildItem $render | ForEach-Object {
    $name = (Get-ItemProperty "$($_.PSPath)\Properties").'{a45c254e-df1c-4efd-8020-67d146a850e0},2'
    $spat = (Get-ItemProperty "$($_.PSPath)\FxProperties" -ErrorAction SilentlyContinue).'{a44531ee-5208-4cf2-97ee-fdfe1b0a1c5c},5'
    if ($name) { Write-Host "$name -> spatializer: $($spat -or '<off>')" }
  }
  ```
- Empty Spatializer GUID = OFF ✓. Anything else = ON (Windows Sonic / Atmos / DTS).

CS2's HRTF (`snd_use_hrtf 1`) does spatial processing in-engine. Stacking Windows Sonic on top blurs directional cues — a footstep that should be 3m to your right gets smeared across a 90° arc.

## Pro player sanity check

| Player | Res | MSAA | Shadow | Particle | AO | Reflex |
|---|---|---|---|---|---|---|
| ZywOo | 1280×960 stretched | 4x | High | High | Medium | Enabled |
| donk | 1280×960 stretched | 8x | High | Low | Off | Off |
| NiKo | 1280×960 stretched | 8x | Med-High | Low | Off | On |
| m0nesy | 1280×960 stretched | 8x | High | Low | Off | On |
| **Recommended for high-end native** | **1920×1080** | **8x** | **High** | **Low** | **Off** | **Enabled+Boost** |

Pros use 1280×960 stretched for hitbox-feel muscle memory carried over from CSGO. On a native 1080p panel use native.

## Things to NOT touch (cargo cult from CSGO)

- `mat_queue_mode` — Source 1 only, no-op in CS2
- `cl_forcepreload 1` — disabled in Source 2 years ago
- `cl_disablehtmlmotd 1` — no-op
- `mat_disable_fancy_blending 1` — Source 1 only
- Most `r_*` convars from CSGO guides — renamed/removed/cheat-flagged in CS2
- Mouse polling rate >1000 Hz — CS2 has documented stutter at 4kHz/8kHz on Win11
- Process Lasso CPU pinning on single-CCD chips (7800X3D, 9800X3D) — no benefit
- Ultimate Performance power plan — disables core parking, no FPS gain on modern CPUs

## Verification after edits

```powershell
$cfg = "<Steam>\userdata\<steamid>\730\local\cfg"
Get-Content "$cfg\cs2_video.txt" | Select-String 'mat_vsync|particle_detail|ao_detail|r_low_latency'
Get-Content "$cfg\cs2_machine_convars.vcfg" | Select-String 'fps_max|snd_mixahead|snd_use_hrtf|cl_interp|mm_dedicated'
```

Expected after a clean apply:
```
setting.mat_vsync                "0"
setting.videocfg_particle_detail "0"
setting.videocfg_ao_detail       "0"
setting.r_low_latency            "2"
fps_max                          "0.000000"
snd_mixahead                     "0.025000"
snd_use_hrtf                     "1"
cl_interp                        "0"
cl_interp_ratio                  "1"
mm_dedicated_search_maxping      "65"
```

## Sources

- [ProSettings.net — CS2 Best Settings (892 pros, May 2026)](https://prosettings.net/guides/cs2-options/)
- [Blur Busters G-SYNC 101](https://blurbusters.com/gsync/gsync101-input-lag-tests-and-settings/)
- [Total CS — Best CS2 Launch Options 2026](https://totalcsgo.com/launch-options)
- [NVIDIA — CS2 with Reflex](https://www.nvidia.com/en-us/geforce/news/counter-strike-2-released-featuring-nvidia-reflex/)
- [Steam Support — CS2 Trusted Mode (FACEIT compat)](https://help.steampowered.com/en/faqs/view/09A0-4879-4353-EF95)
