# build.ps1:      BUILD A SIGNET 26 BINARY WITH NUITKA (WINDOWS, --standalone, or -OneFile)
# AUTHOR:         DANIEL DESAI
# UPDATED:        2026-11-17
# VERSION:        26.b.0.1.7
#
# Needs Python 3 and nuitka (python -m pip install nuitka); Nuitka downloads MinGW64 if no C compiler is found.
# Output: dist\signet-<version>-windows-<arch>.zip, holding signet\signet.exe and its libraries
# (-OneFile: signet-<version>-windows-<arch>-onefile.zip, holding signet\signet.exe alone). Linux: build.sh.
# Run: powershell -ExecutionPolicy Bypass -File build.ps1 [-OneFile]

param([switch]$OneFile)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Need($ok, $msg) { if (-not $ok) { Write-Error "build.ps1: $msg"; exit 1 } }

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
Need $py 'python not found'
& $py -m nuitka --version *> $null
Need ($LASTEXITCODE -eq 0) 'nuitka not found (python -m pip install nuitka)'

$version = (Get-Content VERSION -TotalCount 1).Trim()
$baked = (Select-String -Path signet.py -Pattern '^VERSION = "(.*)"').Matches[0].Groups[1].Value
Need ($baked -eq $version) "VERSION ($version) differs from signet.py ($baked)"
$arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x86_64' }
$name = "signet-$version-windows-$arch"
$mode = '--standalone'
if ($OneFile) { $mode = '--onefile'; $name = "$name-onefile" }

Remove-Item -Recurse -Force build, "dist\$name", "dist\$name.zip" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force build, "dist\$name\signet" | Out-Null
& $py -m nuitka $mode --assume-yes-for-downloads --remove-output `
    --include-data-files=VERSION=VERSION `
    --output-dir=build --output-filename=signet.exe signet.py
Need ($LASTEXITCODE -eq 0) 'nuitka failed'
if ($OneFile) { Copy-Item build\signet.exe "dist\$name\signet\" }
else { Copy-Item -Recurse build\signet.dist\* "dist\$name\signet\" }
Copy-Item VERSION, LICENSE, README.md "dist\$name\"
$bin = (Resolve-Path "dist\$name\signet\signet.exe").Path

# Smoke test: run the binary on a hello module in a scratch folder.
$t = Join-Path ([IO.Path]::GetTempPath()) ([IO.Path]::GetRandomFileName())
New-Item -ItemType Directory $t | Out-Null
Push-Location $t
try {
    function Run([string[]]$a) { $ErrorActionPreference = 'Continue'; $o = & $bin @a 2>&1 | Out-String;Need ($LASTEXITCODE -eq 0) "signet $a failed: $o"; $o }
    Set-Content -Encoding ascii hello.signet "let hello = 'Hello, world!'`nconnect(hello, message.input)`nrun(message)`necho(message.output.sig)"
    Set-Content -Encoding ascii message.signet "echo(input)`noutput(output, input)"
    Need ((Run '--version') -match [regex]::Escape($version)) 'wrong --version'
    Need ((Run 'hello.signet', '--check') -match 'ok') '--check failed'
    Need ((Run 'hello.signet') -match 'message.output.sig = "Hello, world!"') 'Signet module failed'
    Run '--export-helpers', 'helpers' | Out-Null
    Need (Test-Path helpers\signet\__init__.py) '--export-helpers failed'
    Remove-Item message.signet
    Set-Content -Encoding ascii message.py "from signet import signals`nprint(signals.input)`nsignals.output = signals.input"
    Need ((Run 'hello.signet') -match 'message.output.sig = "Hello, world!"') 'Python module failed'
    Write-Output 'smoke test: ok'
} finally { Pop-Location; Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue }

Compress-Archive -Force -Path "dist\$name" -DestinationPath "dist\$name.zip"
Write-Output "built dist\$name.zip"
