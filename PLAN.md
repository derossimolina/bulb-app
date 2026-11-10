# WYW — Plano de lançamento

Plano de **10/11/2026 (terça)** para pôr o WYW à venda até **13/11/2026 (sexta)**. Os requisitos (`REQ-…`) e os
critérios de aceite (`AC-…`) estão no [`SPEC.md`](SPEC.md), seção 12 (lançamento) e seção 8.1 (hospedagem); o
estado anterior do projeto está no [`NOTES.md`](NOTES.md).

**Como trabalhar:** uma tarefa (T-…) por branch e por PR para a `main`; cada tarefa começa pelos testes; o `pytest`
passa antes de qualquer merge; ao terminar um requisito, o status dele no spec muda de 🆕 para ✅.

## Onde estamos

| Pronto | Falta para vender |
|---|---|
| Site com busca, faixa de risco, previsão e avisos do INMET | Geolocalização (IP e aparelho) |
| Motor de risco em Python e JavaScript, com casos compartilhados | Tornado e rajadas calculados no servidor |
| Design system, três idiomas, temas claro e escuro | Contas, locais salvos, pagamento, alertas |
| Spec, notas e decisões D-1 a D-13 | Hospedagem no Lightsail, domínios, páginas legais |

O app Android (M3 a M5) fica para depois do lançamento: não há código e a conta do Google Play depende do D-U-N-S.

## O que só você pode fazer

Estas ações envolvem contas, dinheiro e chaves. Começar **hoje**, porque algumas têm espera.

| # | Ação | Até | Por que cedo |
|---|---|---|---|
| H-1 | Responder Q-10 a Q-15 do `SPEC.md` (preço, Open-Meteo, e-mail, limite de locais, razão social) | Ter | Sem resposta, vale a proposta do spec |
| H-2 | Ativar a conta do **Stripe** para cobrança real (dados da empresa e conta bancária) | Ter | A verificação pode levar dias |
| H-3 | Criar a instância no **Lightsail** (Micro-1GB, Ubuntu 24.04, São Paulo), IP estático e firewall | Qua, manhã | Tudo depende dela |
| H-4 | Na **Hostinger**: registros A de `clima` e `weather`; depois, SPF, DKIM e DMARC do provedor de e-mail | Qua, manhã | Propagação de DNS |
| H-5 | Contratar o plano comercial do **Open-Meteo** e criar a conta do provedor de **e-mail** | Qua | Chaves para o servidor |
| H-6 | Criar o robô do **Telegram** no BotFather | Qui | 5 minutos |
| H-7 | Gravar as chaves em `/opt/wyw/.env` na instância e nos segredos do GitHub | Qua e Qui | As chaves não passam pelo chat nem pelo repositório |
| H-8 | Testar num Android e num iPhone reais (AC-ALERTA-03, AC-GEO-02) | Sex, manhã | Web Push só se prova no aparelho |
| H-9 | Fazer uma assinatura real com o próprio cartão e cancelar | Sex, meio-dia | Prova do fluxo de cobrança |
| H-10 | Levar os textos de `/terms` e `/privacy` a uma pessoa habilitada | Antes de 20/11 | Data da primeira cobrança real (REQ-LEGAL-04) |

## Tarefas de código

"Modelo" indica com qual modelo vale a pena fazer cada tarefa (critério na seção seguinte).

| # | Tarefa | Requisitos | Modelo | Dia |
|---|---|---|---|---|
| T-01 | `/healthz`, gunicorn `gthread`, `ProxyFix`, variável `REDIRECT_TO` | INFRA-02, 06 | Sonnet | Ter |
| T-02 | Idioma por domínio, `hreflang` e `canonical` | WEB-04 | Sonnet | Ter |
| T-03 | `deploy/docker-compose.yml` (`app`, `worker`, `caddy`, volume), `Caddyfile`, GitHub Actions | INFRA-02, 04, 07 | Sonnet | Ter |
| T-04 | Primeiro deploy no Lightsail e conferência de AC-INFRA-01 e AC-WEB-04 | INFRA-01…05 | Sonnet, com você | Qua |
| T-05 | Local pelo IP (base DB-IP, crédito na tela Sobre) | GEO-01, 03, 04 | Sonnet | Qua |
| T-06 | Botão "Usar minha localização" em `wyw.js` | GEO-02, 03 | Sonnet | Qua |
| T-07 | Classificador de tornado em Python e cliente do Open-Meteo no servidor, com chave | ALERTA-02 | Sonnet | Qua |
| T-08 | Banco SQLite: esquema de 12.7 e camada de acesso | 12.7 | Sonnet | Qua |
| T-09 | Entrar por e-mail (link de uso único), sessão, CSRF, limite de tentativas, envio de e-mail | CONTA-01…03 | Sonnet, revisão forte | Qua |
| T-10 | Página `/conta` e locais salvos | CONTA-04…06 | Sonnet | Qui |
| T-11 | **Motor de alertas**: ciclo do verificador, regra de não repetição, fonte fora do ar, batimento | ALERTA-01, 03, 04, 07, 09 | Modelo mais forte | Qui |
| T-12 | Canal e-mail e texto do alerta nos três idiomas | ALERTA-05, 06 | Sonnet | Qui |
| T-13 | Manifesto, *service worker*, Web Push (VAPID) e instrução para iPhone | PWA-01…03 | Sonnet | Qui |
| T-14 | Stripe: Checkout, webhook, portal e situação da conta | PAG-01…04 | Sonnet, revisão forte | Qui |
| T-15 | Páginas `/precos`, `/terms` e `/privacy` (pt e en) | PAG-05, LEGAL-01…03 | Sonnet para as páginas; texto legal revisado | Qui |
| T-16 | Canal Telegram (robô, vínculo e webhook) | ALERTA-06 | Sonnet | Qui |
| T-17 | Alerta de teste na conta | ALERTA-08 | Sonnet | Qui |
| T-18 | Traduções pt e es das telas novas (`pybabel`) | REQ-WEB existentes | Sonnet | Sex |
| T-19 | Revisão de segurança e de código de tudo que entrou | NFR-06, 08 | Modelo mais forte | Sex |
| T-20 | Atualizar `README.md`, `NOTES.md` e os status no `SPEC.md` | — | Sonnet | Sex |

## O que fazer com o Sonnet 5.5

O Sonnet dá conta de quase todo o código deste plano, porque as tarefas são pequenas, seguem padrões conhecidos
(Flask, SQLite, Stripe Checkout, Web Push) e têm requisito e critério de aceite escritos. Ele rende mais quando
recebe **uma tarefa por sessão**, com o número da tarefa, os requisitos e a instrução de escrever os testes antes.

Pedido modelo:

> Implemente a tarefa T-05 do `PLAN.md`, seguindo os requisitos REQ-GEO-01, 03 e 04 do `SPEC.md`. Escreva os testes
> primeiro, sem acesso à rede. Trabalhe num branch próprio e abra um PR para a `main`.

**Fica bem no Sonnet 5.5** (18 das 20 tarefas, duas delas com revisão): infraestrutura em arquivos, rotas e páginas, geolocalização, banco,
conta, canais de envio, integração com o Stripe seguindo a documentação, traduções e documentação.

**Vale um modelo mais forte:**
- **T-11, o motor de alertas.** É a parte que não pode errar: uma regra de repetição mal feita gera alerta em
  dobro ou, pior, silêncio durante um risco real. Projete e revise com o modelo mais forte; o Sonnet pode escrever
  os testes a partir de AC-ALERTA-01 e 02.
- **T-19, a revisão final**, com `/security-review` e `/code-review` sobre o conjunto.
- **Revisão de T-09 e T-14.** O Sonnet implementa; outra sessão revisa o login e o webhook do Stripe, que são os
  dois pontos onde uma falha vira conta invadida ou assinatura grátis.
- **Diagnóstico de problemas em produção** que resistam a uma primeira tentativa.

**Não é trabalho para modelo nenhum:** as ações H-1 a H-10, a decisão de preço e a validação jurídica dos textos.

## Cronograma

### Terça, 10/11 — decidir e destravar
- Você: H-1 e H-2.
- Código: T-01, T-02, T-03 (tudo que não custa dinheiro nem depende de conta).

**Pronto quando:** os três PRs estão na `main` e o Stripe está em análise.

### Quarta, 11/11 — site no ar no endereço novo, com geolocalização
- Você, de manhã: H-3, H-4, H-5 e a primeira parte de H-7.
- Código: T-04 logo que o DNS propagar; em paralelo, T-05, T-06, T-07, T-08; à tarde, T-09.

**Pronto quando:** `https://clima.derossi.dev` abre em menos de 3 s já no local do visitante, e é possível entrar por
e-mail.

### Quinta, 12/11 — o produto pago
- Você: H-6 e o resto de H-7 (chaves de teste do Stripe, VAPID, Telegram).
- Código, nesta ordem: T-10, T-11, T-12, T-14, T-13, T-15, T-17, T-16.

**Pronto quando:** em produção, com o Stripe em modo de teste, uma conta assina, salva um local e recebe o alerta de
teste por e-mail e por push.

### Sexta, 13/11 — conferir e abrir
- Manhã: H-8, T-18, T-19, correções.
- **12h, decisão de lançar.** Critérios: AC-PAG-01, AC-ALERTA-01 e 02 passando; alerta de teste recebido em
  aparelho real; `/terms`, `/privacy` e `/precos` publicados; batimento do verificador em dia.
- Tarde: trocar para as chaves reais do Stripe, H-9, ligar o redirecionamento do Render (REQ-INFRA-06), T-20 e
  anunciar.

Como a assinatura começa com 7 dias grátis, **a primeira cobrança real só acontece em 20/11**. Essa semana serve para
corrigir o que aparecer com os primeiros usuários e para a leitura jurídica (H-10).

## Se o prazo apertar

Cortar nesta ordem, sem mexer no resto:

1. Telegram (T-16).
2. Plano anual (fica só o mensal).
3. Espanhol nas telas novas (ficam em português e inglês).
4. Local pelo IP (T-05); o botão de localização do aparelho continua.
5. Opção de receber o nível Atenção.

**Não se corta:** Lightsail e domínio, entrar por e-mail, Stripe, alerta por e-mail, alerta de teste, batimento,
termos e privacidade. Web Push é meta do lançamento; se falhar só no iPhone, lança com Android e a instrução de usar
e-mail ou Telegram.

Se o Stripe não ativar a tempo, o site abre na sexta com cadastro e teste grátis, e a cobrança é ligada quando a
conta for aprovada.

## Depois do lançamento

| Fase | Entrega | Situação |
|---|---|---|
| Semana 1 | Acompanhar entregas de alerta, spam, cancelamentos; leitura jurídica (H-10) | Até 20/11 |
| Render | Suspender o serviço 30 dias depois do redirecionamento | Dezembro |
| **M3** | App Android com o app aberto (REQ-APP-01 a 13) | A fazer |
| **M4** | Segundo plano e notificações no app (REQ-APP-20 a 34) | Depende do M3 |
| **M5** | Publicação no Google Play | Bloqueada pelo D-U-N-S |

O detalhamento de M3 a M5 está na versão anterior deste arquivo (commit `6ec6e40`).
