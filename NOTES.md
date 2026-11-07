# WYW — Notas do projeto

Retrato do projeto em **07/11/2026**, antes da troca do Windows para o Arch Linux (HefOS). Serve para retomar o
trabalho sem depender do histórico das conversas. A fonte da verdade dos requisitos é o [`SPEC.md`](SPEC.md) (v0.8);
o plano de continuação está em [`PLAN.md`](PLAN.md).

## Em uma frase

**WYW — "Weather is your Weather"** é um site (e, em breve, um app Android) de previsão do tempo que mostra o
**nível de risco à vida** de permanecer num local nas próximas 3 horas, com os avisos oficiais do INMET para o
Brasil. Responsável: derossi research ([derossi.dev](https://derossi.dev)).

## Estado atual

| Item | Situação |
|---|---|
| Site em produção | https://bulb-app.onrender.com (Render Free, Docker, região Oregon) |
| Repositório | [derossimolina/bulb-app](https://github.com/derossimolina/bulb-app), público, branch `main` (último merge: PR #16, `ef4849d`) |
| Testes | 84 passando (`pytest`, incluindo o motor de risco em JavaScript rodando no Node) |
| Requisitos do spec | 23 implementados ✅ · 29 pendentes 🆕 (app Android, infraestrutura e REQ-WEB-04) |
| Marcos concluídos | **M1** (risco no site), **DS** (design system e temas), **M2** (rajadas, tornado e endereço no navegador) |
| Próximos marcos | **INFRA** (AWS Lightsail), **M3** (app Android), **M4** (segundo plano e notificações), **M5** (Google Play, bloqueado) |
| Questões em aberto | Nenhuma (decisões D-1 a D-12 registradas no `SPEC.md`, seção 10) |

### O que o site faz hoje
- Busca por **cidade** (`Santa Maria, RS`) no servidor ou por **endereço** (`Av. Ipiranga 6681, Porto Alegre`) no
  navegador.
- **Faixa de risco à vida** (seção 4 do spec): calor, bulbo úmido, tempestade, vento forte e tornado; dois indicadores
  no mesmo horário (ou tornado alto) mostram "Risco à sua vida!" em vermelho com ícone amarelo.
- Cards em uma linha: Agora, bulbo úmido (colorido pelo nível), umidade, pressão, vento e rajadas.
- Previsão de 7 dias em lista expansível; avisos do INMET com ícones e tipbox.
- Design system **Contexto v8**, temas claro e escuro, português, inglês e espanhol.

### Arquitetura em resumo

```
app/
  meteo/        cálculos puros: risk.py (motor de risco), wetbulb.py, indices.py (pressão), sun.py, wmo.py
  services/     MET Norway, geocodificação Open-Meteo, INMET, janela de risco (risk_window.py), HTTP com cache
  static/       style.css (design system), risk.js (motor em JS), wyw.js (complemento no navegador)
  templates/    base.html, index.html, partials/
  translations/ pt e es
spec/risk-cases.json   18 casos de teste do risco, válidos para Python, JavaScript e Kotlin
tests/                 pytest (+ tests/js/run_cases.js para o motor em JS)
SPEC.md · NOTES.md · PLAN.md · Dockerfile · render.yaml
```

**Quem consulta o quê**

| Fonte | Para | Quem chama |
|---|---|---|
| MET Norway Locationforecast 2.0 | Previsão e condições atuais | Servidor |
| Open-Meteo Geocoding | Busca de cidades | Servidor |
| INMET (`apiprevmet3.inmet.gov.br/avisos/ativos`) | Avisos oficiais | Servidor |
| Open-Meteo Forecast | Rajadas, CAPE, índice de levantamento, vento em altitude (tornado) | **Navegador** |
| Nominatim (OpenStreetMap) | Busca por endereço | **Navegador** |

**Por que algumas chamadas saem do navegador (restrição C-1):** no Render Free o IP de saída é compartilhado, e tanto
o Open-Meteo Forecast (23/10/2026) quanto o Nominatim (02/11/2026) responderam `429` a todas as chamadas do servidor.
No navegador, a chamada sai do IP de quem acessa. Com o Lightsail (IP próprio), essa restrição pode ser revista.

**Privacidade (C-2):** o servidor recebe só coordenadas arredondadas (~1 km) e a cidade; o endereço digitado fica no
navegador.

## Decisões

### Registradas no `SPEC.md` (seção 10)

| ID | Decisão |
|---|---|
| D-1 | Nome: "WYW — Weather is your Weather". |
| D-2 | Tornado com potencial moderado só como ícone informativo; só o potencial alto é indicador (extremo). |
| D-3 | Calor ao sol (> 35 °C) e à sombra (> 38 °C) formam um indicador só (IND-CALOR); sozinho gera Atenção com recomendação. |
| D-4 | Pacote Android `dev.derossi.wyw`; APK de teste até existir a conta do Google Play (depende do D-U-N-S). |
| D-5 | "Ventos Costeiros" do INMET só conta dentro do polígono do aviso (faixa litorânea). |
| D-6 | Vermelho e amarelo (proibidos no design system) só para comunicar risco. |
| D-7 | ~~Só o app segue o design system~~ (substituída pela D-8). |
| D-8 | O site também segue o design system Contexto v8. |
| D-9 | Temas claro e escuro; o claro é derivado da paleta da Contexto, com contraste medido. |
| D-10 | Migrar o site para o AWS Lightsail (instância Micro-1GB, São Paulo, US$ 7/mês). |
| D-11 | Domínios `clima.derossi.dev` e `weather.derossi.dev`. |
| D-12 | `clima` abre em português e `weather` em inglês quando não houver escolha de idioma, com `hreflang`. |

### Anteriores ao spec (contexto das escolhas)
- **MET Norway** é a fonte única de previsão (PR #5): o Open-Meteo no servidor levava `429` pelo IP compartilhado.
- **Nominatim no servidor foi abandonado** (PRs #7 e #8): ele bloqueia o IP do Render e atrasava cada busca; a
  geocodificação de cidades usa o Open-Meteo, e o Nominatim só é chamado pelo navegador, para endereços.
- **Rajadas medidas do INMET** (estações automáticas) exigem chave de acesso, então não são usadas.
- **Avisos do INMET** casam com o município pelo código IBGE (tabela embutida em `app/data/`), com o polígono do aviso
  como reserva.
- Bulbo úmido pela fórmula de Stull (2011), níveis 23 / 31 / 35 °C.

## Ambiente e acessos

| Item | Onde | Observação |
|---|---|---|
| Código | GitHub `derossimolina/bulb-app` | Tudo na `main`, nada pendente |
| Hospedagem atual | Render, workspace "Pessoal e Doutorado", serviço `bulb-app` (`srv-cu9bbr23esus73b2igi0`) | Deploy automático a cada merge na `main` |
| `SECRET_KEY` | Variável de ambiente no Render | Gerada pelo blueprint (`render.yaml`); no Lightsail, gerar uma nova |
| DNS do `derossi.dev` | Hostinger (servidores `dns-parking.com`) | `derossi.dev` aponta para o Render; `clima.` e `weather.` ainda não existem |
| Design system | Artefato "Contexto" no Claude | Valores copiados no `SPEC.md`, seção 5 |
| Conta Google Play | Ainda não existe | Aguarda o D-U-N-S (previsão: 30 dias ou mais) |
| Histórico das conversas | `D:\claude-sessions\55d524f3-61c9-4003-98ef-34b6cba1060c.jsonl` (+ pasta de anexos) | Copiar para fora do disco antes de formatar |

**Não precisa ser levado:** `.env` (só a `API_KEY` antiga do OpenWeatherMap, sem uso) e `.venv` (recriável).

## Pendências e riscos conhecidos
- **Termos de uso:** a API gratuita do Open-Meteo é para uso não comercial, e o Nominatim pede no máximo 1 requisição
  por segundo e identificação. Rever os termos antes da publicação na loja ou se houver monetização.
- **Fuso de Fernando de Noronha:** a geocodificação do Open-Meteo informa o fuso de Recife (UTC−3) em vez de UTC−2;
  só desloca em uma hora a virada do dia na previsão de lá.
- **Plano Free do Render:** o serviço dorme após 15 minutos e a primeira visita espera de 5 a 50 s (resolvido pelo
  marco INFRA).
- **Docker no Windows:** o armazenamento estava no `C:` com pouco espaço; no Arch, o Docker roda nativo e o problema
  deixa de existir.
