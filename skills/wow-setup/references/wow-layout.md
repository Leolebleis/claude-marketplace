# WoW retail install layout and facts

**Verified on 2026-09-17 against client 12.1.0.69814 (Midnight Season 2).** The file layout section is stable; everything under "Addon sources" and "Midnight addon landscape" is a snapshot of that date. Addon status, profile maintainers and Blizzard API policy change every patch, so treat those sections as suspect once the client is past 12.1 and re-verify before recommending anything.

## Paths

```
<WoW>\_retail_\
  Interface\AddOns\<Addon>\                addon code; <Addon>.toc or <Addon>_Mainline.toc
  WTF\Config.wtf                           account-wide CVars (graphics, sound, nameplate cvars)
  WTF\Account\<ACCOUNT>\
    SavedVariables\<Addon>.lua             account-wide addon data (profiles, profileKeys)
    SavedVariables\<Addon>.lua.bak         previous write
    bindings-cache.wtf                     account keybinds
    macros-cache.txt                       account macros
    edit-mode-cache-account.txt            Edit Mode layouts (binary-ish, names readable)
    <Realm>\<Character>\
      AddOns.txt                           per-character enabled list ("Name: enabled|disabled")
      SavedVariables\<Addon>.lua           per-character addon data
      config-cache.wtf                     per-character CVars; EJLootClass = class ID
      macros-cache.txt                     character macros (spell names reveal class/spec)
      cooldownmanager.txt                  Cooldown Manager layout blob
```

Default install: `C:\Program Files (x86)\World of Warcraft\_retail_`. Confirm with the registry key `HKCU\SOFTWARE\Blizzard Entertainment\World of Warcraft\Client` or the Battle.net product database.

Client build: `<WoW>\.build.info` (one level above `_retail_`), Version column, or the FileVersion of `Wow.exe`. Map `12.1.0` to interface `120100`.

`AddOns.txt` is neither complete nor clean: addons installed after its last write are missing (they load with their `## DefaultState`, normally enabled) and entries for uninstalled addons persist. Join it with the `Interface\AddOns\` listing to get the real enabled set.

## Identifying characters

- Class: `SET EJLootClass "N"` in the character's `config-cache.wtf`. IDs: 1 Warrior, 2 Paladin, 3 Hunter, 4 Rogue, 5 Priest, 6 Death Knight, 7 Shaman, 8 Mage, 9 Warlock, 10 Monk, 11 Druid, 12 Demon Hunter, 13 Evoker.
- Which character is active: the newest `config-cache.wtf` across `WTF\Account\<ACCOUNT>\<Realm>\<Char>\`. Folder mtimes only change when entries are added, so they lie.
- Characters never logged in since the folder was created have no `config-cache.wtf`; their class is unknown from disk.
- Spec is not stored plainly. Macro names and Cooldown Manager contents hint at it.

## Write rules

- The game rewrites `SavedVariables\*.lua`, `AddOns.txt`, `config-cache.wtf` and the caches on logout and on `/reload`. Edits made while `Wow.exe` runs are overwritten. Check `tasklist | findstr Wow.exe` before writing.
- `Interface\AddOns\` can be changed while the game runs. The player then needs `/reload` or a relog.
- Saved-variable files have no indentation. Use `scripts/wow_sv.py`, not grep on tabs.
- Profile imports (nameplates, Cooldown Manager, bag layouts, routes) only happen in-game through the addon's Import dialog. Stage strings in a text file for the user to paste.

## Addon sources

- CurseForge app installed: install through it so updates keep working. Deep link `curseforge://install?addonId=<id>&fileId=<fileId>` opens the app's install prompt. It is unreliable for some addons; fallback is the app's search box. Numeric ids come from `https://api.cfwidget.com/wow/addons/<slug>` (public, no key). Direct `curseforge.com` fetches return 403 to scripts.
- CurseForge REST API needs an approved key and forbids caching. Avoid.
- wago.io: `https://data.wago.io/lookup/wago?id=<id>` for metadata, `https://data.wago.io/api/raw/encoded?id=<id>` for the import string. Documented at `https://data.wago.io/openapi.json`. Use `scripts/wago_fetch.py` (`versions` lists every version with its changelog). Wago's compression has corrupted strings before; if an in-game Import rejects a staged string, copy it from the wago page instead.
- The CurseForge app's own install records: `%APPDATA%\CurseForge\agent\database\app.db`, table `project_operations`. No `sqlite3` binary on this machine; use Python's `sqlite3` module on a copy of the file.
- `scripts/toc_audit.py <WoW>\_retail_` lists every addon folder with its TOC interface values and per-character enabled state, and flags out-of-date ones.
- Reading wago listing pages needs JavaScript; use search engines or known ids instead. Wowhead and luxthos.com article bodies are also JS-rendered; rely on search snippets or the wago description text.
- cfwidget also returns per-file `versions` lists, which is the quickest way to see whether an addon has a build for the current patch.

## Midnight (12.x) addon landscape (snapshot 2026-09-17, patch 12.1.0)

- Secret values: addons display combat state but cannot compute on it. WeakAuras and Hekili ended on retail. Built-in replacements: Cooldown Manager, Assisted Highlight, damage meter, boss warnings timeline.
- Nameplates: Platynator is built for the new API and can colour off-tank threat; Plater cannot. Threat Plates disabled its threat logic.
- Still current: DBM and BigWigs, Details, MDT and plugins, Raider.IO, OPie, Leatrix Plus, Plumber, HandyNotes with a per-expansion pack.
- The in-game AddOn list groups addons under collapsible category headers; use its search box. "This addon is only enabled for some characters" is the mixed-state tooltip in All Characters mode.
- "Interface modifications which are out of date" prompt: Blizzard flags any *enabled* addon (including ones absent from `AddOns.txt`, and LoadOnDemand ones) whose every `## Interface:` value is below the client build. A comma list passes if any value is current. A folder holding only a foreign-flavour TOC (`_Vanilla.toc`, `_Cata.toc`) is still enumerated on retail and flagged; DBM ships such test modules. Check every `.toc` in every folder, then cross with enabled state. "Load out of date AddOns" only hides the prompt; disabling the culprit fixes it.
- DBM voices live in `DBM-Core.lua` under `DBM_AllSavedOptions[<profile>]`: `ChosenVoicePack2` (VEM ships inside DBM now), `CountdownVoice`, `CountdownVoice2`, `CountdownVoice3`, `PullVoice`. The profile name comes from `DBM_UsedProfile` in the character's own `DBM-Core.lua`. None of it plays if DBM-Core or the voice module is disabled for that character. Dungeon alerts need the matching `DBM-Party-<Expansion>` module enabled.
- Edit Mode layouts are UI-scale dependent, not resolution dependent: offsets are UI units and the UI space is always 768 / uiScale units tall (16:9 width follows). A layout made at 0.65 spans 1181 by 2100 units; at uiScale 1.0 the space is 768 by 1365, so frames overshoot and pile up. Import at the author's scale, or run `scripts/editmode_rescale.py <layout> <author_scale> <target_scale>`. Current scale: `SET uiScale` in `WTF\Config.wtf`.
- Blizzard Cooldown Manager profiles import in Options > Gameplay > Advanced Cooldown Settings > Import (also reachable from Edit Mode by selecting the Cooldown Manager). Five profiles per spec. The Edit Mode layout Import dialog is a different thing and rejects these strings.

## OPie

- Built-in rings and internal names in `OPie\Bundle\Editable.lua` (`AddDefaultRing("<Name>"`). Class-limited rings can share a key.
- Bindings live in `OPie.lua` under `ProfileStorage.default.Bindings` keyed by internal ring name.
