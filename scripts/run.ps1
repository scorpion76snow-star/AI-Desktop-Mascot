$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python app\main.py
