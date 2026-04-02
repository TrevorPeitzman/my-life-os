# Life OS — Deferred TODOs

Items identified but not yet implemented.

---

## iOS Push Notifications Not Working

**Status:** Known issue, investigation pending.

Push notifications may not fire on iOS. Things to check:
- The PWA must be installed to the Home Screen (not just open in Safari) for Web Push to work on iOS.
- iOS 16.4+ is required for Web Push support in installed PWAs.
- Check `config/push_subscriptions.json` — confirm a subscription exists after subscribing on iOS.
- Safari on iOS may silently deny `Notification.requestPermission()`. Open Safari Web Inspector (Settings > Safari > Advanced > Web Inspector) and check the console on device.
- Add a `console.log` inside the `push` event listener in `frontend/sw.js` and verify it fires when a push is triggered manually from the backend.

Files to investigate:
- `frontend/sw.js` — push event handler
- `frontend/js/push.js` — subscription flow
- `backend/app/services/push_service.py` — push delivery and 410 cleanup

---

## Claude Code CLI Through Container

**Status:** Deferred. Use Mistral API instead (`AI_PROVIDER=mistral`).

The `claude-code` AI provider spawns the host's `claude` CLI as a subprocess. Inside Docker this requires mounting the binary, matching user credentials, and dealing with auth token paths — all fragile. No value over the Mistral API path for daily use.

---

## OpenAI-Compatible AI Provider

**Status:** Not yet implemented.

A generic `openai-compat` provider would allow any model with an OpenAI-format chat completions endpoint (Ollama, OpenRouter, self-hosted Llama, etc.).

Planned env vars:
- `AI_PROVIDER=openai-compat`
- `OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1`
- `OPENAI_COMPAT_API_KEY=ollama`
- `OPENAI_COMPAT_MODEL=llama3.2`

Files to modify:
- `backend/app/config.py` — add the three new vars
- `backend/app/services/ai_service.py` — add `openai-compat` branch using `httpx` to POST to `{base_url}/chat/completions`
- `backend/.env.example` — document the vars
- `README.md` — update the AI Suggestions section
