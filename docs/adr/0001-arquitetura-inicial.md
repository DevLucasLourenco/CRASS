# ADR 0001 — Arquitetura inicial do CRASS

Status: aceita

## Contexto

O CRASS precisa atender uma organização por instalação, com vários prédios, regras de reserva consistentes e prevenção de conflitos mesmo sob pedidos simultâneos. SMS, e-mail, WhatsApp e Google Calendar não serão ativados no primeiro lançamento.

## Decisão

- Uma instalação Docker Compose por organização contém Next.js/TypeScript, FastAPI, um processo de trabalho separado, PostgreSQL e Caddy para HTTPS.
- O PostgreSQL armazena cada ocorrência de uma série e aplica uma restrição de exclusão para impedir sobreposição de reservas pendentes ou confirmadas na mesma sala.
- A API é a fonte de verdade das permissões, regras e reservas. O cliente consome a API REST.
- Notificações internas usam um provedor ativo. Os canais externos usam contratos de provedor e podem guardar uma referência de configuração, mas permanecem desativados. O vínculo sala-calendário pode ser preparado sem habilitar sincronização.
- Fotos ficam em volume persistente; metadados, reservas e configurações ficam no PostgreSQL.

## Consequências

Cada organização administra seus próprios backups, domínio e credenciais. A primeira versão usa `Base.metadata.create_all` para criar tabelas ausentes; mudanças futuras em colunas existentes exigirão migrações de banco explícitas antes de atualizar uma instalação em produção.
