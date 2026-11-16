Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
psScript = fso.BuildPath(dir, "Launch_Daily_Fortune_App.ps1")
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & psScript & """"
CreateObject("WScript.Shell").Run cmd, 0, False
