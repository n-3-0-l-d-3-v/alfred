# Start the Alfred API.
#
# The extension is useless without this running, and every way of starting it by
# hand has a step that is easy to skip: activating the venv, being in the wrong
# directory, forgetting that a fresh clone has no .env and so no JWT secret. Each
# of those surfaces in the panel as the same unhelpful "Can't reach the Alfred
# server", so this script does all of them and refuses to start half-configured.
#
#   powershell -ExecutionPolicy Bypass -File apps\api\run.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "No virtualenv yet - creating one." -ForegroundColor Yellow
    python -m venv .venv
    & $python -m pip install --quiet --upgrade pip
    & $python -m pip install --quiet -r requirements.txt
    Write-Host "Dependencies installed."
}

if (-not (Test-Path ".env")) {
    # Generated rather than prompted for: a default secret in source would let
    # anyone who read the file mint a token for any account, and asking a
    # first-time user to invent one is how .env ends up with "changeme" in it.
    Write-Host "No .env - generating one with a fresh JWT secret." -ForegroundColor Yellow
    $secret = & $python -c "import secrets; print(secrets.token_urlsafe(32))"
    @(
        "# Local development only. Gitignored - never commit this file."
        "ALFRED_JWT_SECRET=$secret"
        "ALFRED_DEV_AUTH_ENABLED=true"
    ) | Set-Content -Path ".env" -Encoding utf8
}

Write-Host ""
Write-Host "Alfred API -> http://127.0.0.1:8000   (docs at /docs)" -ForegroundColor Green
Write-Host "Leave this window open while you use the extension. Ctrl+C to stop."
Write-Host ""

# --reload so editing the API doesn't need a restart; bound to loopback only,
# because dev auth is enabled above and that trusts anyone who can reach the port.
& $python -m uvicorn alfred.main:app --host 127.0.0.1 --port 8000 --reload
