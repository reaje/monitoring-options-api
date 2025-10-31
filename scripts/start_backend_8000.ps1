$ErrorActionPreference = 'Stop'
$env:LOG_LEVEL = 'DEBUG'
$env:PORT = '8000'
$env:API_VERSION = '1.0.0+e2e'
$env:DEBUG = 'true'

Write-Output ("Starting backend on port " + $env:PORT)
python -m app.main

