# WYW — Plano de continuação

Plano a partir de **07/11/2026**, depois dos marcos M1, DS e M2. Os requisitos (`REQ-…`) e critérios de aceite
(`AC-…`) estão no [`SPEC.md`](SPEC.md); o estado e as decisões, no [`NOTES.md`](NOTES.md).

**Como trabalhar (vale para todas as fases):** cada mudança começa pelo `SPEC.md` quando altera comportamento; cada
fase vai num branch próprio e num PR para a `main`; os testes (`pytest`) passam antes de qualquer merge; ao terminar
um requisito, o status dele no spec muda de 🆕 para ✅.

## Visão geral

| Fase | Entrega | Depende de | Situação |
|---|---|---|---|
| **0** | Ambiente no Arch Linux (HefOS) | — | A fazer |
| **1** | **INFRA**: site no AWS Lightsail com `clima.` e `weather.derossi.dev` | Fase 0, conta AWS, DNS na Hostinger | A fazer |
| **2** | **M3**: app Android com o app aberto | Fase 0, celular Android 12+ | A fazer |
| **3** | **M4**: verificação em segundo plano e notificações | Fase 2 | A fazer |
| **4** | **M5**: publicação no Google Play | Fases 1 a 3, D-U-N-S e conta de desenvolvedor | Bloqueada |

As fases 1 e 2 são independentes e podem andar em paralelo. A política de privacidade (`/privacy`, exigida na fase 4)
entra na fase 1, já no novo domínio.

---

## Fase 0 — Ambiente no Arch Linux

1. **Pacotes:** `sudo pacman -S --needed git github-cli python nodejs docker docker-compose` e
   `sudo systemctl enable --now docker`; adicionar o usuário ao grupo `docker`.
2. **Projeto:** `gh auth login` e `git clone https://github.com/derossimolina/bulb-app.git ~/projects/bulb-app`.
3. **Python:** `python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
4. **Conferir:** `.venv/bin/pytest` com **84 testes passando** (o Node precisa estar no `PATH` para
   `tests/test_risk_js.py`).
5. **Rodar o site localmente:** `.venv/bin/python wsgi.py` e abrir http://localhost:5000.
6. **Histórico do Claude Code (opcional):** copiar o `.jsonl` e a pasta de anexos de `claude-sessions` para
   `~/.claude/projects/-home-<usuário>-projects-bulb-app/` e usar `/resume` dentro do projeto.
7. **Acessos:** login no Render (painel ou conector) e, para a fase 1, na AWS (`aws login` ou credenciais de um
   usuário IAM com acesso ao Lightsail).

**Pronto quando:** testes passando e site abrindo em `localhost:5000`.

---

## Fase 1 — INFRA: migração para o AWS Lightsail

Requisitos: REQ-INFRA-01 a 06, REQ-WEB-04 · Aceite: AC-INFRA-01, AC-WEB-04 · Branch sugerido: `feat/infra-lightsail`.

### 1.1 Código no repositório (antes de criar qualquer recurso pago)
1. **Idioma por domínio (REQ-WEB-04):** em `get_locale()`, sem `lang` nem sessão, `clima.derossi.dev` → `pt` e
   `weather.derossi.dev` → `en`; em `base.html`, `<link rel="alternate" hreflang="pt|en|x-default">` e
   `<link rel="canonical">`. Testes com `Host` simulado.
2. **Política de privacidade:** rota `/privacy` (pt, en, es) dizendo o que é coletado (nada armazenado; coordenada
   arredondada; Nominatim e Open-Meteo chamados pelo navegador; localização do app fica no aparelho). Base para o
   REQ-APP-40.
3. **Gunicorn `gthread`** (REQ-INFRA-02): `--worker-class gthread --workers 2 --threads 4` no `Dockerfile`.
4. **Rota de saúde** `/healthz` (resposta simples, sem chamar APIs) para o monitoramento.
5. **`deploy/docker-compose.yml`:** serviço `app` (imagem do GHCR, `SECRET_KEY` de um arquivo `.env` no servidor) e
   serviço `caddy` (portas 80/443, volume para os certificados).
6. **`deploy/Caddyfile`:** `clima.derossi.dev, weather.derossi.dev { reverse_proxy app:5000 }`, com HTTPS automático.
7. **GitHub Actions (REQ-INFRA-04):** a cada merge na `main`, rodar o `pytest`, construir a imagem, enviar ao GitHub
   Container Registry e, por SSH, executar `docker compose pull && docker compose up -d` na instância. Segredos no
   GitHub: chave SSH, IP e usuário.
8. **Redirecionamento do Render (REQ-INFRA-06):** variável `REDIRECT_TO` que, quando definida, faz o app responder
   301 para o mesmo caminho e parâmetros em `https://clima.derossi.dev`.
9. Atualizar `README.md` e `SPEC.md`.

### 1.2 Recursos na AWS (com a conta do usuário; custo a partir daqui)
1. Criar a instância **Linux Micro-1GB (IPv4)**, **Ubuntu 24.04 LTS**, região **São Paulo (`sa-east-1`)**.
2. Criar e anexar um **IP estático**.
3. Firewall do Lightsail: 80 e 443 abertas; 22 só para o IP de quem administra.
4. Na instância: Docker com o plugin Compose, `unattended-upgrades`, usuário de deploy e a chave SSH do GitHub
   Actions; criar `/opt/wyw/.env` com uma `SECRET_KEY` nova.
5. Ativar **snapshots automáticos diários** e os alertas de CPU e status (REQ-INFRA-05).

### 1.3 DNS na Hostinger
1. Criar os registros **A** `clima` e `weather` apontando para o IP estático (TTL curto, por exemplo 300 s, durante a
   migração).
2. Esperar a propagação (`dig clima.derossi.dev`) antes do primeiro deploy, para o Caddy conseguir os certificados.

### 1.4 Primeiro deploy e verificação
1. Disparar o workflow (ou rodar o compose à mão na primeira vez).
2. Verificar AC-INFRA-01: HTTPS válido nos dois domínios; primeira visita em menos de 3 s; logs sem `429` por 7 dias.
3. Verificar AC-WEB-04: `weather` em inglês e `clima` em português, com `hreflang` recíprocos.
4. Testar busca por cidade, por endereço e a faixa de risco em produção, como nos marcos anteriores.

### 1.5 Saída do Render
1. Definir `REDIRECT_TO` no Render e conferir o 301 de `bulb-app.onrender.com`.
2. Depois de 30 dias, suspender o serviço do Render.
3. Opcional: rever a restrição C-1, já que a instância tem IP próprio.

**Pronto quando:** AC-INFRA-01 e AC-WEB-04 atendidos e REQ-INFRA-01 a 06 e REQ-WEB-04 marcados como ✅.

---

## Fase 2 — M3: app Android com o app aberto

Requisitos: REQ-APP-01 a 13, 21, 55, 56, 60, 61 e REQ-DS-01 a 07 · Branch sugerido: `feat/m3-android`.

1. **Build no Docker:** `android/Dockerfile` com JDK 17, Android command-line tools, plataforma e build-tools da
   versão exigida pelo Google Play, e o Gradle Wrapper. Comando único para gerar o APK de debug. (No Arch também é
   possível instalar o SDK direto com o pacote `android-sdk` do AUR.)
2. **Projeto Kotlin** em `android/`: Jetpack Compose, `minSdk 31`, pacote `dev.derossi.wyw`, idiomas pt, en e es.
3. **Design system (seção 5):** tema claro e escuro com os tokens da Contexto, EB Garamond e Inter embutidas,
   cantos retos, Material You desligado; tema segue o sistema, com opção na tela Sobre (REQ-APP-56).
4. **Ícone adaptativo (REQ-APP-60):** nuvem `ivory` com raio `ouro` sobre `ink`, com camada monocromática.
5. **Dados no aparelho (REQ-APP-02):** clientes do MET Norway, Open-Meteo e INMET, tabela IBGE embutida, cache de
   15 min (previsão) e 10 min (avisos).
6. **Motor de risco em Kotlin:** tradução do `app/meteo/risk.py` e do classificador de tornado do `static/risk.js`;
   testes JUnit lendo `spec/risk-cases.json` (os mesmos 18 casos) e conferindo as frases.
7. **Telas:** Início (risco do local atual e cards), Busca (endereço pelo `Geocoder`, cidades pelo Open-Meteo),
   Previsão de 7 dias e Sobre (fontes, aviso sobre as autoridades, privacidade e créditos).
8. **Localização com o app aberto:** permissão aproximada; sem permissão de segundo plano, avisar que só avalia com o
   app aberto (REQ-APP-21).
9. **Teste num celular Android 12+:** instalar o APK (`adb install` ou cópia do arquivo) e conferir as telas, os dois
   temas e a faixa de risco.

**Pronto quando:** APK de debug instalado e funcionando no celular, testes JUnit passando nos casos compartilhados.

---

## Fase 3 — M4: segundo plano e notificações

Requisitos: REQ-APP-20, 22, 23, 30 a 34 e 41 · Aceite: AC-APP-30 · Branch sugerido: `feat/m4-notificacoes`.

1. **Permissão de segundo plano em duas etapas** (REQ-APP-20): tela explicando o motivo antes do pedido do sistema.
2. **`WorkManager` a cada 30 min** com rede disponível (REQ-APP-22): localização aproximada → dados → motor de risco.
3. **Notificação "Risco à sua vida!"** (REQ-APP-30, 31, 55): layout próprio com `DecoratedCustomViewStyle`, área
   vermelha, ícone de alerta amarelo, descrição dos indicadores e aviso sobre as autoridades; canal de importância
   alta, sem som próprio, sem tela cheia.
4. **Notificação de recomendação** para calor (REQ-APP-34), no estilo padrão.
5. **Sem repetição** (REQ-APP-32): só notificar de novo se mudarem os indicadores, se o nível subir ou após 3 h;
   remover quando o risco acabar. Tocar abre a tela de início (REQ-APP-33).
6. **APK de teste assinado** com a chave de upload definitiva, guardada fora do repositório (REQ-APP-41).
7. **Testar AC-APP-30** num Android 12, simulando bulbo úmido de 32 °C e trovoada; conferir o consumo de bateria.

**Pronto quando:** AC-APP-30 atendido e uma semana de uso real sem notificações repetidas ou perdidas.

---

## Fase 4 — M5: publicação no Google Play (bloqueada)

Requisito: REQ-APP-40. **Desbloqueia quando** o D-U-N-S sair e a conta de desenvolvedor (organização) for criada.

1. Criar a conta no Google Play Console e o app `dev.derossi.wyw`.
2. Publicar a política de privacidade (já pronta na fase 1, em `clima.derossi.dev/privacy`).
3. Preencher o formulário de segurança de dados e a declaração de localização em segundo plano, com o vídeo
   demonstrando o recurso.
4. Gerar o AAB de release assinado e passar pelo teste interno e depois pelo teste fechado.
5. Rever os termos de uso do Open-Meteo e do Nominatim antes de publicar (ver riscos no `NOTES.md`).
6. Publicar em produção.

**Pronto quando:** app disponível na loja e REQ-APP-40 marcado como ✅.

---

## Checklist rápido para retomar

- [ ] Fase 0 concluída (testes passando no Arch).
- [ ] Decidir por onde começar: fase 1 (INFRA) ou fase 2 (M3).
- [ ] Para a fase 1: conta AWS pronta e acesso ao painel de DNS da Hostinger.
- [ ] Para a fase 2: celular Android 12+ com depuração USB.
- [ ] Acompanhar o D-U-N-S para desbloquear a fase 4.
