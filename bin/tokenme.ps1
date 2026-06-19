# tokenme launcher — Windows PowerShell
# Usage: .\bin\tokenme.ps1 <subcommand> [args...]
$here = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = $here
python -m tokenme @args
