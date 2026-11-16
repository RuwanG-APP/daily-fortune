Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "K:\STAR\DailyFortune"
WshShell.Run """C:\Python314\python.exe"" fortune_server.py --host 0.0.0.0 --port 8795", 0, False
