#!/usr/bin/env bash
set -euo pipefail

main() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local DRY_RUN=false
    local AUTO_YES=false

    # Parse flags
    for arg in "$@"; do
        case "$arg" in
            --dry-run)
                DRY_RUN=true
                ;;
            --yes)
                AUTO_YES=true
                ;;
            *)
                echo "Unknown flag: $arg"
                echo "Usage: import.sh [--dry-run] [--yes]"
                exit 1
                ;;
        esac
    done

    if $DRY_RUN; then
        echo "[dry-run] No files will be written."
        echo
    fi

    # -------------------------------------------------------------------------
    # Helpers (duplicated from export.sh -- will refactor to lib.sh later)
    # -------------------------------------------------------------------------

    # Detect the real home directory, handling Git Bash path mangling.
    detect_home() {
        case "$(uname -s)" in
            MINGW*|MSYS*|CYGWIN*)
                # Convert /c/Users/leole -> C:/Users/leole
                local drive="${HOME:1:1}"
                drive="$(echo "$drive" | tr '[:lower:]' '[:upper:]')"
                echo "${drive}:${HOME:2}"
                ;;
            *)
                echo "$HOME"
                ;;
        esac
    }

    local REAL_HOME
    REAL_HOME="$(detect_home)"

    local CLAUDE_DIR="$HOME/.claude"

    # Encode a path the same way Claude does:
    # Replace : / \ with -, then strip leading -
    encode_path() {
        echo "$1" | sed 's/[:\\/]/-/g; s/^-//'
    }

    # Dry-run-aware copy (single file)
    safe_cp() {
        local src="$1"
        local dst="$2"
        if $DRY_RUN; then
            echo "  [copy] $src -> $dst"
        else
            mkdir -p "$(dirname "$dst")"
            cp "$src" "$dst"
        fi
    }

    # Dry-run-aware recursive directory copy (contents of src_dir into dst_dir)
    safe_cp_r() {
        local src_dir="$1"
        local dst_dir="$2"
        if $DRY_RUN; then
            # Walk recursively to show all files
            while IFS= read -r -d '' f; do
                local rel="${f#"$src_dir"/}"
                echo "  [copy] $f -> $dst_dir/$rel"
            done < <(find "$src_dir" -type f -print0)
        else
            mkdir -p "$dst_dir"
            cp -r "$src_dir"/. "$dst_dir/"
        fi
    }

    # Prompt for confirmation. Returns 0 if yes.
    # If --yes flag is set, always returns 0.
    confirm() {
        local msg="$1"
        if $AUTO_YES; then
            echo "  $msg [auto-yes]"
            return 0
        fi
        if $DRY_RUN; then
            # In dry-run mode, assume yes for display purposes
            return 0
        fi
        printf "  %s [y/N] " "$msg"
        local answer
        read -r answer
        case "$answer" in
            [yY]|[yY][eE][sS]) return 0 ;;
            *) return 1 ;;
        esac
    }

    # Convert REAL_HOME (C:/Users/leole) back to unix path for filesystem ops
    to_unix_path() {
        local p="$1"
        case "$(uname -s)" in
            MINGW*|MSYS*|CYGWIN*)
                local drive_letter="${p:0:1}"
                drive_letter="$(echo "$drive_letter" | tr '[:upper:]' '[:lower:]')"
                echo "/${drive_letter}${p:2}"
                ;;
            *)
                echo "$p"
                ;;
        esac
    }

    # -------------------------------------------------------------------------
    # Counters
    # -------------------------------------------------------------------------
    local global_count=0
    local project_count=0
    local file_count=0

    # -------------------------------------------------------------------------
    # 1. Global config import
    # -------------------------------------------------------------------------
    echo "=== Global config ==="

    local global_src="$SCRIPT_DIR/global"
    if [[ ! -d "$global_src" ]]; then
        echo "  (no global/ directory found in repo)"
    else
        # Iterate over all files and directories in global/
        for item in "$global_src"/*; do
            [[ -e "$item" ]] || continue
            local name
            name="$(basename "$item")"
            local target="$CLAUDE_DIR/$name"

            if [[ -d "$item" ]]; then
                # Directory (e.g., commands/)
                if [[ -d "$target" ]]; then
                    if ! confirm "Overwrite $target/ ?"; then
                        echo "  Skipping $name/"
                        continue
                    fi
                fi
                safe_cp_r "$item" "$target"
                # Count files inside
                while IFS= read -r -d '' f; do
                    (( file_count++ )) || true
                    (( global_count++ )) || true
                done < <(find "$item" -type f -print0)
            else
                # Single file
                if [[ -f "$target" ]]; then
                    if ! confirm "Overwrite $target ?"; then
                        echo "  Skipping $name"
                        continue
                    fi
                fi
                safe_cp "$item" "$target"
                (( file_count++ )) || true
                (( global_count++ )) || true

                # Preserve execute bit on superpowers-bootstrap.sh
                if [[ "$name" == "superpowers-bootstrap.sh" ]] && ! $DRY_RUN; then
                    chmod +x "$target"
                fi
            fi
        done
    fi

    echo "  $global_count global files"
    echo

    # -------------------------------------------------------------------------
    # 2. Per-project config import
    # -------------------------------------------------------------------------
    echo "=== Projects ==="

    local projects_src="$SCRIPT_DIR/projects"
    if [[ ! -d "$projects_src" ]]; then
        echo "  (no projects/ directory found in repo)"
    else
        # Find unique project directories.
        # A directory is a "project" if it directly contains _global/, _local/,
        # or a CLAUDE.md (that is not inside _global or _local).
        local -A seen_projects

        # Find _global and _local dirs, take their parent
        while IFS= read -r -d '' d; do
            local parent
            parent="$(dirname "$d")"
            local rel="${parent#"$projects_src"/}"
            seen_projects["$rel"]=1
        done < <(find "$projects_src" -type d \( -name "_global" -o -name "_local" \) -print0)

        # Find CLAUDE.md files whose parent is NOT _global or _local
        while IFS= read -r -d '' f; do
            local parent
            parent="$(dirname "$f")"
            local parent_name
            parent_name="$(basename "$parent")"
            if [[ "$parent_name" != "_global" && "$parent_name" != "_local" ]]; then
                local rel="${parent#"$projects_src"/}"
                seen_projects["$rel"]=1
            fi
        done < <(find "$projects_src" -name "CLAUDE.md" -type f -print0)

        # Sort project paths for deterministic output
        local sorted_projects=()
        for key in "${!seen_projects[@]}"; do
            sorted_projects+=("$key")
        done
        IFS=$'\n' sorted_projects=($(sort <<< "${sorted_projects[*]}")); unset IFS

        for rel_path in "${sorted_projects[@]}"; do
            local proj_src="$projects_src/$rel_path"
            local target_dir="$REAL_HOME/$rel_path"
            local target_dir_unix
            target_dir_unix="$(to_unix_path "$target_dir")"

            echo "  --- $rel_path"

            # Check if target directory exists
            if [[ ! -d "$target_dir_unix" ]]; then
                if ! confirm "Create ~/$rel_path/ ?"; then
                    echo "    Skipping project"
                    continue
                fi
                if ! $DRY_RUN; then
                    mkdir -p "$target_dir_unix"
                else
                    echo "  [mkdir] $target_dir_unix"
                fi
            fi

            # Import _local/ -> <target>/.claude/
            if [[ -d "$proj_src/_local" ]]; then
                local local_target="$target_dir_unix/.claude"
                if [[ -d "$local_target" ]]; then
                    if ! confirm "Overwrite $target_dir/.claude/ ?"; then
                        echo "    Skipping _local"
                    else
                        safe_cp_r "$proj_src/_local" "$local_target"
                        while IFS= read -r -d '' f; do
                            (( file_count++ )) || true
                        done < <(find "$proj_src/_local" -type f -print0)
                    fi
                else
                    safe_cp_r "$proj_src/_local" "$local_target"
                    while IFS= read -r -d '' f; do
                        (( file_count++ )) || true
                    done < <(find "$proj_src/_local" -type f -print0)
                fi
            fi

            # Import CLAUDE.md (root-level, not inside _global or _local)
            if [[ -f "$proj_src/CLAUDE.md" ]]; then
                local claude_target="$target_dir_unix/CLAUDE.md"
                if [[ -f "$claude_target" ]]; then
                    if ! confirm "Overwrite $target_dir/CLAUDE.md ?"; then
                        echo "    Skipping CLAUDE.md"
                    else
                        safe_cp "$proj_src/CLAUDE.md" "$claude_target"
                        (( file_count++ )) || true
                    fi
                else
                    safe_cp "$proj_src/CLAUDE.md" "$claude_target"
                    (( file_count++ )) || true
                fi
            fi

            # Import _global/ -> ~/.claude/projects/<encoded>/
            if [[ -d "$proj_src/_global" ]]; then
                local full_target_path="$target_dir"
                local encoded
                encoded="$(encode_path "$full_target_path")"
                local global_target="$CLAUDE_DIR/projects/$encoded"

                if [[ -f "$proj_src/_global/CLAUDE.md" ]]; then
                    safe_cp "$proj_src/_global/CLAUDE.md" "$global_target/CLAUDE.md"
                    (( file_count++ )) || true
                fi
                if [[ -f "$proj_src/_global/memory/MEMORY.md" ]]; then
                    safe_cp "$proj_src/_global/memory/MEMORY.md" "$global_target/memory/MEMORY.md"
                    (( file_count++ )) || true
                fi
            fi

            (( project_count++ )) || true
        done
    fi

    echo
    echo "  $project_count projects"
    echo

    # -------------------------------------------------------------------------
    # 3. Plugins
    # -------------------------------------------------------------------------
    echo "=== Plugins ==="

    local plugins_file="$SCRIPT_DIR/plugins.json"
    if [[ ! -f "$plugins_file" ]]; then
        echo "  (no plugins.json found)"
    else
        if command -v jq &>/dev/null; then
            # Extract plugin names from the "plugins" object keys
            local plugin_names
            plugin_names="$(jq -r '.plugins | keys[]' "$plugins_file" 2>/dev/null || true)"
            if [[ -z "$plugin_names" ]]; then
                echo "  (no plugins found in plugins.json)"
            else
                echo "  Install plugins manually:"
                echo
                while IFS= read -r name; do
                    # Extract the package part (name@registry -> name)
                    local short_name="${name%%@*}"
                    local registry="${name#*@}"
                    if [[ "$registry" == "$name" ]]; then
                        # No @ separator
                        echo "    claude plugin install $name"
                    else
                        echo "    claude plugin install $short_name@$registry"
                    fi
                done <<< "$plugin_names"
            fi
        else
            # No jq -- extract plugin names with grep/sed
            local plugin_names
            plugin_names="$(grep -oE '"[^"]+@[^"]+":' "$plugins_file" | sed 's/"//g; s/://' || true)"
            if [[ -z "$plugin_names" ]]; then
                echo "  (could not parse plugins.json without jq)"
            else
                echo "  Install plugins manually:"
                echo
                while IFS= read -r name; do
                    echo "    claude plugin install $name"
                done <<< "$plugin_names"
            fi
        fi
    fi

    echo

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    echo "=== Summary ==="
    echo "  Global files: $global_count"
    echo "  Projects:     $project_count"
    echo "  Total files:  $file_count"
    if $DRY_RUN; then
        echo
        echo "  (dry run -- nothing was written)"
    else
        echo
        echo "  Imported from: $SCRIPT_DIR"
    fi
}

main "$@"
