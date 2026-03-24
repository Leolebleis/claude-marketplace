---
name: pc-performance-audit
description: "Use when the user wants to diagnose performance issues on a Windows PC, optimize a gaming setup, audit system resources, find what's eating RAM or CPU, check for bloatware, or improve FPS. Applies to both local machines and remote PCs via SSH."
---

# PC Performance Audit

Audit a Windows PC for performance bottlenecks. Produce a ranked fix plan with exact apply/verify/rollback commands. Apply fixes one at a time with verification between each.

Works both **locally** (commands run directly) and **remotely** (commands prefixed with an SSH connection string).

## Input

Determine whether this is a local or remote audit:
- **Remote:** The user provides an SSH connection string (e.g., `ssh -i key user@host`). Prefix every command with it.
- **Local:** The target is the current machine. Run commands directly. Note: `powercfg` and some Windows commands may need to be wrapped in `powershell -Command "..."` when running from a bash shell. Some commands need admin — use `gsudo` if available, otherwise note that admin is required.

For remote audits, `$` variables in PowerShell commands will be eaten by bash — write `.ps1` script files and execute them via `powershell -ExecutionPolicy Bypass -File script.ps1` instead.

## Step 1: Gather Data

Run all diagnostic groups **in parallel** — they're independent reads. Parse the results and note everything for the report.

### Group A: Hardware

```bash
# CPU
"wmic cpu get Name,NumberOfCores,NumberOfLogicalProcessors,CurrentClockSpeed /format:list"

# RAM sticks (slot count, capacity, speed, dual/single channel)
"powershell -Command \"Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator, Capacity, Speed, ConfiguredClockSpeed, Manufacturer | Format-Table -AutoSize\""

# GPU
"powershell -Command \"Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, DriverDate, AdapterRAM | Format-List\""

# Disks (SSD vs HDD, model, size)
"wmic diskdrive get Model,MediaType,Size,InterfaceType /format:list"

# Drive letters, free space
"wmic logicaldisk get DeviceID,FreeSpace,Size,VolumeName,DriveType /format:csv"
```

### Group B: System State

```bash
# RAM + swap usage
"wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /format:list"
"wmic OS get FreeVirtualMemory,TotalVirtualMemorySize /format:list"

# Active power plan
"powercfg /getactivescheme"

# Available power plans
"powercfg /list"

# Page file — location, size, usage (check which drive it's on + free space on that drive)
"powershell -Command \"Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage | Format-List\""
"powershell -Command \"Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' | Select-Object PagingFiles | Format-List\""

# CPU clock + load snapshot
"wmic cpu get CurrentClockSpeed,LoadPercentage /format:list"
```

### Group C: Processes & Services

```bash
# Top processes by memory — pipe through awk locally:
# tr -d '\r' | awk -F',' 'NR>1 && $3!="" {name=$2; mb=$3/1048576; if(mb>30) printf "%8.0f MB  %s\n", mb, name}' | sort -rn | head -30
"wmic process get Name,WorkingSetSize /format:csv"

# Startup programs
"powershell -Command \"Get-CimInstance Win32_StartupCommand | Select-Object Name, Command | Format-Table -AutoSize -Wrap\""

# Key services
"powershell -Command \"Get-Service SysMain, DiagTrack, WSearch | Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize\""

# Nahimic (OEM audio bloatware — may not exist on non-OEM builds)
"sc query NahimicService 2>NUL & sc qc NahimicService 2>NUL"
```

### Group D: Gaming-Specific

```bash
# Game DVR status
"reg query \"HKCU\System\GameConfigStore\" /v GameDVR_Enabled"

# NVIDIA overlay processes
"tasklist | findstr /I \"NVIDIA Overlay\""

# Find Steam installation
"where /R C:\ steam.exe 2>NUL & where /R D:\ steam.exe 2>NUL & where /R E:\ steam.exe 2>NUL"
```

After finding Steam, list installed games:
```bash
"dir /b \"<steam-path>\steamapps\common\" 2>NUL"
```

## Step 2: Analyze

Cross-reference findings against `references/known-issues.md` for the full pattern catalog. That file contains every known issue pattern, detection criteria, fix commands, and impact ratings.

## Step 3: Report

Structure the output as:

```
## PC Performance Audit: <username or hostname>

### System Specs
[Table: CPU, GPU, RAM config, drives with type/size/free, OS]

### Health Summary
[Table: metric | value | OK/Warning/BAD status]
Key metrics: power plan, CPU clock vs max boost, free RAM, swap usage, disk layout

### Top Memory Consumers
[Table: process | RAM | notes — top 15-20]

### Issues Found
[Ranked by impact, each referencing a fix]

### Fix Plan
[Fixes ordered by impact — see Step 4 for format]
```

## Step 4: Fix Format

Every fix MUST include:

```
#### FIX N: <title>
**Why:** <what's wrong and why it matters>
**Impact:** CRITICAL / HIGH / MEDIUM / LOW — <expected improvement>
**Risk:** <what could break or be lost>
**Needs reboot:** Yes/No
**Needs user's hands:** Yes/No

**Apply:**  <exact command>
**Verify:** <exact command + expected output>
**Rollback:** <exact command to undo>
```

## Step 5: Execute

Apply fixes **one at a time** in impact order:

1. Run the apply command
2. Run the verify command — confirm expected output
3. Ask the user to check with the PC owner that nothing broke
4. Only then proceed to the next fix

Never batch fixes. If something breaks, you need to know which fix caused it.

## Minecraft-Specific

If Minecraft is relevant and a Spark profile URL is provided, defer to the `minecraft-spark-analyzer:spark-analyze` skill for deep analysis. This skill handles system-level issues.

For JVM args, check running Java processes:
```bash
"wmic process where \"name='javaw.exe'\" get CommandLine /format:list"
```
