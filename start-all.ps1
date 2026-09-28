$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.env' -PathType Leaf)) {
        throw 'Arquivo .env não encontrado. Copie .env.example para .env e preencha as configurações antes de iniciar.'
    }

    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose não está disponível.'
    }

    docker compose --env-file .env config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw 'A configuração do Docker Compose é inválida. Confira o arquivo .env.'
    }

    docker compose --env-file .env up -d --build
    if ($LASTEXITCODE -ne 0) {
        throw 'Não foi possível iniciar todos os serviços do CRASS.'
    }

    docker compose --env-file .env ps
    if ($LASTEXITCODE -ne 0) {
        throw 'Os serviços foram iniciados, mas não foi possível consultar o estado deles.'
    }
}
catch {
    Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
