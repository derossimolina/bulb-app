# Deploy no AWS Lightsail

Passo a passo da tarefa T-04 do [`PLAN.md`](../PLAN.md). Requisitos: `SPEC.md`, seção 8.1 (REQ-INFRA-01 a 07).

O que há nesta pasta:

| Arquivo | Para quê |
|---|---|
| `docker-compose.yml` | Serviços `app` (imagem do GitHub Container Registry) e `caddy` (HTTPS) |
| `Caddyfile` | `clima.derossi.dev` e `weather.derossi.dev` apontando para o app |
| `.env.example` | Modelo do `/opt/wyw/.env`, que só existe na instância |

O workflow [`deploy.yml`](../.github/workflows/deploy.yml) testa todo PR. Na `main`, ele constrói a imagem e, se a
variável `DEPLOY_ENABLED` for `true`, atualiza a instância por SSH.

## 1. Instância (painel do Lightsail)

1. Criar a instância **Linux, Ubuntu 24.04 LTS, plano Micro-1GB (IPv4)**, região **São Paulo**.
2. Criar um **IP estático** e anexar à instância.
3. Em *Networking*, deixar abertas só as portas **80** e **443** (TCP) e **443** (UDP); a **22** restrita ao seu IP.
   O GitHub Actions também entra pela 22: ou libere a 22 para qualquer origem (a entrada é só por chave), ou rode o
   deploy à mão (passo 5).
4. Ativar os **snapshots automáticos** e os alertas de CPU e de status.

## 2. DNS (Hostinger)

Criar os registros **A** `clima` e `weather` com o IP estático (TTL 300). Conferir antes de seguir:

```bash
dig +short clima.derossi.dev weather.derossi.dev
```

O Caddy só consegue os certificados depois que os dois nomes resolvem para a instância.

## 3. Preparar a instância (por SSH, uma vez)

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 unattended-upgrades
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
sudo install -d -o deploy -g deploy /opt/wyw
```

Criar um par de chaves só para o deploy (no seu computador) e autorizar a chave pública na instância:

```bash
ssh-keygen -t ed25519 -f wyw-deploy -N "" -C "github-actions"
```

```bash
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
sudo install -m 600 -o deploy -g deploy /dev/stdin /home/deploy/.ssh/authorized_keys < wyw-deploy.pub
```

Criar o `/opt/wyw/.env` a partir do `.env.example`, com uma `SECRET_KEY` nova, e proteger o arquivo:

```bash
sudo -u deploy sh -c 'umask 077; echo "SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")" > /opt/wyw/.env'
```

## 4. Segredos e variável no GitHub

Em *Settings → Secrets and variables → Actions* do repositório:

| Nome | Tipo | Valor |
|---|---|---|
| `DEPLOY_HOST` | segredo | IP estático da instância |
| `DEPLOY_USER` | segredo | `deploy` |
| `DEPLOY_SSH_KEY` | segredo | conteúdo do arquivo `wyw-deploy` (a chave privada) |
| `DEPLOY_KNOWN_HOSTS` | segredo | saída de `ssh-keyscan -t ed25519 <IP>` |
| `DEPLOY_ENABLED` | variável | `true` |

Depois disso, apague a chave privada do seu computador ou guarde num cofre de senhas.

## 5. Primeiro deploy

Rodar o workflow **Deploy** à mão (*Actions → Deploy → Run workflow*) ou fazer um merge na `main`.

Para rodar sem o GitHub Actions, copie `docker-compose.yml` e `Caddyfile` para `/opt/wyw` e, na instância:

```bash
cd /opt/wyw && docker compose pull && docker compose up -d
```

Sem o workflow, a instância precisa conseguir baixar a imagem: torne o pacote `bulb-app` público no GitHub
(*Packages → bulb-app → Package settings*) ou faça `docker login ghcr.io` com um token de leitura de pacotes.

## 6. Conferir (AC-INFRA-01 e AC-WEB-04)

```bash
curl -sS -o /dev/null -w "%{http_code} em %{time_total}s\n" https://clima.derossi.dev/healthz
```

```bash
curl -sS https://weather.derossi.dev/ | grep -o '<html lang="[a-z]*">'
```

```bash
curl -sS https://clima.derossi.dev/ | grep -o '<html lang="[a-z]*">'
```

Esperado: `200` em menos de 3 s, `lang="en"` no `weather` e `lang="pt"` no `clima`. Ver os logs:

```bash
cd /opt/wyw && docker compose logs --tail 100 app caddy
```

## 7. Sair do Render

Com tudo conferido, definir no serviço do Render a variável `REDIRECT_TO=https://clima.derossi.dev`. O endereço
antigo passa a responder 301 para o mesmo caminho no domínio novo (REQ-INFRA-06). Suspender o serviço 30 dias depois.
