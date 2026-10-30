---
name: module-boundaries
description: >-
  Where routes, model clients, prompts, and speech live in the PT-PT Learning
  Companion package. Use when adding a route, client, router, prompt, or speech
  code, or when reviewing src/pt_pt_learning_companion.
---

# Module boundaries

The page calls `/api/generate` and `/api/speak`. Keep the package matched to that.

## Modules

| Module | Owns |
| --- | --- |
| `app.py` | Routes and `create_app()`. Inject model, speaker, text service, and transcriber for tests. |
| `schemas.py` | Pydantic bodies. |
| `ai_router.py` | `plan_model_route()`, `model_base_url()`, `tls_verify()`. Planning only. |
| `ai_models.py` | The chat client and `RoutedTextService`. |
| `providers.py` | Study-only client. Same HTTP job as `MetaTextClient`. Do not add a third copy. |
| `speech.py` | edge-tts synthesis and the transcriber. |

## Rules for new code

- One chat-completions implementation. Extend `MetaTextClient` (or fold `ChatCompletionsModel` into it). Do not paste another `httpx.post` to `/chat/completions`.
- Put prompt strings next to the call that uses them, not mixed into unrelated routes.
- Do not add Glimmer, Muse Image, or SAM call sites until a route needs them. `plan_model_route()` may name them; executing them is a separate change.
- Wonder runs only when `quality=high` and confidence is below the threshold. Do not force Wonder on every Explore or Talk request. The live client currently reports confidence `1.0`, so say that in docs instead of claiming escalation works.
- Cap completion size with `max_tokens` on text generation. Translate stays short. Choice labels do not need a long completion.
- `/api/generate` uses blocking `httpx.post`. New model I/O should be async, or stay as short as that call. Do not add more sync network work on the request path.
- `create_app()` must still run with no `MODEL_API_KEY`. Tests use the stub.

## Docs

When a module boundary changes, update the Python layout table in `README.md`. Leave `docs/ai-design.md` as the target design. Do not describe uncalled models as running.
