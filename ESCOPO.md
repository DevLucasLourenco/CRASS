# CRASS — Central de Reserva e Agendamento de Salas Simples

## Objetivo

Criar do zero um sistema direto e fácil de usar para reservar salas de reunião e ajudar a pessoa responsável a acompanhar disponibilidade, uso e problemas das salas.

## Decisões tomadas

- O CRASS será um projeto próprio, inspirado em ideias do LibreBooking, room-book-simple e Effective Office, sem usar um deles como base de código.
- A experiência deve priorizar rapidez, clareza, acessibilidade e uma interface de alta qualidade.
- A navegação principal usará uma **barra lateral com menu em árvore**: grupos expansíveis, no máximo dois níveis visíveis e itens apresentados conforme o perfil do usuário. No celular, a barra lateral poderá ser recolhida.
- O banco de dados será **PostgreSQL**.
- Haverá integração configurável com **Google Calendar**.
- A comunicação incluirá notificações no sistema, e-mail e **SMS opcional**. O SMS ficará desligado até que a instituição configure e ative um provedor.
- Não haverá chat integrado nem reserva feita na porta da sala.
- Este documento registra o planejamento; a implementação ainda não foi iniciada.

## Estrutura inicial da barra lateral

```text
Visão geral
Agenda
  Hoje
  Calendário
Reservas
  Minhas reservas
  Todas as reservas *
Salas
  Catálogo
  Bloqueios *
  Ocorrências *
Relatórios *
Administração *
  Usuários e perfis
  Regras de reserva
  Integrações
  Comunicação
```

`*` Itens exibidos apenas a quem tiver a permissão correspondente. A ação **Nova reserva** deve estar sempre fácil de encontrar, sem depender de abrir um grupo do menu.

## O que vamos construir

### 1. Base e acesso

- Aplicação web responsiva, com interface em português e navegação por teclado.
- Autenticação e perfis de acesso: administrador, responsável pelas salas e usuário.
- Cadastro de usuários, permissões e histórico das ações administrativas importantes.
- Estrutura de dados no PostgreSQL para salas, reservas, bloqueios, ocorrências, usuários e notificações.

### 2. Salas e disponibilidade

- Cadastro de salas com nome, localização, capacidade, fotos e recursos disponíveis.
- Filtros por localização, capacidade, recursos e disponibilidade.
- Estado claro de cada sala: livre, ocupada, próxima reserva ou indisponível.
- Bloqueio de períodos para manutenção, limpeza e eventos internos.
- Registro e acompanhamento de problemas da sala, como equipamento ou limpeza.

### 3. Agenda e reservas

- Visão geral do dia e calendário por sala, data e período.
- Busca de sala disponível para um horário e quantidade de pessoas.
- Criação rápida de reserva e ações para editar, cancelar ou mover a reserva.
- Prevenção de conflitos de horário e indicação clara do motivo quando uma reserva não puder ser feita.
- Regras configuráveis, como antecedência, duração, horário de funcionamento e prazo de cancelamento.
- Check-in e check-out da reunião, com possibilidade de liberar a sala em caso de ausência, conforme regra configurada.

### 4. Comunicação e integrações

- Avisos de confirmação, alteração, cancelamento e lembrete de reserva.
- Preferências de comunicação por usuário e ativação de canais por tipo de evento.
- SMS opcional: escolha do provedor, credenciais, modelos de mensagem, limites de uso/custo e registro de envio. Considerar um provedor comercial e, se útil, um gateway próprio com celular e chip.
- Google Calendar configurável para relacionar as reservas à agenda dos usuários ou das salas.
- Indicação de falha de envio e possibilidade de nova tentativa para notificações importantes.

### 5. Gestão e acompanhamento

- Painel para a pessoa responsável acompanhar reuniões de hoje, próximas reuniões, salas indisponíveis e ocorrências abertas.
- Histórico de reservas e uso das salas.
- Relatórios de ocupação, cancelamentos e ausências.
- Configurações administrativas organizadas pela mesma navegação lateral.

## Ordem sugerida de construção

1. Definir fluxos e protótipos das telas principais, incluindo a barra lateral e a reserva rápida.
2. Construir autenticação, perfis, cadastro de salas e base PostgreSQL.
3. Construir agenda, disponibilidade, reservas e prevenção de conflitos.
4. Acrescentar bloqueios, check-in, ausências e ocorrências.
5. Acrescentar notificações e integrações opcionais.
6. Acrescentar relatórios e ajustes de experiência de uso.

## Decisões a detalhar antes de implementar

- Tecnologia da aplicação e forma de hospedagem.
- Fluxo exato de check-in e prazo para liberar uma reserva por ausência.
- Sentido da sincronização com Google Calendar e tratamento de conflitos entre agendas.
- Provedor inicial de SMS e limites de custo.
- Quais relatórios são indispensáveis na primeira versão.
