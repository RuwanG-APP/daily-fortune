$ErrorActionPreference = "SilentlyContinue"
$AppDir = $PSScriptRoot
$Port = if ($env:PORT) { $env:PORT } else { "8795" }
$HealthUrl = "http://127.0.0.1:$Port/healthz"
$AppUrl = "http://127.0.0.1:$Port"

function Test-FortuneServer {
    try {
        $resp = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

if (-not (Test-FortuneServer)) {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $pyExe = $pyCmd.Source
        $pywExe = Join-Path (Split-Path $pyExe -Parent) "pythonw.exe"
        $runner = if (Test-Path $pywExe) { $pywExe } else { $pyExe }
        $serverScript = Join-Path $AppDir "fortune_server.py"
        Start-Process -FilePath $runner `
            -ArgumentList @("`"$serverScript`"", "--host", "0.0.0.0", "--port", $Port) `
            -WorkingDirectory $AppDir `
            -WindowStyle Hidden

        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Milliseconds 300
            if (Test-FortuneServer) { break }
        }
    }
}

$BrowserCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)

$Browser = $BrowserCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if ($Browser) {
    Start-Process -FilePath $Browser -ArgumentList @("--app=$AppUrl")
} else {
    Start-Process $AppUrl
}
