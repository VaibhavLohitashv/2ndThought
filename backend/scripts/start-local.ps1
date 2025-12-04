param(
    [int]$Port = 8000
)

Write-Host "Starting Postgres and Redis via docker-compose..."
docker-compose up -d db redis

Write-Host "Waiting a few seconds for DB to accept connections..."
Start-Sleep -Seconds 3

Write-Host "Starting backend (uvicorn) on port $Port..."

if (Test-Path -Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -and ($_ -notmatch '^#')) {
            $parts = $_ -split '='
            if ($parts.Count -ge 2) {
                $name = $parts[0].Trim()
                $value = ($parts[1..($parts.Count-1)] -join '=').Trim()
                [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
            }
        }
    }
}

python -m uvicorn app.main:app --reload --port $Port
