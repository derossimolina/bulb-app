# WYW — Especificação

> **WYW** — "Weather is your Wheather" *(grafia a confirmar, ver Q-1)*.
> Site e app Android de previsão do tempo com **nível de risco à vida** para quem permanece num local.

| | |
|---|---|
| Versão | 0.1 (rascunho para revisão) |
| Data | 06/11/2026 |
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
| Casos de teste do risco, compartilhados | Novo | `spec/risk-cases.json` |

**Fora do escopo desta versão:** iOS, contas de usuário, histórico de buscas no servidor, alertas sonoros próprios.

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
- **REQ-WEB-01 🔄** O nome do site DEVE ser **WYW** no título da página, no cabeçalho e no `<title>`.
- **REQ-WEB-02 🔄** O rodapé DEVE trazer "Copyright 2025-6 **derossi research**", com o link para
  `https://derossi.dev`.
  - **AC-WEB-02** O rodapé contém um `<a href="https://derossi.dev">` cujo texto inclui "derossi research".

### 3.2 Busca
- **REQ-WEB-10 ✅** Busca por cidade, aceitando a região depois da vírgula: país, estado ou UF (`Santa Maria, RS`).
  Entre cidades com o mesmo nome, vence a mais populosa.
- **REQ-WEB-11 🆕** Busca por **endereço** (rua, número, bairro). O navegador consulta o Nominatim (C-1) e envia
  ao servidor só `lat`, `lon` (C-2) e um rótulo para exibição. Se o Nominatim não encontrar o endereço ou falhar, a
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
- **REQ-WEB-22 🆕** Os cards de vento (atual e diário) DEVEM mostrar também as **rajadas**, obtidas do Open-Meteo
  pelo navegador (C-1). Sem esse dado, o campo não aparece.

### 3.4 Avisos oficiais
- **REQ-WEB-30 ✅** Avisos do INMET de hoje no card "Agora", com ícone e etiqueta do nível; avisos de outros dias
  como ícones na linha do dia e num card ao abrir o dia; vários avisos lado a lado.
- **REQ-WEB-31 ✅** Tipbox em todos os ícones de aviso (mouse, teclado e toque), com nível, período, riscos e
  instruções.

### 3.5 Risco à vida
- **REQ-WEB-40 🆕** Acima dos cards, o site DEVE mostrar o **nível de risco** do local (seção 4), calculado com os
  dados do servidor mais os do Open-Meteo obtidos pelo navegador.
- **REQ-WEB-41 🆕** Com nível **Risco à sua vida** ou **Extremo**, a faixa DEVE ter **fundo vermelho**, **ícone de
  alerta amarelo**, o título "**Risco à sua vida!**" e, abaixo, a descrição de cada indicador ativo (seção 4.5).
- **REQ-WEB-42 🆕** Com o indicador de tornado ativo, a faixa DEVE mostrar o **ícone de tornado**.
- **REQ-WEB-43 🆕** Toda exibição de risco DEVE trazer o aviso: "*Este indicador não substitui os alertas das
  autoridades e da Defesa Civil.*"
- **REQ-WEB-44 🆕** Se o navegador não conseguir os dados do Open-Meteo, o risco é calculado sem os indicadores
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
| **IND-SOL** | Calor ao sol, ao ar livre | temperatura do ar **> 35 °C** **e** sol acima do horizonte **e** nebulosidade **< 75 %** | MET (temperatura, nebulosidade); elevação solar calculada (NOAA) |
| **IND-SOMBRA** | Calor à sombra, ao ar livre | temperatura do ar **> 38 °C** | MET |
| **IND-TW** | Bulbo úmido | Tw **≥ 31 °C** (nível "Perigo" de 4.3) | MET (temperatura, umidade) |
| **IND-TEMP** | Tempestade (local aberto ou fechado) | símbolo de trovoada no horário (WMO 95–99) **ou** aviso INMET "Tempestade" de qualquer nível vigente | MET, INMET |
| **IND-VENTO** | Vento forte | vento médio ou rajada **> 60 km/h** **ou** aviso INMET "Vendaval"/"Ventos Costeiros" de nível Perigo ou Grande Perigo vigente | MET (vento), Open-Meteo (rajada), INMET |
| **IND-TORNADO** | Possibilidade de tornado (local aberto ou fechado) | potencial de tornado **alto** (4.4) | Open-Meteo |

**Observação.** A temperatura do ar das previsões é medida à sombra. Por isso, de dia com sol e acima de 38 °C,
IND-SOL e IND-SOMBRA ficam ativos juntos e, sozinhos, já resultam em "Risco à sua vida" (ver Q-3).

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

Potencial **moderado** mostra o ícone de tornado em modo informativo, sem disparar risco (ver Q-2).

### 4.5 Nível de risco
| Nível | Regra | Exibição |
|---|---|---|
| **Sem risco** | nenhum indicador ativo na janela | faixa discreta: "Sem risco identificado nas próximas 3 horas" |
| **Atenção** | algum indicador ativo, mas nunca dois no mesmo horário | faixa amarela com os indicadores |
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
| 2 | 36 °C, de dia, nebulosidade 20 % | Atenção (IND-SOL) |
| 3 | 36 °C, de dia, nebulosidade 90 % | Sem risco |
| 4 | 39 °C, de dia, nebulosidade 10 % | Risco à sua vida (IND-SOL + IND-SOMBRA) |
| 5 | 39 °C, à noite | Atenção (IND-SOMBRA) |
| 6 | Tw 31 °C e trovoada no mesmo horário | Risco à sua vida |
| 7 | Tw 31 °C em h0 e trovoada só em h2 | Atenção |
| 8 | Rajada 65 km/h e aviso INMET "Tempestade" vigente | Risco à sua vida |
| 9 | Vento 60 km/h exatos e trovoada | Atenção (60 não é "acima de 60") |
| 10 | Potencial de tornado alto em h3, nada mais | Extremo |
| 11 | Potencial de tornado moderado + Tw 32 °C | Atenção, com ícone informativo de tornado |
| 12 | Sem dados do Open-Meteo, Tw 33 °C e trovoada | Risco à sua vida; tornado "indisponível" |

---

## 5. Requisitos — App Android

### 5.1 Plataforma
- **REQ-APP-01 🆕** Kotlin, Jetpack Compose, `minSdk 31` (Android 12), `targetSdk` exigido pelo Google Play na
  data de publicação. Pacote: `dev.derossi.wyw` (ver Q-4). Nome do app: **WYW**.
- **REQ-APP-02 🆕** O app funciona sem o servidor do site: consulta MET Norway, Open-Meteo e INMET direto do
  aparelho, com a tabela IBGE embutida. Respostas em cache por 15 min (previsão) e 10 min (avisos).
- **REQ-APP-03 🆕** Interface em português, inglês e espanhol, seguindo o idioma do sistema.

### 5.2 Telas
- **REQ-APP-10 🆕** **Início:** risco do local atual no topo (faixa de 4.5), seguido de "Agora", bulbo úmido,
  umidade, pressão, vento/rajadas e avisos do INMET de hoje, como no site.
- **REQ-APP-11 🆕** **Busca:** cidade ou endereço completo. Endereços pelo `android.location.Geocoder`; se ele não
  encontrar, busca de cidades do Open-Meteo. O resultado mostra o nível de risco do endereço (REQ-APP-30 não se
  aplica: não há notificação para endereços buscados).
- **REQ-APP-12 🆕** **Previsão de 7 dias** com os mesmos campos e ícones de aviso do site.
- **REQ-APP-13 🆕** **Sobre:** fontes de dados, aviso de 4.5/REQ-WEB-43, política de privacidade e créditos.

### 5.3 Localização e verificação em segundo plano
- **REQ-APP-20 🆕** Pede localização **aproximada** primeiro e, depois, localização **em segundo plano** em etapa
  separada, com uma tela explicando o motivo antes do pedido do sistema (exigência do Android 12 e do Google Play).
- **REQ-APP-21 🆕** Sem permissão em segundo plano, o app funciona normalmente, mas só avalia o risco com ele aberto
  e informa isso na tela de início.
- **REQ-APP-22 🆕** Com permissão, um `WorkManager` periódico (a cada 30 min, rede disponível) obtém a localização
  aproximada, avalia o risco (seção 4) e notifica conforme 5.4.
- **REQ-APP-23 🆕** A localização não sai do aparelho, exceto arredondada (C-2) nas consultas às APIs de tempo.

### 5.4 Notificação de risco
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
- **AC-APP-30** Num aparelho com Android 12, simulando Tw 32 °C e trovoada no local atual: a notificação aparece
  com área vermelha, ícone amarelo, "Risco à sua vida!", as duas linhas de indicadores e o aviso sobre as
  autoridades; nenhuma segunda notificação é criada na verificação seguinte.

**Limitação conhecida.** O Android controla o cabeçalho das notificações (ícone pequeno, nome do app, hora); só a
área de conteúdo pode ser vermelha. Fundo totalmente colorido (`setColorized`) só é permitido para serviços em
primeiro plano e mídia, o que não se aplica aqui.

### 5.5 Publicação
- **REQ-APP-40 🆕** Publicação no Google Play: conta de desenvolvedor, política de privacidade publicada no site
  (`/privacy`), formulário de segurança de dados e declaração de localização em segundo plano com vídeo
  demonstrando o recurso.

---

## 6. Requisitos não funcionais
- **NFR-01** Uma busca deve responder em até 3 s no servidor aquecido (sem contar a partida a frio do Render Free).
- **NFR-02** Falha de uma fonte não derruba a página nem o app: os campos dela somem ou aparecem como
  indisponíveis.
- **NFR-03** Acessibilidade: faixa de risco com contraste AA, ícones com texto alternativo e tipbox acessível por
  teclado.
- **NFR-04** Testes: `pytest` no site; testes unitários (JUnit) do modelo de risco no app; os três motores de risco
  passam em `spec/risk-cases.json`.
- **NFR-05** Logs: erros de serviços externos registrados com código HTTP e corpo resumido.

---

## 7. Arquitetura

```
bulb-app/
├── app/                  site Flask (servidor)
│   ├── meteo/risk.py     motor de risco (Python)            🆕
│   └── static/risk.js    complemento no navegador: Open-Meteo, rajadas, tornado,
│                         busca de endereço (Nominatim)      🆕
├── android/              app Kotlin                         🆕
│   └── …/risk/           motor de risco (Kotlin)
├── spec/risk-cases.json  casos de teste compartilhados       🆕
└── SPEC.md
```

**Fluxo no site.** O servidor calcula os indicadores que dependem de MET e INMET e entrega, junto com a página, a
série horária da janela. O navegador busca no Open-Meteo os dados de rajada e tornado, completa os indicadores e
calcula o nível final, exibindo a faixa de risco.

**Fluxo no app.** Tudo no aparelho: localização → MET + Open-Meteo + INMET → motor de risco → tela e notificação.

---

## 8. Plano de entrega

| Marco | Conteúdo | Requisitos |
|---|---|---|
| **M1** | Nome WYW, rodapé derossi research, motor de risco em Python + `risk-cases.json`, faixa de risco (sem tornado/rajadas) | WEB-01, 02, 40, 41, 43; seção 4 |
| **M2** | Complemento no navegador: rajadas, tornado, busca de endereço | WEB-11, 22, 42, 44 |
| **M3** | App Android: telas, busca, risco com o app aberto | APP-01…13, 21 |
| **M4** | Segundo plano e notificação de risco | APP-20, 22, 23, 30…33 |
| **M5** | Publicação no Google Play e política de privacidade | APP-40 |

---

## 9. Questões em aberto
- **Q-1** Grafia do nome: "Weather is your **Wheather**" está correto ou seria "Weather is your **Weather**"/"**Whether**"?
- **Q-2** Potencial de tornado **moderado** só como ícone informativo (proposto) ou também como indicador extremo?
  No verão do Sul do Brasil o moderado é frequente e geraria muitos alarmes.
- **Q-3** De dia, com sol e acima de 38 °C, IND-SOL e IND-SOMBRA contam como dois indicadores (proposto) ou como um?
- **Q-4** Nome do pacote Android (`dev.derossi.wyw`) e conta de desenvolvedor do Google Play a usar.
- **Q-5** Rótulo "Ventos Costeiros" do INMET: incluir em IND-VENTO só nos municípios costeiros (como o próprio aviso
  delimita) — proposto — ou tratar como os demais avisos de vento.

## 10. Referências
- Stull, R. (2011). Wet-Bulb Temperature from Relative Humidity and Air Temperature. *J. Appl. Meteor. Climatol.*
- Sherwood, S. C.; Huber, M. (2010). An adaptability limit to climate change due to heat stress. *PNAS* 107(21).
- Taszarek, M. et al. (2020). Severe convective storms across Europe and the United States. *J. Climate* 33.
- MET Norway Locationforecast 2.0 · Open-Meteo · INMET Alert-AS · Nominatim Usage Policy · Android notifications
  (custom layouts) e background location (Google Play policy).
