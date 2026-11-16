@echo off
title Daily Fortune - Create Windows Desktop App Shortcut
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir = '%~dp0'.TrimEnd('\'); " ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$lnkPath = Join-Path $desktop 'Daily Fortune.lnk'; " ^
  "$wsh = New-Object -ComObject WScript.Shell; " ^
  "$sc = $wsh.CreateShortcut($lnkPath); " ^
  "$sc.TargetPath = 'wscript.exe'; " ^
  "$sc.Arguments = '\"' + (Join-Path $dir 'Launch_Daily_Fortune_App.vbs') + '\"'; " ^
  "$sc.WorkingDirectory = $dir; " ^
  "$sc.IconLocation = (Join-Path $dir 'web\icons\daily_fortune.ico') + ',0'; " ^
  "$sc.Description = 'Daily Fortune - Personal Auspicious Time Planner'; " ^
  "$sc.Save(); " ^
  "Write-Host ('Shortcut created at: ' + $lnkPath) -ForegroundColor Green"
echo.
echo Desktop Shortcut ("Daily Fortune") created successfully!
pause
