---
name: model-transport-safety
description: >-
  Keeps the PT-PT Learning Companion model client, speech, keys, TLS, logs,
  and file mounts safe. Use when editing Python that calls a model, speech,
  .env, certificates, CORS, downloads, prompts, or when a secret appears in source.
---

# Model transport safety

Apply this whenever you touch model calls, speech, env files, or the HTTP app in this repo.

## Secrets

- Read `MODEL_API_KEY` only from the environment. `app.py` loads a git-ignored `.env` via `load_dotenv()`.
- Never write a key, token, or connection string into source, tests, `README.md`, or `.env.example`. The example file keeps `# MODEL_API_KEY=` commented.
- If a real key shows up in a tracked file, remove it in the same change and tell the user to revoke it. A key that was in git is compromised.
- Do not print `MODEL_API_KEY`, Authorization headers, or audio bytes in logs, test output, or chat.

## TLS

- Model HTTP calls use `tls_verify()` in `ai_router.py`. Leave verification on.
- Allowed values: `True` (default store) or a CA file path (`MODEL_CA_BUNDLE` or `.certs/trust-bundle.pem`).
- Never pass `verify=False` to httpx, even for a corporate proxy or a local test. Add the proxy CA to the trust bundle instead.
- `.certs/` stays git-ignored. Do not commit corporate CA material.

## Learner data

- Do not log prompt text, translations, dictated audio, or study passages.
- Error responses stay generic (`502` / `503` with a short detail). Do not attach provider bodies or exception strings to the HTTP response.
- `/api/transcribe` returns `503` when the stub transcriber fails so the browser can dictate. Keep that fallback. Do not swallow the error into a fake transcript.

## Surface area

- Do not add `allow_origins=["*"]`. Current origins are localhost and `null` for the file preview.
- Do not mount a broader directory than `~/Downloads` for `.mp4`, and do not serve other file types from that mount.
- Do not add a new endpoint that returns the env, the key, or raw provider payloads.

## Before finishing a model or HTTP change

- [ ] No secret in the diff
- [ ] `verify` is `tls_verify()` or `True`, never `False`
- [ ] Logs and HTTP errors omit user text and keys
- [ ] Tests still pass with `MODEL_API_KEY` unset (stub path)
