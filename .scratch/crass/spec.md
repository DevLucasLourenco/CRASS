# CRASS — Central de Reserva e Agendamento de Salas e Serviços

Status: ready-for-human

## Problem Statement

Quem organiza reuniões precisa descobrir salas disponíveis, evitar conflitos e acompanhar reservas, ausências, indisponibilidades e problemas. A pessoa responsável pelas salas precisa de uma visão única do dia e de regras previsíveis, sem depender de planilhas ou de várias agendas desconectadas. O sistema deve funcionar bem tanto para quem reserva quanto para quem administra, em computador ou celular.

## Solution

Construir o CRASS do zero como aplicação web em português. Cada organização terá sua própria instalação, com vários prédios, um fuso horário e uma agenda de salas central. Usuários reservam suas próprias reuniões; responsáveis gerenciam todas as salas e tratam aprovações, bloqueios, ausências e ocorrências. A interface terá painel inicial único, agenda, busca direta e barra lateral em árvore. O primeiro lançamento terá notificações internas e todas as funções de gestão descritas abaixo. Integrações externas terão interfaces preparadas e permanecerão desativadas até a escolha de provedores e uma entrega posterior.

## User Stories

1. Como administrador, quero iniciar uma instalação para uma organização, para que seus dados fiquem separados dos de outras instalações.
2. Como administrador, quero definir o fuso horário da instalação, para que todas as salas usem a mesma referência de horário.
3. Como administrador, quero criar contas com senha temporária, para controlar quem acessa o CRASS.
4. Como novo usuário, quero trocar a senha temporária no primeiro acesso, para proteger minha conta.
5. Como usuário, quero entrar com e-mail e senha, para acessar minhas reservas.
6. Como usuário, quero ativar TOTP e guardar códigos de recuperação, para aumentar a proteção da conta sem depender de SMS ou e-mail.
7. Como administrador, quero redefinir o acesso de um usuário, para ajudá-lo quando perder a senha e não houver envio de e-mail configurado.
8. Como administrador, quero atribuir os perfis de administrador, responsável e usuário, para controlar as ações disponíveis.
9. Como responsável, quero gerenciar todas as salas da instalação, para cobrir qualquer prédio sem trocar de conta ou área.
10. Como usuário, quero ver um painel com agenda, disponibilidade e avisos, para entender rapidamente o que exige minha atenção.
11. Como responsável, quero ver aprovações, mudanças e ocorrências em uma fila no painel, para tratar o trabalho sem receber um aviso separado por cada evento.
12. Como usuário, quero navegar por uma barra lateral em árvore com grupos claros, para encontrar as funções sem enfrentar menus longos.
13. Como usuário no celular, quero recolher a barra lateral, para ter espaço para a agenda e os formulários.
14. Como usuário, quero encontrar a ação de nova reserva sem abrir um grupo do menu, para reservar rapidamente.
15. Como administrador, quero cadastrar prédios e andares, para organizar as salas por localização.
16. Como administrador, quero cadastrar salas com nome, localização, capacidade, fotos e recursos, para descrever o que cada uma oferece.
17. Como usuário, quero filtrar salas por prédio, andar, capacidade, recursos e disponibilidade, para escolher uma sala adequada.
18. Como usuário, quero ver os estados livre, ocupada, próxima reserva e indisponível, para compreender a situação de cada sala.
19. Como usuário, quero consultar agenda diária e calendário por sala e período, para planejar uma reunião.
20. Como usuário, quero consultar os detalhes das reservas da instalação, para compreender como as salas serão usadas.
21. Como administrador, quero configurar regras gerais de horário, antecedência, duração e cancelamento, para estabelecer uma política de reserva.
22. Como administrador, quero ajustar essas regras por sala, para atender salas com necessidades diferentes.
23. Como administrador, quero definir por sala se a reserva é imediata ou exige aprovação, para controlar salas especiais.
24. Como usuário, quero reservar uma sala informando título, descrição, número previsto de pessoas, início e fim, para registrar minha reunião.
25. Como usuário, quero receber confirmação imediata quando a sala não exigir aprovação e as regras forem atendidas, para saber que posso usá-la.
26. Como usuário, quero ver uma solicitação pendente quando a sala exigir aprovação, para acompanhar a decisão.
27. Como usuário, quero que uma solicitação pendente bloqueie o horário, para não disputar a sala com outra solicitação enquanto aguardo.
28. Como responsável, quero aprovar ou rejeitar solicitações, para controlar o uso das salas que exigem revisão.
29. Como administrador, quero configurar o prazo de expiração das pendências, para que um horário não fique bloqueado indefinidamente.
30. Como usuário, quero receber uma explicação quando horário, capacidade ou regra impedir a reserva, para corrigir a solicitação.
31. Como usuário, quero editar, mover ou cancelar minhas reservas, para adaptar a agenda quando os planos mudarem.
32. Como responsável, quero editar, mover ou cancelar reservas de qualquer usuário, para resolver necessidades da operação.
33. Como usuário, quero criar uma série recorrente, inclusive sem data final, para reuniões repetidas.
34. Como usuário, quero que o CRASS gere reservas dos próximos 12 meses e continue a série ao longo do tempo, para manter a agenda futura.
35. Como usuário, quero que datas ocupadas sejam puladas e listadas, para aproveitar as datas livres sem perder conhecimento dos conflitos.
36. Como usuário, quero alterar uma ocorrência, todas as futuras ou toda a série, para corrigir a parte necessária da recorrência.
37. Como responsável, quero aprovar de uma vez as ocorrências disponíveis de uma série em sala controlada, para evitar decisões repetitivas.
38. Como usuário, quero que a reunião passe a estar em andamento no horário previsto, para não precisar fazer check-in manual.
39. Como responsável, quero marcar uma ausência e liberar a sala, para permitir novo uso quando ninguém comparecer.
40. Como organizador, quero encerrar minha reunião antes do horário previsto, para liberar a sala.
41. Como responsável, quero encerrar antecipadamente qualquer reunião, para atualizar a disponibilidade.
42. Como responsável, quero bloquear uma sala para manutenção, limpeza ou evento, para impedir novas reservas no período.
43. Como responsável, quero ver reservas já confirmadas que coincidam com um bloqueio, para realocá-las ou cancelá-las conscientemente.
44. Como organizador, quero ver um alerta quando minha reserva confirmada coincidir com um bloqueio, para procurar uma solução.
45. Como usuário, quero relatar um problema na sala, para avisar sobre equipamento, limpeza ou outra condição.
46. Como responsável, quero acompanhar e resolver ocorrências, para manter as salas utilizáveis.
47. Como responsável, quero decidir se uma ocorrência exige bloqueio, para não tornar a sala indisponível por todo relato.
48. Como organizador, quero receber avisos internos de confirmação, alteração, cancelamento e lembrete, para acompanhar minhas reservas.
49. Como responsável, quero consultar mudanças e pendências na fila do painel, para agir conforme a prioridade.
50. Como administrador, quero ver o histórico de reservas e ações administrativas importantes, para entender alterações e decisões.
51. Como responsável, quero consultar ocupação calculada pelo tempo reservado, para avaliar o uso planejado das salas.
52. Como responsável, quero consultar cancelamentos e ausências, para identificar padrões de uso.
53. Como responsável, quero filtrar e exportar relatórios em CSV, para analisar os dados em planilhas.
54. Como administrador, quero configurar a futura conexão de canais por provedor, para ativar SMS, e-mail ou WhatsApp sem alterar as regras de reserva.
55. Como administrador, quero manter canais sem provedor desativados, para que o sistema não prometa mensagens que não consegue enviar.
56. Como administrador, quero preparar o vínculo futuro entre sala e calendário Google, para conectar a agenda sem trocar a fonte principal das reservas.
57. Como responsável, quero que falhas futuras de sincronização não cancelem reservas no CRASS, para manter a agenda interna confiável.
58. Como responsável, quero ser alertado quando alguém alterar diretamente um evento criado pelo CRASS no Google, para tratar a divergência sem importar a mudança automaticamente.
59. Como operador da instalação, quero implantar o CRASS com HTTPS e volumes persistentes, para disponibilizá-lo pela internet.
60. Como operador da instalação, quero fazer backup e restaurar banco e fotos, para recuperar o serviço após uma falha.

## Implementation Decisions

- Criar uma aplicação Next.js com TypeScript, uma API FastAPI, um processo de trabalho para tarefas agendadas e PostgreSQL. Distribuir uma instalação independente por organização com Docker Compose, HTTPS e volumes persistentes.
- Usar uma API REST para autenticação, usuários, prédios, salas, regras, reservas, bloqueios, ocorrências, relatórios e notificações. O cliente deve consumir essa API; permissões e validações serão aplicadas no servidor.
- Usar os perfis administrador, responsável e usuário. Administrador configura contas e regras; responsável gerencia todas as salas; usuário gerencia apenas as próprias reservas. Todos podem consultar os detalhes das reservas.
- Exigir troca da senha temporária no primeiro acesso. Oferecer TOTP opcional com códigos de recuperação. Sem provedor de e-mail, somente o administrador redefine o acesso.
- Uma reserva ocupa exatamente uma sala. Equipamentos são características da sala, não recursos com agenda separada. Regras gerais podem ser substituídas por configuração da sala; responsáveis obedecem às mesmas regras de reserva.
- Modelar estados de reserva pendente, confirmada, rejeitada, expirada, cancelada e ausência registrada. O estado de reunião em andamento decorre do relógio; não há ação de check-in.
- Persistir cada ocorrência de série para consultar disponibilidade. Uma série sem data final gera ocorrências em janela móvel de 12 meses; a expansão ocorre em trabalho agendado. Datas em conflito são registradas como ignoradas e mostradas ao usuário. Edição permite ocorrência isolada, esta e futuras, ou série inteira.
- Impedir transacionalmente a sobreposição de reservas pendentes ou confirmadas da mesma sala. Uma pendência bloqueia o horário até aprovação, rejeição ou prazo de expiração configurável. Aprovação de série alcança as ocorrências livres geradas na janela.
- Bloqueios impedem novas reservas, mas não cancelam reservas anteriores sobrepostas. Essas reservas continuam confirmadas e recebem marcação de conflito visível ao organizador e à pessoa responsável.
- Implementar mensageria com uma interface por canal e provedores registrados por injeção de dependência. O canal interno é funcional no primeiro lançamento; SMS, e-mail e WhatsApp têm contratos e configuração, mas não têm provedores reais nem envio ativo. WhatsApp futuro é somente para avisos.
- Preparar contrato para publicar eventos em calendários de sala, mantendo o CRASS como fonte principal. A integração Google real não pertence ao primeiro lançamento. Quando implementada, usará conta @gmail.com conectada por OAuth, um calendário por sala, credenciais por instalação e compartilhamento manual de acesso. Falha de publicação exige nova tentativa; edição feita no Google gera alerta, sem alterar a reserva interna.
- A interface usa painel inicial único, barra lateral em árvore com até dois níveis e ação de nova reserva visível. Itens variam conforme permissão. Relatórios usam tempo reservado para ocupação e exportam CSV.
- Registrar histórico das ações administrativas e mudanças relevantes de reservas. Definir backup e restauração de PostgreSQL e fotos no procedimento de implantação.

## Testing Decisions

- Como não existe aplicação nem suíte de testes no repositório, não há exemplos anteriores a seguir. Criar verificações sobre comportamento observável, evitando afirmar detalhes internos como nomes de funções ou consultas SQL.
- Usar a API com PostgreSQL real como principal ponto de teste para regras, permissões, aprovações, expiração, concorrência, recorrência, bloqueios e relatórios. Esse ponto cobre cliente e servidor sem multiplicar interfaces de teste para cada módulo.
- Cobrir no navegador os percursos de login, troca de senha, busca, reserva rápida, aprovação, edição, ausência, ocorrência e exportação CSV; verificar desktop, celular e navegação por teclado.
- Verificar duas tentativas simultâneas para a mesma sala e horário; apenas uma pode ocupar o intervalo. Verificar também pendência expirada, datas ignoradas em série, edição parcial de série e reserva confirmada sobreposta por bloqueio posterior.
- Verificar que canais externos desativados não tentam enviar mensagens e que a falta futura do Google não muda o estado da reserva.
- Validar instalação nova por Docker Compose, HTTPS, inicialização do primeiro administrador e restauração de backup.

## Out of Scope

- Envio real por SMS, e-mail ou WhatsApp e escolha de provedores para esses canais no primeiro lançamento.
- Sincronização real com Google Calendar no primeiro lançamento.
- Chat integrado, comandos por WhatsApp e reserva por dispositivo na porta da sala.
- Reserva de múltiplas salas ou de equipamentos independentes no mesmo pedido.
- Cadastro público de usuários e gestão de várias organizações na mesma instalação.

## Further Notes

- Esta especificação substitui o antigo escopo preliminar. O repositório agora tem remoto Git; esta especificação continua sendo a fonte de escopo da primeira entrega.
- A verificação completa da API em instalação descartável passou antes das correções da revisão. A compilação Next.js e a checagem de tipos passaram após essas correções. A nova execução com PostgreSQL e a inspeção visual dependem de retomar o Docker Desktop, que está pausado nesta máquina.
- A integração futura com uma conta @gmail.com é viável com calendários separados, mas cada organização precisará configurar OAuth para uso contínuo. Projetos OAuth em modo de teste têm limitações de validade de token, conforme a [documentação do Google](https://developers.google.com/identity/protocols/oauth2/production-readiness/overview).
