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

**BEFORE you run anything:** read `references/known-issues.md` — the **Diagnostic Traps & Gotchas** section at the top. It catalogs traps that produce false readings (e.g., WMI's `MaxClockSpeed` returns the rated clock not the boost clock — never use it to decide if a CPU is throttled), localized PerfMon counter names on non-English Windows, the SSH+sudo gotcha, and more. Several of those traps will save 30+ min of debugging if you internalize them up front.

Run all diagnostic groups **in parallel** — they're independent reads. Parse the results and note everything for the report.

**Parallel batch hazards:** A single command in a parallel SSH batch returning exit 1 (e.g., `findstr` with no matches, `where` with no result) cancels the WHOLE batch. Wrap with `& exit 0` or use PowerShell `Where-Object`.

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
# WARNING: wmic cpu's CurrentClockSpeed/MaxClockSpeed returns the SMBIOS RATED clock, not the live boost clock.
# Reading CurrentClockSpeed = MaxClockSpeed does NOT mean the CPU isn't boosting -- WMI just can't tell you.
# Use PerfMon for real boost state (locale-aware names; see Diagnostic Traps in known-issues.md):
"powershell -Command \"Get-Counter '\Processor Information(_Total)\% Processor Performance', '\Processor Information(_Total)\Processor Frequency', '\Processor Information(_Total)\Performance Limit Flags' -SampleInterval 1 -MaxSamples 2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CounterSamples | ForEach-Object { Write-Host ($_.Path.Split('\\')[-1] + ' = ' + [math]::Round($_.CookedValue,1)) } }\""
# % Processor Performance > 100 = boosting. Performance Limit Flags = 0 = nothing throttling.
# On French Windows: Get-Counter -ListSet 'Informations sur le processeur' to find localized names.

# Hardware-Accelerated GPU Scheduling (HAGS) state -- relevant for RTX 30+/40+/50 with Frame Gen
"reg query \"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\" /v HwSchMode 2>NUL & exit 0"

# HVCI / Memory Integrity state -- significant gaming perf tax on weaker CPUs
"powershell -Command \"(Get-CimInstance -Namespace root/Microsoft/Windows/DeviceGuard -ClassName Win32_DeviceGuard).SecurityServicesRunning -join ','\""
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
"tasklist | findstr /I \"NVIDIA Overlay\" & exit 0"

# Per-app GPU preferences (since Win10 20H1, this overrides NVIDIA Control Panel)
# Look for game exes with GpuPreference=2 (dGPU). Missing or AppStatus=4096 = Windows defaults to iGPU on Optimus.
"powershell -Command \"Get-ItemProperty 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' -ErrorAction SilentlyContinue | Format-List\""

# GPU engine utilization by process -- detects Discord Go Live encoder tax (videoencode at 20-30% sustained = streaming)
"powershell -Command \"(Get-Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -MaxSamples 1).CounterSamples | Where-Object CookedValue -gt 5 | Sort-Object CookedValue -Descending | Select-Object -First 10 | ForEach-Object { $proc = if ($_.InstanceName -match 'pid_(\d+)') { (Get-Process -Id $matches[1] -ErrorAction SilentlyContinue).Name } else { '?' }; Write-Host ($_.InstanceName.Split('_')[-2..-1] -join '_') ' = ' [math]::Round($_.CookedValue,1) '% ' $proc }\""

# Find Steam installation
"where /R C:\ steam.exe 2>NUL & where /R D:\ steam.exe 2>NUL & where /R E:\ steam.exe 2>NUL & exit 0"
```

After finding Steam, list installed games:
```bash
"dir /b \"<steam-path>\steamapps\common\" 2>NUL"
```

### Group E: ASUS-Specific (run only if Win32_ComputerSystem.Manufacturer matches ASUS)

```bash
# Verify ASUS WMI class is exposed (most ROG/TUF gaming laptops have it)
"powershell -Command \"Get-CimClass -Namespace root/wmi -ErrorAction SilentlyContinue | Where-Object CimClassName -match 'AsusAtk' | Select-Object CimClassName\""

# Read current Armoury Crate performance mode (0=Windows, 1=Silent, 2=Performance, 3=Turbo, 4=Manual)
"powershell -Command \"$cim = Get-CimInstance -Namespace root/wmi -ClassName AsusAtkWmi_WMNB -ErrorAction SilentlyContinue; if ($cim) { $raw = (Invoke-CimMethod -InputObject $cim -MethodName DSTS -Arguments @{Device_ID=0x00120075}).device_status; Write-Host ('Armoury Crate mode: ' + ($raw - 65536) + ' (3=Turbo)') }\""

# ASUS services (for cleanup pass -- see HVCI/Armoury sections in known-issues.md for KEEP/DISABLE triage)
"powershell -Command \"Get-Service | Where-Object { $_.Name -match 'asus|armoury|rog' -or $_.DisplayName -match 'ASUS|Armoury|ROG' } | Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize\""
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
