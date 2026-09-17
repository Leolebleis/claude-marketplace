---
name: wow-setup
description: Use when a user asks about their World of Warcraft retail install on Windows - which addons or profiles they have, installing or updating addons, reading or changing WTF SavedVariables, AddOns.txt, keybinds, OPie rings, nameplate or Cooldown Manager profiles, wago.io import strings, DBM voice packs, or which character and class they play.
---

# WoW Setup

Read and change a World of Warcraft retail install from outside the game: addon inventory, per-character enabled lists, saved-variable profiles, keybinds, and staged import strings. Pairs with `leo-skills:game-tuning` for graphics and latency.

**Core principle:** the game owns its files. Everything under `WTF\` is rewritten on logout and `/reload`, so file edits only stick when `Wow.exe` is closed, and profile imports only happen through the addon's in-game Import dialog.

**Freshness:** the file mechanics here are stable. Every claim about which addons are alive, which profiles are maintained and what the API allows was verified on 2026-09-17 for patch 12.1.0. Check the client build first (`<WoW>\.build.info`); if it is newer than 12.1, re-verify those claims through research before repeating them.

## When to Use

- "What addons / profiles do I have?", "which character is my DK?"
- Install, update, enable or disable an addon for one character
- Change saved settings on disk: OPie bindings, DBM options, addon profile assignment
- Fetch a wago.io profile or MDT route so the user can paste it in-game
- Out-of-date addon prompts, missing nameplates, addon not visible in the list

**Don't use for:** writing addon Lua (use an addon-dev MCP), Battle.net API data, FPS tuning.

## Workflow

1. **Locate.** Default `C:\Program Files (x86)\World of Warcraft\_retail_`. Layout and file meanings: `references/wow-layout.md`.
2. **Guard.** PowerShell `Get-Process Wow -ErrorAction SilentlyContinue` (in Git Bash, `tasklist` with flags breaks on MSYS path mangling). Running: only touch `Interface\AddOns\` and stage files for the user. Closed: `WTF\` edits are safe; copy each file to `<name>.claude-bak` first. The game already owns the `.bak` suffix, so never use it.
3. **Identify the character.** The active one has the newest `config-cache.wtf` under `WTF\Account\<ACCOUNT>\<Realm>\<Char>\` (folder mtimes lie). Class from `EJLootClass` in that file (6 = Death Knight, 8 = Mage; full table in the reference). A `profileKeys` entry only matters if the addon is `enabled` in that character's `AddOns.txt`.
4. **Read data with the parser**, never with grep on indentation:
   ```
   python scripts/wow_sv.py dump "<SV>\Plater.lua" profileKeys 1
   python scripts/wow_sv.py json "<SV>\OPie.lua" ProfileStorage/default/Bindings
   ```
5. **Install through the CurseForge app** when it is present, so updates keep working. First check it is not already there: `Interface\AddOns\<Name>\*.toc`, and the app's own record in `%APPDATA%\CurseForge\agent\database\app.db` table `project_operations` (ProjectId, FileId, Status). Get ids from `https://api.cfwidget.com/wow/addons/<slug>` (public; `id` is the project, `download.id` the latest file), then `Start-Process "curseforge://install?addonId=<id>&fileId=<fileId>"`. Verify the folder appeared; if not, tell the user to search the app by name. `curseforge.com` itself returns 403 to scripts.
6. **Fetch import strings** with `python scripts/wago_fetch.py info <id>` to confirm name and last-modified date, then `raw <id> <file>`. Stage every string in `Desktop\wow-imports\` with a numbered filename and a README line naming the in-game import path. Reuse the folder if it exists and update its README in the same edit so it never drifts. Never inject profiles into saved variables by hand; the addon's migrations must run.
7. **Enable per character** by editing `<Realm>\<Char>\AddOns.txt` (`Name: enabled`) while the game is closed, or tell the user to tick it in the AddOn list.

## Quick Reference

| Need | Where |
|---|---|
| Profile per character | `SavedVariables\<Addon>.lua` -> `profileKeys` |
| Plater mods and scripts on a profile | `PlaterDB.profiles.<name>.hook_data[i].{Name,Enabled}` and `script_data[i]` |
| Enabled addons per character | `<Realm>\<Char>\AddOns.txt` |
| Addon version and game-version support | `## Version`, `## Interface:` in the addon `.toc` |
| Account keybinds and macros | `bindings-cache.wtf`, `macros-cache.txt` |
| OPie ring bindings | `OPie.lua` -> `ProfileStorage.default.Bindings`, internal names in `OPie\Bundle\Editable.lua` |
| DBM voice pack and countdown voices | `DBM-Core.lua` -> `DBM_AllSavedOptions.<profile>.{ChosenVoicePack2,CountdownVoice,PullVoice}` |
| Client build | `<WoW>\.build.info` Version column; `12.1.0` = interface `120100` |
| wago metadata / string | `data.wago.io/lookup/wago?id=` / `api/raw/encoded?id=` |

## Common Mistakes

| Mistake | Fix |
|---|---|
| Editing `WTF\` while the game runs | Check `Wow.exe` first; the game overwrites on logout |
| Backing up as `<file>.bak` | That is the game's own previous-write file; use `.claude-bak` |
| `curl` to wago returns 0 bytes | Send a browser User-Agent; `wago_fetch.py` does |
| Grepping saved variables by tabs | Files are unindented; use `wow_sv.py` |
| Dropping addon folders in by hand when the CurseForge app manages the install | Install through the app so it can update them |
| Assuming the addon failed because it is not in the in-game list | The list groups by category headers; use its search box |
| Treating "only enabled for some characters" as an error | It is the mixed-state tooltip in All Characters mode |
| Telling the user to change UI Scale before an Edit Mode import | Import at the layout author's scale, or rescale the string with `scripts/editmode_rescale.py` |
| Recommending profiles from memory | Check `modified` date on wago; many pre-Midnight profiles are abandoned |
| Hunting the out-of-date prompt by reading `_Mainline.toc` only | Run `python scripts/toc_audit.py <_retail_>`: it applies Blizzard's rule (enabled addons, every TOC, DefaultState) |
| Treating `AddOns.txt` as the enabled list | It misses newly installed addons and keeps uninstalled ones; join it with the AddOns folder |
