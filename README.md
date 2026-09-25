# CRASS

**Central de Reserva e Agendamento de Salas e Serviços**. Uma instalação por organização, com vários prédios e um fuso horário configurável.

O primeiro lançamento inclui contas com senha temporária, perfis, TOTP opcional, salas, reservas com aprovação, recorrência, bloqueios, ocorrências, notificações internas e relatórios CSV. SMS, e-mail, WhatsApp e Google Calendar têm interfaces preparadas, sem provedores ou sincronização ativos.

Em **Comunicação e integrações**, o administrador pode registrar o nome do provedor planejado para cada canal e o identificador do calendário de cada sala. Essas referências não ativam envios ou sincronização.

## Requisitos

- Docker Engine e Docker Compose
- Um domínio DNS apontando para o servidor
- Portas 80 e 443 acessíveis para emissão automática do certificado HTTPS pelo Caddy

## Instalação

1. Copie `.env.example` para `.env` e preencha domínio, senha do PostgreSQL, segredo de sessão e credenciais temporárias do administrador. Use senhas e segredo aleatórios; não envie `.env` ao Git.
2. Execute `docker compose up -d --build` na pasta do projeto.
3. Acesse `https://SEU_DOMINIO`. O administrador troca a senha temporária no primeiro acesso.
4. Em **Regras de reserva**, configure organização, fuso, horário e prazos. Cadastre prédios em **Salas**, depois as salas e os usuários.

O banco, as fotos e os dados do Caddy ficam em volumes Docker persistentes. A API de saúde está em `/api/health`; a documentação REST em `/api/docs`.

## Backup

Faça cópias do banco, das fotos e do arquivo `.env`, mantendo-os em armazenamento seguro. Exemplo em PowerShell, com a instalação iniciada:

```powershell
New-Item -ItemType Directory -Force backup | Out-Null
$db = docker compose ps -q db
$api = docker compose ps -q api
docker exec $db sh -c 'pg_dump -U crass -Fc crass > /tmp/crass.dump'
docker cp "${db}:/tmp/crass.dump" .\backup\crass.dump
docker cp "${api}:/app/uploads" .\backup\uploads
Copy-Item .env .\backup\.env
```

Confira o arquivo com `docker exec` e `pg_restore --list` ou restaure em uma instalação de ensaio antes de depender desse backup. Guarde versões anteriores em outro equipamento.

## Restauração

Use a **mesma versão do código** da instalação que gerou o backup e o `.env` correspondente. Em uma instalação nova, execute `docker compose up -d db`, depois:

```powershell
$db = docker compose ps -q db
docker cp .\backup\crass.dump "${db}:/tmp/crass.dump"
docker exec $db pg_restore --clean --if-exists -U crass -d crass /tmp/crass.dump
docker compose up -d api
$api = docker compose ps -q api
docker cp .\backup\uploads\. "${api}:/app/uploads/"
docker compose up -d
```

Se o destino já contém dados, interrompa antes `api`, `worker`, `web` e `caddy` com `docker compose stop api worker web caddy`. A restauração substitui os dados do destino. Depois, verifique login, salas, reservas, fotos e `/api/health`.

## Desenvolvimento e validação

- API: `api/app/main.py`; modelo: `api/app/models.py`; trabalhador: `api/app/worker.py`.
- Interface: `web/` (Next.js + TypeScript).
- Escopo aprovado: `.scratch/crass/spec.md`.
- Verificação básica em **instalação descartável**: defina `CRASS_URL`, `CRASS_ADMIN_EMAIL` e `CRASS_ADMIN_PASSWORD`, depois execute `py scripts/smoke.py`. O script cria dados de teste e verifica autenticação, TOTP, permissões, conflitos simultâneos, aprovação, recorrência, alterações de série, bloqueios, notificações, histórico, relatórios e CSV.
- Para verificar a API diretamente, `CRASS_API_URL` pode apontar para a raiz da API, sem o prefixo `/api`. O script troca a senha temporária do administrador no primeiro acesso.
- Interface: `cd web; npm install; npm run typecheck; npm run build`.

Não use `scripts/smoke.py` em uma instalação de produção: ele cria usuários, salas e reservas de teste.
