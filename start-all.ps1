$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.env' -PathType Leaf)) {
        throw 'Arquivo .env nao encontrado. Copie .env.example para .env e preencha as configuracoes antes de iniciar.'
    }

    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose não está disponível.'
    }

    docker compose --env-file .env config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw 'A configuracao do Docker Compose e invalida. Confira o arquivo .env.'
    }

    docker compose --env-file .env up -d --build
    if ($LASTEXITCODE -ne 0) {
        throw 'Nao foi possivel iniciar todos os servicos do CRASS.'
    }

    docker compose --env-file .env ps
    if ($LASTEXITCODE -ne 0) {
        throw 'Os servicos foram iniciados, mas nao foi possivel consultar o estado deles.'
    }
}
catch {
    Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
