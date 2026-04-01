# Life OS

A self-hosted personal operating system for daily planning, journaling, long-term goal tracking, and milestone logging. Runs as a Progressive Web App (PWA) backed by a FastAPI service that stores all data as plain Markdown files on your own machine.

## Features

- **Daily planner** — morning intention-setting and evening reflection with mood tracking, sleep logging, habit check-ins, and gratitude capture
- **Task management** — per-day task lists with priority ordering and completion tracking
- **Hierarchical goal planning** — linked daily → weekly → monthly → quarterly → yearly horizons, each with its own Markdown vault entry
- **Milestone tagging** — tag any line in any vault entry with `@milestone` (or `@milestone:category`) to surface achievements in a dedicated timeline view
- **Journal** — structured morning and evening journal entries separate from task/planning content
- **AI suggestions** — daily prompts and reflection nudges via Mistral API or local Claude Code CLI
- **Google Calendar integration** — read free/busy data and write new events without leaving the app
- **Push notifications** — twice-daily VAPID web push reminders (7 AM morning, 8 PM evening)
- **PWA / iOS compatible** — installable to home screen, offline shell via service worker, safe-area insets for notched phones
- **Plain-text vault** — all data stored as Markdown with YAML frontmatter; no database, no lock-in

## Architecture

```
┌─────────────────────────────────────────┐
│  Browser / iOS Home Screen PWA          │
│  Vanilla JS · No build step required    │
└──────────────┬──────────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────────┐
│  nginx (TLS termination + static files) │
└──────────────┬──────────────────────────┘
               │ HTTP (internal)
┌──────────────▼──────────────────────────┐
│  FastAPI backend (Python 3.12)          │
│  · Bearer-token auth on all API routes  │
│  · Markdown vault read/write            │
│  · Google Calendar OAuth2               │
│  · VAPID push subscriptions             │
│  · AI provider abstraction              │
└──────────────┬──────────────────────────┘
               │ host bind mount
┌──────────────▼──────────────────────────┐
│  ./vault/   (Markdown files)            │
│  ./config/  (push subscriptions, token) │
└─────────────────────────────────────────┘
```

A separate `cron` container in Docker Compose runs the push-notification scripts on schedule.

> **Cloudflare Tunnel variant:** The `cloudflare-tunnel` branch replaces nginx with a Cloudflare Tunnel running on your host machine. The backend binds to `127.0.0.1` only and serves the frontend via FastAPI's `StaticFiles` mount. Use this branch if you already run `cloudflared` and want to skip TLS certificate management.

## Prerequisites

- Docker and Docker Compose v2
- A domain name with DNS pointed at your server (for TLS)
- TLS certificates for nginx (e.g. from Let's Encrypt)
- Optional: Mistral API key, Google Cloud OAuth credentials

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url> my-life-os
cd my-life-os
cp .env.example .env
$EDITOR .env
```

### 2. Generate an API key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Paste the result into `API_KEY` in your `.env`.

### 3. Generate VAPID keys (push notifications)

```bash
pip install cryptography
python - <<'EOF'
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

key = ec.generate_private_key(ec.SECP256R1())
priv_int = key.private_numbers().private_value
priv_b64 = base64.urlsafe_b64encode(priv_int.to_bytes(32, "big")).rstrip(b"=").decode()
pub_raw  = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
pub_b64  = base64.urlsafe_b64encode(pub_raw).rstrip(b"=").decode()
print("VAPID_PRIVATE_KEY=" + priv_b64)
print("VAPID_PUBLIC_KEY="  + pub_b64)
EOF
```

Copy both values into `.env`.

### 4. Place TLS certificates

```
nginx/certs/fullchain.pem
nginx/certs/privkey.pem
```

These paths are gitignored. Obtain certs from Let's Encrypt (`certbot`) or your preferred CA.

### 5. Update nginx config

Edit `nginx/nginx.conf` and replace `lifeos.yourdomain.com` with your domain.

### 6. Start

```bash
docker compose up -d
```

Open `https://lifeos.yourdomain.com` in your browser, enter your API key when prompted, and install the PWA from the browser menu.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `API_KEY` | Yes | Long random string for Bearer-token auth |
| `VAULT_DIR` | No | Path to vault inside container (default `/app/vault`) |
| `CONFIG_DIR` | No | Path to config inside container (default `/app/config`) |
| `TZ` | No | Timezone for cron push schedule (default `America/New_York`) |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins, e.g. `https://lifeos.yourdomain.com` |
| `VAPID_PRIVATE_KEY` | No | VAPID private key (push notifications) |
| `VAPID_PUBLIC_KEY` | No | VAPID public key (push notifications) |
| `VAPID_EMAIL` | No | Contact email for push, e.g. `mailto:you@example.com` |
| `AI_PROVIDER` | No | `mistral`, `claude-code`, or `disabled` (default `disabled`) |
| `MISTRAL_API_KEY` | No | Required when `AI_PROVIDER=mistral` |
| `MISTRAL_MODEL` | No | Mistral model name (default `mistral-small-latest`) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth2 client secret |
| `GOOGLE_REDIRECT_URI` | No | Must match URI registered in Google Cloud Console |
| `GOOGLE_CALENDAR_IDS` | No | Comma-separated calendar IDs for free/busy (default `primary`) |
| `GOOGLE_CALENDAR_WRITE_ID` | No | Calendar ID to create new events in (default `primary`) |

## Google Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Google Calendar API**.
3. Create **OAuth 2.0 credentials** (Web application type).
4. Add your redirect URI: `https://lifeos.yourdomain.com/api/calendar/callback`
5. Copy the client ID and secret into `.env`.
6. After deploying, open the app, navigate to the Calendar tab, and click **Connect Google Calendar**. Complete the OAuth flow once — the token is stored in `./config/` and refreshed automatically.

## AI Suggestions

Set `AI_PROVIDER` in `.env`:

- **`disabled`** — no AI features (default)
- **`mistral`** — calls the Mistral API using `MISTRAL_API_KEY`. Uses `mistral-small-latest` by default.
- **`claude-code`** — spawns the local `claude` CLI binary as a subprocess. The binary must be installed and authenticated on the host, and the Docker container must have access to it (mount the binary or use `network_mode: host`). No API key configuration needed — it uses the existing Claude Code session.

## Data Storage

All data lives in `./vault/` on your host machine as plain Markdown files with YAML frontmatter. The directory structure is:

```
vault/
  daily/        YYYY-MM-DD.md       — daily planner + tasks + habits
  weekly/       YYYY-Www.md         — weekly themes and review
  monthly/      YYYY-MM.md          — monthly goals and reflection
  quarterly/    YYYY-Qn.md          — quarterly OKRs
  yearly/       YYYY.md             — annual vision and priorities
  journal/
    morning/    YYYY-MM-DD.md       — morning journal entries
    evening/    YYYY-MM-DD.md       — evening journal entries
```

Frontmatter `parent` fields link each entry to its parent horizon (e.g. a daily entry links to its week). Back up `./vault/` like any other important directory — it's just files.

## Milestone Tagging

Tag any line in any vault entry with `@milestone` to mark it as a milestone:

```markdown
- Launched v1.0 of the product @milestone
- Completed marathon training @milestone:health
- Got promoted @milestone:career
```

Supported categories: `career`, `business`, `health`, `learning`, `finance`, `personal`.

Milestones are surfaced in the **Milestones** page as a timeline grouped by year, filterable by category, with one-click copy for resume/CV use.

## Push Notifications

The cron container runs two scripts on schedule:

| Time | Script | Purpose |
|---|---|---|
| 7:00 AM | `morning_push.py` | Morning planning reminder |
| 8:00 PM | `evening_push.py` | Evening reflection reminder |

Times are in the timezone specified by `TZ`. The push schedule is baked into the Docker image at build time via `/etc/crontabs/root`.

To enable push in the browser: open the app, go to **Settings**, and click **Enable Push Notifications**. The browser will request permission and register a push subscription with the backend.

## Security

- All API endpoints require a `Bearer <API_KEY>` header. The key is compared with `secrets.compare_digest` to prevent timing attacks.
- Path traversal is prevented with two layers: `date.fromisoformat()` validates the key format, and `.resolve()` + prefix check catches symlink escapes.
- Concurrent vault writes are serialised with `filelock`.
- The API key is stored in `localStorage` in the browser — treat it like a password. Use a long random value (32+ bytes).
- CORS is restricted to `CORS_ORIGINS`. Set this to your exact domain in production.
- The health endpoint (`GET /health`) is unauthenticated so Docker can health-check the container. It returns no sensitive data.

## Branches

| Branch | Reverse Proxy | TLS |
|---|---|---|
| `main` | nginx (included in Compose) | Certificates in `nginx/certs/` |
| `cloudflare-tunnel` | Cloudflare Tunnel (runs on host) | Managed by Cloudflare |

If you already run `cloudflared` on your home server, use the `cloudflare-tunnel` branch — it requires no certificate management and no nginx container.

## Development

Run the backend locally without Docker:

```bash
cd backend
pip install -r requirements.txt
API_KEY=dev VAULT_DIR=../vault CONFIG_DIR=../config uvicorn app.main:app --reload
```

The frontend is plain HTML/CSS/JS — open `frontend/index.html` directly or serve it with any static file server. Point the `api.js` base URL at your local backend.

## Updating

```bash
git pull
docker compose build
docker compose up -d
```

The vault and config directories are host-mounted, so your data is never touched by an image rebuild.
