# WYW — Especificação

> **WYW** — "Weather is your Weather".
> Site e app Android de previsão do tempo com **nível de risco à vida** para quem permanece num local.

| | |
|---|---|
| Versão | 0.9 — lançamento comercial: geolocalização e assinatura WYW Alerta (seção 12, D-13) |
| Data | 10/11/2026 |
| Responsável | derossi research — [derossi.dev](https://derossi.dev) |
| Repositório | `derossimolina/bulb-app` |

Este documento orienta o desenvolvimento (*spec-driven*): cada mudança de código deve apontar para um requisito
(`REQ-…`) e ser validada pelos seus critérios de aceite (`AC-…`). Mudanças de comportamento começam por uma alteração
neste arquivo.

**Convenções.** "DEVE" é obrigatório; "PODE" é opcional. Valores "acima de" são estritamente maiores (`>`).
Status de cada requisito: ✅ implementado · 🆕 novo · 🔄 muda o que existe.

---

## 1. Visão geral

### 1.1 Objetivo
Informar, para uma cidade ou endereço, as condições do tempo e se **permanecer naquele local oferece risco à
segurança e à integridade física** da pessoa — e, no app, avisar com uma notificação quando esse risco existir onde
ela está.

### 1.2 Escopo
| Produto | Situação | Onde |
|---|---|---|
| Site (Flask) | Em produção em `bulb-app.onrender.com` | `app/` |
| App Android (Kotlin) | Novo | `android/` |
| Casos de teste do risco, compartilhados | Em uso | `spec/risk-cases.json` |
| **WYW Alerta** (assinatura de alertas pelo site) | Novo, lançamento em 13/11/2026 | seção 12 |

**Fora do escopo desta versão:** app iOS nativo, histórico de buscas no servidor, alertas sonoros próprios, anúncios,
plano para empresas, SMS e WhatsApp. Contas de usuário passam a existir, só para o WYW Alerta (seção 12).

### 1.3 Glossário
| Termo | Significado |
|---|---|
| Bulbo úmido (Tw) | Temperatura de bulbo úmido, fórmula de Stull (2011). |
| Indicador | Condição de perigo avaliada hora a hora (seção 4). |
| Janela de risco | A hora atual e as 3 horas seguintes (4 horários). |
| Horário | Uma hora cheia da série prevista, no fuso do local. |
| Aviso oficial | Aviso meteorológico do INMET para o município. |
| Aparelho | O navegador da pessoa (site) ou o celular (app). |

---

## 2. Fontes de dados

| Dado | Fonte | Quem consulta | Chave |
|---|---|---|---|
| Previsão e condições atuais | MET Norway Locationforecast 2.0 | Servidor (site) e app | Não; User-Agent identificável |
| CAPE, índice de levantamento, vento em 850/500 hPa, rajadas | Open-Meteo Forecast | **Aparelho** (navegador ou app) 🆕 | Não |
| Busca de cidade | Open-Meteo Geocoding | Servidor (site) e app | Não |
| Busca de endereço | Nominatim (site, pelo navegador) · `android.location.Geocoder` (app) 🆕 | Aparelho | Não |
| Avisos oficiais | INMET `apiprevmet3.inmet.gov.br/avisos/ativos` | Servidor (site) e app | Não |
| Código do município | Tabela IBGE embutida (`app/data/municipios_ibge.json`) | Servidor e app | — |
| Fuso horário por coordenada | `tzfpy` (servidor) · `TimeZone` do Android (app) 🆕 | — | — |

**Restrição C-1 (IP compartilhado).** No plano Free do Render o IP de saída é compartilhado: o Open-Meteo Forecast
(23/10/2026) e o Nominatim (02/11/2026) responderam `429` às chamadas do servidor. Por isso, essas duas APIs DEVEM
ser chamadas **do aparelho** (IP da pessoa), nunca do servidor.

**Restrição C-2 (privacidade).** Coordenadas enviadas ao servidor ou às APIs DEVEM ser arredondadas para 2 casas
decimais (~1 km). O servidor não guarda buscas; os logs de acesso podem conter a coordenada arredondada.

---

## 3. Requisitos — Site

### 3.1 Identidade
- **REQ-WEB-04 🆕** Idioma padrão por domínio (D-12): sem escolha da pessoa (parâmetro `lang` ou sessão),
  `clima.derossi.dev` abre em **português** e `weather.derossi.dev` em **inglês**; em outros endereços vale o idioma
  do navegador. Cada página traz `<link rel="alternate" hreflang="pt" | "en" | "x-default">` apontando para o mesmo
  caminho nos dois domínios e `<link rel="canonical">` para o domínio atual.
  - **AC-WEB-04** Sem cookie de sessão, `https://weather.derossi.dev/?city=Porto+Alegre` mostra a página em inglês e
    `https://clima.derossi.dev/?city=Porto+Alegre` em português; os dois têm os `hreflang` recíprocos.
- **REQ-WEB-03 ✅** O visual do site segue a seção 5 (design system Contexto v8, temas claro e escuro), mantendo o
  layout, as animações e as funcionalidades descritas nesta seção.
- **REQ-WEB-01 ✅** O nome do site DEVE ser **WYW** no título da página, no cabeçalho e no `<title>`.
- **REQ-WEB-02 ✅** O rodapé DEVE trazer "Copyright 2025-6 **derossi research**", com o link para
  `https://derossi.dev`.
  - **AC-WEB-02** O rodapé contém um `<a href="https://derossi.dev">` cujo texto inclui "derossi research".

### 3.2 Busca
- **REQ-WEB-10 ✅** Busca por cidade, aceitando a região depois da vírgula: país, estado ou UF (`Santa Maria, RS`).
  Entre cidades com o mesmo nome, vence a mais populosa.
- **REQ-WEB-11 ✅** Busca por **endereço** (rua, número, bairro). O navegador consulta o Nominatim (C-1) quando o
  texto tem número ou começa com um tipo de logradouro ("Rua", "Av." etc.) e envia ao servidor só `lat`, `lon`
  arredondados (C-2), a cidade, a UF e o país. O endereço aparece só no título, montado no navegador; não vai à
  URL nem ao servidor. Se o Nominatim não encontrar o endereço ou falhar, a
  busca usa a de cidades (REQ-WEB-10).
  - **AC-WEB-11a** "Av. Ipiranga 6681, Porto Alegre" mostra o risco para essa coordenada, com o rótulo do endereço.
  - **AC-WEB-11b** Com o Nominatim fora do ar, "Porto Alegre" continua funcionando pela busca de cidades.
- **REQ-WEB-12 ✅** A busca não recarrega a página; os resultados entram com animação, saindo de baixo do campo.

### 3.3 Condições atuais e previsão
- **REQ-WEB-20 ✅** Cards em uma única linha (faixa com rolagem lateral no celular): **Agora** (temperatura,
  condição, sensação), **bulbo úmido** (colorido pelo nível de 4.3), umidade relativa e ponto de orvalho,
  pressão (alta ≥ 1020 hPa, baixa ≤ 1008 hPa) e vento.
- **REQ-WEB-21 ✅** Previsão de 7 dias em lista expansível: mín./máx., condição, chuva (mm), umidade, pressão com
  tendência, vento máximo e bulbo úmido máximo.
- **REQ-WEB-22 ✅** Os cards de vento (atual e diário) DEVEM mostrar também as **rajadas**, obtidas do Open-Meteo
  pelo navegador (C-1). Sem esse dado, o campo não aparece.

### 3.4 Avisos oficiais
- **REQ-WEB-30 ✅** Avisos do INMET de hoje no card "Agora", com ícone e etiqueta do nível; avisos de outros dias
  como ícones na linha do dia e num card ao abrir o dia; vários avisos lado a lado.
- **REQ-WEB-31 ✅** Tipbox em todos os ícones de aviso (mouse, teclado e toque), com nível, período, riscos e
  instruções.

### 3.5 Risco à vida
- **REQ-WEB-40 ✅** Acima dos cards, o site DEVE mostrar o **nível de risco** do local (seção 4), calculado com os
  dados do servidor mais os do Open-Meteo obtidos pelo navegador.
- **REQ-WEB-41 ✅** Com nível **Risco à sua vida** ou **Extremo**, a faixa DEVE ter **fundo vermelho**, **ícone de
  alerta amarelo**, o título "**Risco à sua vida!**" e, abaixo, a descrição de cada indicador ativo (seção 4.5).
- **REQ-WEB-42 ✅** Com o indicador de tornado ativo, a faixa DEVE mostrar o **ícone de tornado**.
- **REQ-WEB-43 ✅** Toda exibição de risco DEVE trazer o aviso: "*Este indicador não substitui os alertas das
  autoridades e da Defesa Civil.*"
- **REQ-WEB-44 ✅** Se o navegador não conseguir os dados do Open-Meteo, o risco é calculado sem os indicadores
  de tornado e rajadas, e a faixa informa: "Indicador de tornado indisponível no momento".

---

## 4. Modelo de risco (site e app)

O mesmo modelo DEVE ser implementado em Python (servidor), JavaScript (complemento no navegador) e Kotlin (app),
e os três DEVEM passar nos casos de `spec/risk-cases.json` (seção 4.6).

### 4.1 Janela e horários
A avaliação é feita para cada horário `h0` (hora atual) a `h3` (3 horas depois), no fuso do local. Um indicador
está **ativo num horário** quando sua condição vale naquele horário. Avisos do INMET valem para os horários dentro
do período `início → fim` do aviso.

### 4.2 Indicadores

| ID | Indicador | Ativo no horário quando | Dados |
|---|---|---|---|
| **IND-CALOR** | Calor do ar, ao ar livre | temperatura do ar **> 35 °C** com sol (sol acima do horizonte **e** nebulosidade **< 75 %**) **ou** temperatura do ar **> 38 °C** em qualquer condição | MET (temperatura, nebulosidade); elevação solar calculada (NOAA) |
| **IND-TW** | Bulbo úmido | Tw **≥ 31 °C** (nível "Perigo" de 4.3) | MET (temperatura, umidade) |
| **IND-TEMP** | Tempestade (local aberto ou fechado) | símbolo de trovoada no horário (WMO 95–99) **ou** aviso INMET "Tempestade" de qualquer nível vigente | MET, INMET |
| **IND-VENTO** | Vento forte | vento médio ou rajada **> 60 km/h** **ou** aviso INMET "Vendaval" de nível Perigo ou Grande Perigo vigente **ou** aviso INMET "Ventos Costeiros" de nível Perigo ou Grande Perigo vigente **com o ponto avaliado dentro do polígono do aviso** (faixa litorânea; D-5) | MET (vento), Open-Meteo (rajada), INMET |
| **IND-TORNADO** | Possibilidade de tornado (local aberto ou fechado) | potencial de tornado **alto** (4.4) | Open-Meteo |

**Calor do ar (D-3).** Como não há como saber se a pessoa está ao ar livre, ao sol ou à sombra, IND-CALOR é
**um único indicador** (nunca conta duas vezes) e, sozinho, gera só **Atenção** com uma recomendação:

| Variante | Condição | Recomendação |
|---|---|---|
| Sol | > 35 °C, de dia, nebulosidade < 75 % | "Se estiver ao ar livre e ao sol, saia do sol e procure sombra ou um lugar fresco." |
| Sombra | > 38 °C (a qualquer hora) | "Calor insalubre mesmo à sombra: se estiver ao ar livre, procure um lugar fresco ou com ar condicionado." |

Quando as duas variantes valem, mostra-se só a de sombra (mais grave). O bulbo úmido (IND-TW) é um indicador
separado: calor do ar **e** bulbo úmido ≥ 31 °C no mesmo horário somam dois indicadores.

### 4.3 Níveis do bulbo úmido (convenção existente)
| Tw | Nível | Cor | Mensagem |
|---|---|---|---|
| < 23 °C | Normal | verde | "Temperatura normal." |
| ≥ 23 °C | Alerta | amarelo | "Alerta! Procure um lugar fresco." |
| ≥ 31 °C | Perigo | laranja | "Perigo! Procure um local com ar condicionado. Risco de vida para pessoas sensíveis." |
| ≥ 35 °C | Extremo | vermelho | "Risco de vida! Procure um lugar com ar condicionado imediatamente!" |

### 4.4 Potencial de tornado
Recupera o classificador removido no commit `7e6d4b1` (`app/meteo/indices.py` em `5bb8995`), por horário:
`WMAXSHEAR = √(2·CAPE) × cisalhamento superfície–500 hPa` (Taszarek et al., 2020).

| Potencial | Condição |
|---|---|
| Muito baixo | CAPE < 100 J/kg ou WMAXSHEAR < 400 |
| Baixo | demais casos |
| Moderado | WMAXSHEAR ≥ 800 e cisalhamento superfície–850 hPa ≥ 8 m/s |
| **Alto** | WMAXSHEAR ≥ 1200, cisalhamento superfície–850 hPa ≥ 12 m/s e índice de levantamento ≤ −4 |

Potencial **moderado** mostra o ícone de tornado só em modo informativo ("Possibilidade moderada de tornado"),
sem contar como indicador (D-2).

### 4.5 Nível de risco
| Nível | Regra | Exibição |
|---|---|---|
| **Sem risco** | nenhum indicador ativo na janela | faixa discreta: "Sem risco identificado nas próximas 3 horas" |
| **Atenção** | algum indicador ativo, mas nunca dois no mesmo horário | faixa amarela com os indicadores e, para IND-CALOR, a recomendação |
| **Risco à sua vida** | **dois ou mais indicadores ativos no mesmo horário** (exceto IND-TORNADO) | faixa vermelha, REQ-WEB-41 / REQ-APP-30 |
| **Extremo** | IND-TORNADO ativo em qualquer horário (basta ele, sozinho) | igual ao anterior, com ícone de tornado |

**Descrição dos indicadores ativos** (usada na faixa e na notificação), um por linha, com valor e horário, por
exemplo:
- "Bulbo úmido de 32 °C às 14h"
- "Tempestade prevista entre 14h e 16h (aviso INMET: Perigo)"
- "Vento de até 72 km/h às 15h"
- "Possibilidade de tornado às 16h"

### 4.6 Casos de teste compartilhados
`spec/risk-cases.json` lista entradas por horário e o nível esperado. Casos mínimos:

| # | Entradas (no mesmo horário, salvo indicação) | Esperado |
|---|---|---|
| 1 | 30 °C, Tw 22 °C, sem trovoada, vento 20 km/h | Sem risco |
| 2 | 36 °C, de dia, nebulosidade 20 % | Atenção (IND-CALOR, recomendação "sol") |
| 3 | 36 °C, de dia, nebulosidade 90 % | Sem risco |
| 4 | 39 °C, de dia, nebulosidade 10 % | Atenção (IND-CALOR, recomendação "sombra"); calor conta uma vez só |
| 5 | 39 °C, à noite | Atenção (IND-CALOR, recomendação "sombra") |
| 6 | Tw 31 °C e trovoada no mesmo horário | Risco à sua vida |
| 7 | Tw 31 °C em h0 e trovoada só em h2 | Atenção |
| 8 | Rajada 65 km/h e aviso INMET "Tempestade" vigente | Risco à sua vida |
| 9 | Vento 60 km/h exatos e trovoada | Atenção (60 não é "acima de 60") |
| 10 | Potencial de tornado alto em h3, nada mais | Extremo |
| 11 | Potencial de tornado moderado + Tw 32 °C | Atenção, com ícone informativo de tornado |
| 12 | Sem dados do Open-Meteo, Tw 33 °C e trovoada | Risco à sua vida; tornado "indisponível" |
| 13 | 36 °C, de dia, nebulosidade 20 %, Tw 31 °C | Risco à sua vida (IND-CALOR + IND-TW) |
| 14 | Aviso INMET "Ventos Costeiros" (Perigo) vigente, ponto fora do polígono do aviso, trovoada | Atenção (só IND-TEMP) |
| 15 | Aviso INMET "Ventos Costeiros" (Perigo) vigente, ponto dentro do polígono do aviso, trovoada | Risco à sua vida |

---

## 5. Design system (site e app)

O site e o app seguem o design system **Contexto v8** (artefato "Contexto" no Claude,
[claude.ai/artifact/6ThQ7KTG8djxUFBkF8zqPn](https://claude.ai/artifact/6ThQ7KTG8djxUFBkF8zqPn), revisão de
02/11/2026), com temas **claro e escuro** (D-8, D-9). Os valores estão copiados aqui para o repositório não depender
do artefato. Se o design system mudar, esta seção é atualizada primeiro.

### 5.1 Temas e cores
- **REQ-DS-01 ✅ Temas claro e escuro.** O tema **escuro** é o "Padrão" do design system; o **claro** é derivado da
  mesma paleta (D-9). Por padrão, segue a preferência do sistema; no site, um botão no cabeçalho alterna os temas e
  a escolha fica salva no navegador.

  | Papel | Escuro | Claro | Uso |
  |---|---|---|---|
  | `fundo` | `ink` `#0f0e0d` | `ivory` `#fafaf9` | Fundo da página e dos cards |
  | `faixa` | `g4` `#3a3835` | `marmore` `#ede6da` | Faixas: dia aberto, blocos internos, barra de navegação do app |
  | `texto` | `ivory` | `ink` | Texto principal, nome WYW, valores (18,46:1) |
  | `texto-apoio` | `g1` `#d6d4cf` | `g4` | Texto de apoio (13,02:1 · 11,19:1) |
  | `texto-meta` | `g2` `#a6a39c` | `g3` `#6b6862` | Rótulos e metadados (7,66:1 · 5,32:1); no claro, nunca sobre `faixa` (4,48:1) |
  | `borda` | `g3` | `g3` | Bordas de cards, campos e botões (3,47:1 · 5,32:1) |
  | `filete` | `g4` | `hair` `#c8c5be` | Divisórias decorativas |
  | `acento` | `ouro` `#c9964a` | `bronze` `#7a4a22` | Texto de destaque e item ativo (7,30:1 · 7,10:1) |
  | `acento-filete` | `ouro` | `ouro` | Só filetes e barras decorativos (no claro, 2,53:1: nunca texto) |

- **REQ-DS-05 ✅ Cores de risco (exceção semântica, D-6).** O design system proíbe vermelho e amarelo puro como cor
  de marca. No WYW, eles são permitidos **apenas para comunicar risco**, nunca como decoração, iguais nos dois temas:

  | Token WYW | Valor | Uso | Contraste |
  |---|---|---|---|
  | `risco-vida` | `#b3261e` | Fundo da faixa e da notificação "Risco à sua vida!" e do card de bulbo úmido no nível Extremo | `ivory` sobre ele: 6,26:1 |
  | `alerta-icone` | `#f5c518` | Ícone de alerta sobre `risco-vida` | 4,01:1 (ícone, mínimo 3:1) |
  | `atencao` | `#e8a64f` (= `ambar`) | Faixa "Atenção" e card de bulbo úmido no nível Alerta | `ink` sobre ele: 9,18:1 |
  | `perigo` | `#7a4a22` (= `bronze`) | Card de bulbo úmido no nível Perigo | `ivory` sobre ele: 7,10:1 |

  Bulbo úmido no nível Normal usa o card padrão, sem cor. `risco-vida` nunca aparece como texto, borda ou ícone
  sobre `ink` (2,95:1, abaixo do mínimo de 3:1).
- **REQ-DS-07 ✅ Gráficos.** A barra de temperatura dos dias usa gradiente `ardosia` `#5b6770` → `ambar` → `bronze`
  (decorativo); medidores (umidade) usam `texto-meta`. Os selos de pressão são neutros (letra A, B ou ≈ na cor de
  texto, borda `borda`): a letra carrega o significado, não a cor.

### 5.2 Tipografia
- **REQ-DS-02 ✅** Fontes SIL OFL (no site, pelo Google Fonts; no app, embutidas):
  - **EB Garamond SemiBold**: nome WYW, títulos de seção e de tela, em frase normal (não caixa alta).
  - **Inter**: todo o resto (valores, rótulos, textos), com algarismos tabulares nos números.
  - **Chapéu**: Inter 500, caixa alta, tracking 0,28em, para rótulos de card ("AGORA", "BULBO ÚMIDO").

### 5.3 Forma e movimento
- **REQ-DS-03 ✅** Cantos retos (0px) em cards, faixas, campos e botões; raio de 8px só em pílulas (etiquetas de
  nível de aviso). Cards sem sombra: fundo `fundo` com borda de 1px `borda`. Margem lateral de 16px no celular.
  As animações do site (resultados saindo de baixo da busca, acordeão) continuam, e todas respeitam
  "reduzir movimento" do sistema.

### 5.4 Nome e marcas
- **REQ-DS-04 ✅** "WYW" escrito em texto (EB Garamond SemiBold, cor `texto`), sem logo. Abaixo, "Weather is your
  Weather" no estilo chapéu, em `texto-meta`. Site e app não usam as marcas da Contexto (wordmark `contexto`, símbolo
  `{c}`, tagline) nem as cores da derossi.dev; o crédito "derossi research" aparece em texto (rodapé do site, tela
  Sobre do app).

### 5.5 Ícones
- **REQ-DS-06 ✅** Sem emoji na interface. No site, ícones do Font Awesome 6 (estilo sólido), na cor de texto do
  tema; no app, ícones desenhados (REQ-APP-61). Exceções: os ícones oficiais dos avisos do INMET e as bandeiras de
  idioma e de país, que são imagens.

---

## 6. Requisitos — App Android

### 6.1 Plataforma
- **REQ-APP-01 🆕** Kotlin, Jetpack Compose, `minSdk 31` (Android 12), `targetSdk` exigido pelo Google Play na
  data de publicação. Pacote: `dev.derossi.wyw` (D-4). Nome do app: **WYW** — "Weather is your Weather".
- **REQ-APP-02 🆕** O app funciona sem o servidor do site: consulta MET Norway, Open-Meteo e INMET direto do
  aparelho, com a tabela IBGE embutida. Respostas em cache por 15 min (previsão) e 10 min (avisos).
- **REQ-APP-03 🆕** Interface em português, inglês e espanhol, seguindo o idioma do sistema.

### 6.2 Telas
- **REQ-APP-10 🆕** **Início:** risco do local atual no topo (faixa de 4.5), seguido de "Agora", bulbo úmido,
  umidade, pressão, vento/rajadas e avisos do INMET de hoje, como no site.
- **REQ-APP-11 🆕** **Busca:** cidade ou endereço completo. Endereços pelo `android.location.Geocoder`; se ele não
  encontrar, busca de cidades do Open-Meteo. O resultado mostra o nível de risco do endereço (REQ-APP-30 não se
  aplica: não há notificação para endereços buscados).
- **REQ-APP-12 🆕** **Previsão de 7 dias** com os mesmos campos e ícones de aviso do site.
- **REQ-APP-13 🆕** **Sobre:** fontes de dados, aviso de 4.5/REQ-WEB-43, política de privacidade e créditos.

### 6.3 Localização e verificação em segundo plano
- **REQ-APP-20 🆕** Pede localização **aproximada** primeiro e, depois, localização **em segundo plano** em etapa
  separada, com uma tela explicando o motivo antes do pedido do sistema (exigência do Android 12 e do Google Play).
- **REQ-APP-21 🆕** Sem permissão em segundo plano, o app funciona normalmente, mas só avalia o risco com ele aberto
  e informa isso na tela de início.
- **REQ-APP-22 🆕** Com permissão, um `WorkManager` periódico (a cada 30 min, rede disponível) obtém a localização
  aproximada, avalia o risco (seção 4) e notifica conforme 6.4.
- **REQ-APP-23 🆕** A localização não sai do aparelho, exceto arredondada (C-2) nas consultas às APIs de tempo.

### 6.4 Notificação de risco
- **REQ-APP-30 🆕** Com nível **Risco à sua vida** ou **Extremo** no local atual, o app DEVE publicar uma
  notificação com:
  - **fundo vermelho** na área de conteúdo (layout próprio com `DecoratedCustomViewStyle`);
  - **ícone de alerta amarelo** (e ícone de tornado quando IND-TORNADO estiver ativo);
  - título "**Risco à sua vida!**";
  - abaixo, a descrição dos indicadores ativos (4.5);
  - a linha "*Não substitui os alertas das autoridades e da Defesa Civil.*"
- **REQ-APP-31 🆕** **Sem sinal sonoro extra:** canal "Risco à vida" com importância alta, som e vibração padrão do
  sistema (a pessoa pode alterá-los nas configurações), sem som próprio, sem alarme e sem tela cheia.
- **REQ-APP-32 🆕** Não repetir a notificação para o mesmo risco: só notificar de novo se o conjunto de indicadores
  mudar, se o nível subir ou depois de 3 h. Quando o risco acabar, remover a notificação.
- **REQ-APP-33 🆕** Tocar na notificação abre o app na tela de início com o detalhe do risco.
- **REQ-APP-34 🆕** Com nível **Atenção** por IND-CALOR no local atual, o app publica uma **notificação de
  recomendação** (estilo padrão do sistema, sem fundo vermelho, canal "Recomendações" de importância padrão) com a
  recomendação da variante (4.2) e o aviso sobre as autoridades. Segue as mesmas regras de repetição de REQ-APP-32.
- **AC-APP-30** Num aparelho com Android 12, simulando Tw 32 °C e trovoada no local atual: a notificação aparece
  com área vermelha, ícone amarelo, "Risco à sua vida!", as duas linhas de indicadores e o aviso sobre as
  autoridades; nenhuma segunda notificação é criada na verificação seguinte.

**Limitação conhecida.** O Android controla o cabeçalho das notificações (ícone pequeno, nome do app, hora); só a
área de conteúdo pode ser vermelha. Fundo totalmente colorido (`setColorized`) só é permitido para serviços em
primeiro plano e mídia, o que não se aplica aqui.

### 6.5 Publicação
- **REQ-APP-40 🆕** Publicação no Google Play: conta de desenvolvedor, política de privacidade publicada no site
  (`/privacy`), formulário de segurança de dados e declaração de localização em segundo plano com vídeo
  demonstrando o recurso.
- **REQ-APP-41 🆕** Até a conta do Google Play existir, o app é distribuído como APK de teste (assinado com a
  chave de upload definitiva, guardada fora do repositório).


### 6.6 Notificação, ícone e ilustrações do app
O visual do app segue a seção **5 — Design system** (antigos REQ-APP-50 a 54, agora REQ-DS-01 a 06). Aqui ficam só
os requisitos exclusivos do app.

- **REQ-APP-55 🆕 Notificação.** A área de conteúdo usa `risco-vida` de fundo, `alerta-icone` no ícone e `ivory` no
  texto, nos dois temas. Se o layout de notificação não aceitar as fontes embutidas, usa a fonte do sistema.
- **REQ-APP-56 🆕 Tema.** Segue o tema escuro ou claro do Android; a tela Sobre permite fixar um dos dois. Cores
  dinâmicas do Android (Material You) ficam desligadas.
- **REQ-APP-60 🆕 Ícone do app.** Um **raio no meio de uma nuvem**, em ícone adaptativo:
  - camada de fundo: `ink` chapado;
  - camada da frente: nuvem em contorno ou preenchimento `ivory` e raio em `ouro`, centralizados na área segura
    (66dp de 108dp);
  - camada monocromática (ícones temáticos do Android 13+): a mesma silhueta, nuvem e raio vazado;
  - sem texto e sem as marcas da Contexto.
- **REQ-APP-61 🆕 Ícones de tempo e de aviso.** Desenhados em traço único, na cor de texto do tema, no mesmo desenho
  do ícone do app; tornado na cor de texto e, na faixa de risco, `alerta-icone`. Os ícones dos avisos do INMET
  continuam sendo os oficiais, enviados pelo próprio INMET.
- **AC-APP-60** Na tela inicial do Android 12, o ícone mostra a nuvem com o raio sobre fundo escuro e fica
  legível nas máscaras circular, quadrada e "squircle".

---

## 7. Requisitos não funcionais
- **NFR-01** Uma busca deve responder em até 3 s no servidor aquecido (sem contar a partida a frio do Render Free).
- **NFR-02** Falha de uma fonte não derruba a página nem o app: os campos dela somem ou aparecem como
  indisponíveis.
- **NFR-03** Acessibilidade: faixa de risco com contraste AA, ícones com texto alternativo e tipbox acessível por
  teclado.
- **NFR-04** Testes: `pytest` no site; testes unitários (JUnit) do modelo de risco no app; os três motores de risco
  passam em `spec/risk-cases.json`. O motor em JavaScript roda no Node dentro do `pytest`
  (`tests/test_risk_js.py`), que confere nível, indicadores e frases contra o motor em Python.
- **NFR-05** Logs: erros de serviços externos registrados com código HTTP e corpo resumido.

---

## 8. Arquitetura

```
bulb-app/
├── app/                  site Flask (servidor)
│   ├── meteo/risk.py     motor de risco (Python)            ✅
│   ├── meteo/sun.py      elevação do sol (NOAA)             ✅
│   ├── services/risk_window.py  janela h0–h3 (MET + INMET)  ✅
│   ├── static/risk.js    motor de risco (JavaScript)        ✅
│   └── static/wyw.js     complemento no navegador: Open-Meteo (rajadas, tornado),
│                         busca de endereço (Nominatim)      ✅
├── android/              app Kotlin                         🆕
│   └── …/risk/           motor de risco (Kotlin)
├── spec/risk-cases.json  casos de teste compartilhados       ✅
└── SPEC.md
```

**Fluxo no site.** O servidor calcula os indicadores que dependem de MET e INMET e entrega, junto com a página, a
série horária da janela. O navegador busca no Open-Meteo os dados de rajada e tornado, completa os indicadores e
calcula o nível final, exibindo a faixa de risco.

**Fluxo no app.** Tudo no aparelho: localização → MET + Open-Meteo + INMET → motor de risco → tela e notificação.

### 8.1 Hospedagem: migração para o AWS Lightsail (decidida, D-10)

O app Android não depende do servidor (REQ-APP-02); a hospedagem afeta só o site e a futura política de privacidade
(`/privacy`, REQ-APP-40).

**Hoje (Render Free).** Container Docker, 512 MB e 0,15 vCPU, região Oregon. O serviço **dorme após 15 minutos sem
acesso** e a primeira visita espera a partida a frio (5 a 50 s); os caches em memória se perdem a cada parada. O IP de
saída é **compartilhado** com outros serviços, o que causou os 429 do Open-Meteo (23/10/2026) e do Nominatim
(02/11/2026) e motivou a restrição C-1.

**Consumo medido no Render** (06/11/2026): **~77 MB de memória** com 2 workers do gunicorn; **~10 MB de tráfego em 30
dias**. A página de resultados tem de 30 a 135 KB, e fontes, ícones e scripts de terceiros vêm de CDNs.

**Dimensionamento no Lightsail** (preços oficiais de 06/11/2026, em USD por mês):

| Componente | Memória estimada |
|---|---|
| Ubuntu 24.04 LTS (sistema) | 150–250 MB |
| Docker | 50–80 MB |
| App (gunicorn, 2 workers; medido) | ~80 MB, até ~120 MB em picos |
| Caddy (HTTPS automático com Let's Encrypt) | 20–40 MB |
| **Total** | **~300–490 MB** |

| Opção | Preço | Recursos | Avaliação |
|---|---|---|---|
| **Instância Linux Micro-1GB (IPv4)** — **recomendada** | **$7** | 1 GB, 2 vCPU, 40 GB SSD, 2 TB de transferência (1 TB em São Paulo) | Folga de ~50% de memória; IP estático próprio; sempre ligada |
| Instância Linux Nano-0.5GB (IPv4) | $5 | 0,5 GB, 2 vCPU, 20 GB SSD, 1 TB (0,5 TB em São Paulo) | Cabe, mas no limite: exige swap de 1 GB e pode travar em atualizações do sistema |
| Serviço de containers Nano | $7 | 512 MB, 0,25 vCPU compartilhada, 500 GB | HTTPS e deploy de imagem gerenciados, sem SSH; a documentação não garante IP de saída próprio, então o risco dos 429 pode continuar |
| Planos só IPv6 ($3,50 / $5) | — | — | **Inviáveis**: sem IPv4 de saída, o servidor não alcança APIs que só têm IPv4 |

- **REQ-INFRA-01 🆕** Instância **Linux Micro-1GB** na região **South America (São Paulo), `sa-east-1`**
  (menor latência para o Brasil; preço igual, com metade da franquia de transferência, muito acima do uso medido).
- **REQ-INFRA-02 🆕** Ubuntu 24.04 LTS com Docker Compose: o container atual do app (`Dockerfile`, sem mudanças) e o
  Caddy na frente, com HTTPS automático. Workers do gunicorn do tipo `gthread` (2 workers × 4 threads), porque as
  requisições esperam APIs externas.
- **REQ-INFRA-03 🆕** IP estático do Lightsail anexado (incluído no plano). Os domínios **`clima.derossi.dev`** e
  **`weather.derossi.dev`** (D-11) apontam para ele com registros A no DNS da Hostinger (servidores de nome
  `dns-parking.com`, onde está o `derossi.dev`). O Caddy emite um certificado Let's Encrypt para cada domínio; `.dev`
  exige HTTPS em todos os navegadores (HSTS pré-carregado) e não há registro CAA que impeça a emissão.
  Firewall do Lightsail: só 80 e 443 abertas; 22 restrita ao IP de quem administra.
- **REQ-INFRA-04 🆕** Deploy pelo GitHub Actions a cada merge na `main` (build da imagem, envio ao GitHub Container
  Registry e `docker compose pull && up -d` por SSH), mantendo o fluxo atual do Render.
- **REQ-INFRA-05 🆕** Snapshots automáticos diários da instância (cobrados à parte pelo Lightsail) e alerta de CPU e
  de status no próprio painel.
- **REQ-INFRA-06 🆕** Depois da migração, `bulb-app.onrender.com` redireciona (301) para `clima.derossi.dev`,
  mantendo o caminho e os parâmetros, por pelo menos 30 dias; depois o serviço do Render é suspenso.
- **AC-INFRA-01** Depois da migração: primeira visita em menos de 3 s (sem partida a frio, NFR-01), HTTPS válido nos
  dois domínios, e logs sem 429 das APIs de tempo por 7 dias.

**Ganhos esperados:** fim da partida a frio; caches em memória persistentes; IP próprio (a restrição C-1 pode ser
revista: o Open-Meteo e o Nominatim voltariam a ser viáveis no servidor, se for útil); dados no Brasil.
**Custos e trabalho:** US$ 7/mês (US$ 84/ano) mais snapshots; manutenção do sistema operacional (atualizações de
segurança automáticas com `unattended-upgrades`); configuração inicial de domínio, HTTPS e deploy.

---

## 9. Plano de entrega

| Marco | Conteúdo | Requisitos |
|---|---|---|
| **M1** ✅ | Nome WYW, rodapé derossi research, motor de risco em Python + `risk-cases.json`, faixa de risco (sem tornado/rajadas) | WEB-01, 02, 40, 41, 43, 44; seção 4 |
| **DS** ✅ | Design system Contexto v8 no site, temas claro e escuro, ícones no lugar de emoji | WEB-03; DS-01…07 |
| **M2** ✅ | Complemento no navegador: rajadas, tornado, busca de endereço | WEB-11, 22, 42, 44 |
| **M3** | App Android: telas, busca, risco com o app aberto, design system e ícone | APP-01…13, 21, 55, 56, 60, 61; DS-01…07 |
| **M4** | Segundo plano, notificação de risco e de recomendação | APP-20, 22, 23, 30…34, 41 |
| **M5** | Publicação no Google Play e política de privacidade — **bloqueado** até a conta de desenvolvedor (D-4) | APP-40 |
| **INFRA** | Migração do site para o AWS Lightsail (8.1), domínios `clima.derossi.dev` e `weather.derossi.dev` com idioma por domínio | INFRA-01…06; WEB-04 |
| **L1** | Lançamento comercial em 13/11/2026: geolocalização, contas, WYW Alerta, pagamento e páginas legais. Depende do INFRA e vem **antes** de M3 a M5 | seção 12 |

---

## 10. Decisões
| ID | Questão | Decisão (06/11/2026) |
|---|---|---|
| **D-1** | Grafia do nome | "WYW — Weather is your Weather". |
| **D-2** | Potencial de tornado moderado | Só ícone informativo; não conta como indicador. Só o potencial **alto** é indicador (extremo). |
| **D-3** | Calor ao sol e à sombra | Formam um único indicador, IND-CALOR. Sozinho, gera Atenção com recomendação ("se estiver ao ar livre e ao sol, saia"); nunca gera Risco à sua vida por si só. Bulbo úmido segue separado. |
| **D-4** | Pacote e conta do Google Play | Pacote `dev.derossi.wyw` (domínio derossi.dev; não depende da conta e é definitivo após a primeira publicação). A conta de desenvolvedor depende do D-U-N-S, previsto para daqui a no mínimo 30 dias: M3 e M4 seguem com APK de teste; M5 aguarda a conta. |
| **D-5** | "Ventos Costeiros" do INMET | Entra em IND-VENTO só quando o ponto avaliado está dentro do polígono do aviso (a faixa litorânea definida pelo INMET), e não apenas no município. |
| **D-6** | Cores de risco | Vermelho (`risco-vida`) e amarelo (`alerta-icone`), proibidos no design system, são uma exceção só para comunicar risco, porque REQ-WEB-41 e REQ-APP-30 os exigem. O ícone do app é um raio numa nuvem (REQ-APP-60). |
| **D-7** | Design system no site (Q-6) | ~~Só o app segue o design system.~~ Substituída por D-8. |
| **D-8** | Design system no site | O site também segue o design system Contexto v8 (seção 5), mantendo o layout, as animações e as funcionalidades. |
| **D-9** | Temas claro e escuro | Site e app têm os dois temas. O escuro é o "Padrão" do design system; o claro é derivado da mesma paleta (`ivory`, `ink`, `marmore`, `g3`, `g4`, acento `bronze`), com contraste medido. Padrão: preferência do sistema. |
| **D-10** | Hospedagem (Q-7) | Migrar o site do Render Free para o AWS Lightsail, instância Micro-1GB em São Paulo (US$ 7/mês): o custo compensa pelo fim da partida a frio e pelo IP próprio. |
| **D-11** | Domínios (Q-8) | `clima.derossi.dev` e `weather.derossi.dev`, os dois apontando para a instância. |
| **D-12** | Idioma por domínio (Q-9) | `clima.derossi.dev` abre em português e `weather.derossi.dev` em inglês quando a pessoa não escolheu o idioma, com `hreflang` entre os dois (REQ-WEB-04). |

| **D-13** | Monetização (10/11/2026) | Site continua grátis e ganha geolocalização. A receita vem da assinatura **WYW Alerta**, cobrada pelo Stripe: alertas de risco por e-mail, Telegram e notificação no celular (Web Push) para os locais salvos da pessoa. Exige login por e-mail, verificador periódico no servidor e a migração para o Lightsail (seção 12). |

### Questões em aberto
Cada uma traz uma proposta. Enquanto não houver resposta, a seção 12 foi escrita com a proposta.

| ID | Questão | Proposta |
|---|---|---|
| **Q-10** | Preço e período de teste | R$ 9,90 por mês ou R$ 99 por ano, 7 dias grátis com cartão, só em reais no lançamento. |
| **Q-11** | Licença do Open-Meteo (a API gratuita é só para uso não comercial) | Assinar o plano comercial e passar a chamá-lo do servidor, com chave. A alternativa é lançar os alertas sem tornado e rajadas. |
| **Q-12** | Provedor de e-mail | Um provedor transacional com ativação imediata (por exemplo, Resend). O Amazon SES começa em modo restrito e a liberação pode não sair até sexta. |
| **Q-13** | Limite de locais salvos por assinante | 5. |
| **Q-14** | Quem vende | Razão social, CNPJ e e-mail de contato que aparecem nos termos, na política de privacidade e no Stripe. |
| **Q-15** | Repositório público sob GPLv3 | Manter público. Não impede a venda do serviço, mas o código pode ser copiado. |

Novas dúvidas entram aqui como **Q-16** em diante, antes de virar código.

## 11. Referências
- Stull, R. (2011). Wet-Bulb Temperature from Relative Humidity and Air Temperature. *J. Appl. Meteor. Climatol.*
- Sherwood, S. C.; Huber, M. (2010). An adaptability limit to climate change due to heat stress. *PNAS* 107(21).
- Taszarek, M. et al. (2020). Severe convective storms across Europe and the United States. *J. Climate* 33.
- MET Norway Locationforecast 2.0 · Open-Meteo · INMET Alert-AS · Nominatim Usage Policy · Android notifications
  (custom layouts) e background location (Google Play policy).
- AWS Lightsail: preços (aws.amazon.com/lightsail/pricing), planos ("Lightsail bundles") e regiões ("Regions and
  Availability Zones in Lightsail"), consultados em 06/11/2026.

---

## 12. Lançamento comercial — WYW Alerta (L1)

Meta: site à venda em **sexta, 13/11/2026**. Decisão D-13; questões Q-10 a Q-15 na seção 10.

### 12.1 Produto

| | Grátis | WYW Alerta (pago) |
|---|---|---|
| Busca, faixa de risco, previsão de 7 dias, avisos do INMET | Sim | Sim |
| Abrir já no local da pessoa (IP ou localização do aparelho) | Sim | Sim |
| Locais salvos | — | Até 5 (Q-13) |
| Alerta quando houver risco num local salvo | — | E-mail, Telegram e notificação no celular |
| Verificação | Só com a página aberta | A cada 15 min, no servidor |

A promessa do plano pago é uma só: **avisar a pessoa quando o risco aparecer onde ela está ou onde estão as pessoas
de quem ela cuida, sem ela precisar abrir o site.**

**Fora do L1:** app Android (M3 a M5 continuam valendo, depois do lançamento), anúncios, plano para empresas, SMS,
WhatsApp, aviso de "risco encerrado", histórico de alertas na conta, outras moedas além do real.

### 12.2 Geolocalização (grátis)

- **REQ-GEO-01 🆕 Local pelo IP.** Ao abrir a página inicial sem busca, o servidor estima a cidade pelo IP e mostra o
  resultado dela, com o rótulo "Localização aproximada pelo seu IP" e as ações "Usar minha localização" e "Trocar".
  A consulta usa uma base local (DB-IP City Lite, CC BY 4.0, com o crédito exigido na tela Sobre), sem chamar
  serviço externo. O IP real vem do cabeçalho do proxy (Caddy), com `ProxyFix` limitado a um salto.
- **REQ-GEO-02 🆕 Local pelo aparelho.** O botão "Usar minha localização" chama `navigator.geolocation`. O navegador
  arredonda a coordenada para 2 casas (C-2), obtém o nome da cidade pelo Nominatim (C-1) e segue o fluxo de
  coordenadas que já existe (REQ-WEB-11). A permissão só é pedida depois do toque no botão.
- **REQ-GEO-03 🆕 Falhas.** IP privado, fora da base ou permissão negada: a página inicial aparece como hoje, com o
  campo de busca, sem mensagem de erro bloqueante.
- **REQ-GEO-04 🆕 Privacidade.** O IP não é gravado em banco nem associado à conta. A coordenada do aparelho só chega
  ao servidor arredondada.
- **AC-GEO-01** Com `X-Forwarded-For` de um IP de Porto Alegre, `GET /` mostra a faixa de risco de Porto Alegre e o
  rótulo de localização aproximada. Com IP `10.0.0.1`, mostra a página inicial vazia.
- **AC-GEO-02** No celular, tocar em "Usar minha localização" e permitir mostra o risco do local, e a URL enviada ao
  servidor tem `lat` e `lon` com no máximo 2 casas decimais.

### 12.3 Site instalável e notificação no celular

- **REQ-PWA-01 🆕** `manifest.webmanifest` (nome WYW, cores `ink` e `ivory`, ícone de REQ-APP-60 em 192 e 512 px e
  versão mascarável) e um *service worker* em `/sw.js` que trata `push` e `notificationclick`. Sem cache offline de
  previsão: dado de risco velho é pior que nenhum.
- **REQ-PWA-02 🆕** Web Push com chaves VAPID. A inscrição do aparelho é enviada ao servidor só por quem está logado.
  No iPhone, a página da conta explica que é preciso "Adicionar à Tela de Início" antes de ativar (iOS 16.4 ou mais
  novo).
- **REQ-PWA-03 🆕** A notificação traz o título "Risco à sua vida!" (ou "Atenção"), as linhas de indicadores de 4.5,
  o nome do local e, ao toque, abre o site nesse local. Usa o som e a vibração padrão do sistema (como REQ-APP-31).

### 12.4 Conta

- **REQ-CONTA-01 🆕 Entrar por e-mail, sem senha.** A pessoa informa o e-mail e recebe um link assinado, válido por
  15 minutos e de uso único. A resposta da tela é a mesma exista ou não a conta.
- **REQ-CONTA-02 🆕 Sessão.** Cookie `Secure`, `HttpOnly`, `SameSite=Lax`, com 30 dias. Todo formulário com `POST`
  tem proteção contra CSRF.
- **REQ-CONTA-03 🆕 Limite de tentativas.** No máximo 5 pedidos de link por hora por e-mail e por IP.
- **REQ-CONTA-04 🆕 Página `/conta`.** Situação da assinatura, locais salvos, canais ativos, opção de receber também
  o nível Atenção (desligada por padrão), botão "Enviar alerta de teste", link para o portal do Stripe e "Excluir
  minha conta".
- **REQ-CONTA-05 🆕 Locais salvos.** Até 5, cada um com rótulo ("Casa", "Mãe"), coordenada arredondada (C-2),
  cidade, UF, país, código IBGE e fuso. Um local é salvo a partir de um resultado de busca ou da localização do
  aparelho.
- **REQ-CONTA-06 🆕 Exclusão.** "Excluir minha conta" cancela a assinatura no Stripe e apaga e-mail, locais, canais e
  estado de alertas na hora.
- **AC-CONTA-01** Um link usado pela segunda vez, ou depois de 15 minutos, não abre sessão e leva à tela de entrada.

### 12.5 Pagamento

- **REQ-PAG-01 🆕** Stripe Checkout em modo assinatura, com dois preços (mensal e anual, Q-10) e 7 dias de teste. Os
  identificadores dos preços e as chaves ficam em variáveis de ambiente, nunca no repositório.
- **REQ-PAG-02 🆕** O estado da assinatura vem **só** do webhook do Stripe, com a assinatura do evento conferida e
  cada evento processado uma única vez (identificador guardado). Eventos tratados: `checkout.session.completed`,
  `customer.subscription.updated`, `customer.subscription.deleted` e `invoice.payment_failed`.
- **REQ-PAG-03 🆕** Recebem alertas as contas em teste, ativas ou com pagamento em nova tentativa. Assinatura
  cancelada ou não paga para os alertas e mantém a conta e os locais.
- **REQ-PAG-04 🆕** Trocar cartão, mudar de plano e cancelar acontecem no portal do cliente do Stripe.
- **REQ-PAG-05 🆕** Página `/precos` (`/pricing` em inglês) com o que é grátis, o que é pago, o preço, o teste de 7
  dias, o direito de arrependimento e o aviso de REQ-WEB-43.
- **AC-PAG-01** No modo de teste do Stripe: assinar com o cartão de teste leva a conta a "em teste" em até 1 minuto;
  cancelar pelo portal leva a "cancelada" e os alertas param no ciclo seguinte; reenviar o mesmo evento não muda
  nada.

### 12.6 Alertas

- **REQ-ALERTA-01 🆕 Verificador.** Um processo separado do site (serviço `worker` no Docker Compose, mesma imagem)
  roda a cada 15 minutos e avalia todos os locais ativos de contas com direito a alerta. Locais com a mesma
  coordenada arredondada são consultados uma vez só.
- **REQ-ALERTA-02 🆕 Modelo completo no servidor.** O verificador usa o modelo da seção 4 inteiro, com tornado e
  rajadas. Para isso o classificador de tornado (4.4), hoje só em `risk.js`, ganha uma versão em Python que passa
  nos casos de `spec/risk-cases.json`, e o Open-Meteo passa a ser chamado do servidor com a chave do plano comercial
  (Q-11). A restrição C-1 deixa de valer para o Open-Meteo no Lightsail; o Nominatim continua só no navegador.
- **REQ-ALERTA-03 🆕 Quando avisar.** Nível **Risco à sua vida** ou **Extremo**: sempre, em todos os canais ativos
  da conta. Nível **Atenção**: só para quem ligou a opção.
- **REQ-ALERTA-04 🆕 Sem repetição** (mesma regra de REQ-APP-32). Para o mesmo local, só avisar de novo se o conjunto
  de indicadores mudar, se o nível subir ou depois de 3 horas. O estado fica no banco, por local.
- **REQ-ALERTA-05 🆕 Conteúdo.** Título do nível, nome do local, descrição dos indicadores (4.5), avisos do INMET
  vigentes, o aviso sobre as autoridades (REQ-WEB-43), link para o site nesse local e link para gerenciar ou
  cancelar os alertas. No idioma da conta.
- **REQ-ALERTA-06 🆕 Canais.** E-mail (sempre ativo, é o próprio login), Web Push (12.3) e Telegram: um robô do WYW,
  ligado à conta por um link `t.me/<robô>?start=<código>`; o webhook do Telegram confere o cabeçalho secreto.
  A falha de um canal não impede os outros; inscrição de push expirada (404 ou 410) é removida.
- **REQ-ALERTA-07 🆕 Fonte fora do ar.** Sem MET Norway, o local é pulado no ciclo e o erro é registrado. Sem
  Open-Meteo, o risco é avaliado sem tornado e rajadas e a mensagem diz "indicador de tornado indisponível" (como
  REQ-WEB-44). Nunca se envia alerta com dado de mais de 1 hora.
- **REQ-ALERTA-08 🆕 Alerta de teste.** O botão da conta envia, na hora, uma mensagem marcada como "TESTE" a todos
  os canais ativos e mostra o resultado de cada um.
- **REQ-ALERTA-09 🆕 Batimento.** O verificador grava a hora de cada ciclo completo. `/healthz` responde 503 quando o
  último ciclo tem mais de 30 minutos, para um monitor externo avisar quem administra.
- **AC-ALERTA-01** Com dados simulados (Tw 32 °C e trovoada em h1) num local salvo de conta ativa: um ciclo envia
  um alerta por canal ativo, com as duas linhas de indicadores e o aviso sobre as autoridades; o ciclo seguinte não
  envia nada; trocar a trovoada por rajada de 70 km/h envia de novo.
- **AC-ALERTA-02** A mesma simulação numa conta cancelada não envia nada.
- **AC-ALERTA-03** Num Android e num iPhone reais, o alerta de teste chega por push, e-mail e Telegram em menos de
  1 minuto.

### 12.7 Dados guardados

SQLite em volume do Docker na instância (modo WAL), com cópia diária do arquivo além do snapshot (REQ-INFRA-05).

| Tabela | Conteúdo |
|---|---|
| `user` | e-mail, idioma, cliente e situação no Stripe, fim do período, opção "Atenção" |
| `location` | conta, rótulo, lat/lon com 2 casas, cidade, UF, país, IBGE, fuso |
| `channel` | conta, tipo (push ou Telegram), endereço da inscrição ou do chat |
| `alert_state` | por local: nível, indicadores e hora do último aviso |
| `stripe_event` | identificadores de eventos já processados |
| `login_token` | códigos de entrada já usados, até expirarem |

Não se guardam: IP, endereço digitado, coordenada exata, dados de cartão (ficam no Stripe) nem o texto dos alertas
enviados.

### 12.8 Páginas legais e conformidade

- **REQ-LEGAL-01 🆕** `/privacy` em português e inglês: o que é coletado (12.7), para quê, com quem é compartilhado
  (Stripe, provedor de e-mail, Telegram, serviços de push do navegador, AWS), por quanto tempo, como excluir e o
  contato do responsável (Q-14). Atende também REQ-APP-40.
- **REQ-LEGAL-02 🆕** `/terms` em português e inglês: o serviço é informativo e não substitui a Defesa Civil nem as
  autoridades; a entrega do alerta depende de terceiros e não é garantida; preço, renovação, cancelamento e
  arrependimento em 7 dias com reembolso integral; quem vende (Q-14).
- **REQ-LEGAL-03 🆕** O aceite dos termos é registrado no checkout. Créditos das fontes na tela Sobre: MET Norway
  (CC BY 4.0), Open-Meteo, INMET, OpenStreetMap e DB-IP.
- **REQ-LEGAL-04 🆕** Os textos legais DEVEM ser lidos por uma pessoa habilitada antes da primeira cobrança real
  (20/11/2026, fim do primeiro período de teste). Vender alerta de risco à vida traz responsabilidade que um aviso
  no rodapé não elimina.

### 12.9 Operação

- **NFR-06 🆕** Segredos (Stripe, VAPID, Telegram, e-mail, Open-Meteo, `SECRET_KEY`) só em `/opt/wyw/.env` na
  instância e nos segredos do GitHub Actions.
- **NFR-07 🆕** Um alerta sai em até 20 minutos depois de a condição entrar na janela de risco.
- **NFR-08 🆕** Testes: tudo de 12.2 a 12.6 coberto por `pytest` sem rede (Stripe, e-mail, push e Telegram
  simulados); os ACs com aparelho real são conferidos à mão e anotados no PR.
- **REQ-INFRA-07 🆕** O Compose passa a ter três serviços (`app`, `worker`, `caddy`) e um volume para o banco e a
  base de IPs. O plano Micro-1GB continua suficiente.

### 12.10 Custos recorrentes (a confirmar na contratação)

| Item | Valor |
|---|---|
| AWS Lightsail Micro-1GB | US$ 7 por mês, mais snapshots |
| Open-Meteo, plano comercial | da ordem de € 29 por mês na última consulta; confirmar no site |
| Provedor de e-mail | plano gratuito deve bastar no início; confirmar limites |
| Stripe | taxa por transação; sem mensalidade |
| Telegram, Web Push, DB-IP Lite | sem custo |

Estimativa: o custo fixo se paga com algo entre 25 e 30 assinantes mensais, dependendo do câmbio e das taxas.

### 12.11 Riscos do lançamento

| Risco | Efeito | Resposta |
|---|---|---|
| Ativação da conta Stripe demora | Sem cobrança na sexta | Começar hoje. Se não sair, lançar com lista de espera e teste grátis, e ligar a cobrança quando ativar. |
| Alerta falso ou alerta que não chega | Perda de confiança; risco jurídico | Mesma regra testada do site, alerta de teste, batimento, termos claros, primeira cobrança só em 20/11. |
| Web Push no iPhone | Canal não funciona para parte das pessoas | Instrução de instalação; e-mail e Telegram cobrem. |
| E-mail caindo em spam | Alerta não visto | SPF, DKIM e DMARC no `derossi.dev` antes do lançamento. |
| Prazo | Entrega incompleta | Ordem de corte definida no `PLAN.md`. |
