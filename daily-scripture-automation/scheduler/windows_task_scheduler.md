# Windows Task Scheduler setup

Windows Task Scheduler triggers fire by the machine's local timezone
setting, not a named zone. Set the machine's timezone to Central Time
(Windows manages the CST/CDT switch itself once the zone is set correctly)
before creating the task.

## Install (PowerShell, run as the user who will own the task)

```powershell
$action = New-ScheduledTaskAction -Execute "C:\Users\REPLACE_ME\Montiwebster1\daily-scripture-automation\.venv\Scripts\daily-scripture.exe" -Argument "run" -WorkingDirectory "C:\Users\REPLACE_ME\Montiwebster1\daily-scripture-automation"
$trigger = New-ScheduledTaskTrigger -Daily -At 5:00AM
Register-ScheduledTask -TaskName "DailyScriptureAutomation" -Action $action -Trigger $trigger -Description "Daily Scripture-to-Audio and Journal Automation"
```

## Enable / Disable

```powershell
Enable-ScheduledTask -TaskName "DailyScriptureAutomation"
Disable-ScheduledTask -TaskName "DailyScriptureAutomation"
```

## Manual test

```powershell
Start-ScheduledTask -TaskName "DailyScriptureAutomation"
```

## Status

```powershell
Get-ScheduledTaskInfo -TaskName "DailyScriptureAutomation"
```

## Logs

Same as any other environment: `logs\daily-scripture-YYYY-MM-DD.log` inside
the project directory.
