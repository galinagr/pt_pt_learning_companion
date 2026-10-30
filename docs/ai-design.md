# AI System Design (Meta-first, Cost-Optimized)

This document defines **when and why** PT-PT Learning Companion uses each model or agent, and which parameters control behavior in production.

> **Target design, not the running code.** What the package does today is in the [README](../README.md#python-layout). This file is the routing we want later: Glimmer classifying, Wonder only when needed, budgets, and telemetry. The live client does not call Glimmer, and it reports full confidence, so Wonder does not escalate.

## 1) Product goals

- Fast interactive UX for `Translate`, `Explore`, and `A situation`
- High language quality for European Portuguese (`pt-PT`)
- Predictable cost in production
- Safe fallbacks when a provider/model is unavailable

## 2) Model and agent roles

## Managed models (Meta Model API)

- **Muse Spark series** (default: `muse-spark-1.3`)
  - **When:** standard text generation for user-facing flows
  - **Why:** best quality/cost baseline for most requests
- **Muse Wonder**
  - **When:** high-quality rewrites, nuance-heavy prompts, or premium mode
  - **Why:** higher quality, but more expensive; should be gated
- **Muse Voice Transcribe**
  - **When:** robust dictation/transcription pipeline
  - **Why:** more consistent than browser-only speech in noisy/real-world usage
- **Muse Image**
  - **When:** generated visual assets (hero, onboarding cards, social previews)
  - **Why:** reusable branded assets; optional for MVP runtime
- **SAM 3.1**
  - **When:** segmentation/cropping of scene assets and demo media prep
  - **Why:** cleaner framing and visual composition

## Open-weights models

- **Muse Glimmer**
  - **When:** low-cost routing/classification step
  - **Why:** cheap decision layer before expensive generation
- **Muse Spark Open**
  - **When:** strict budget mode, fallback, batch/offline workflows
  - **Why:** cost control and resilience if managed quota is constrained

## Coding agent

- **Muse Code**
  - **When:** implementation, refactoring, test scaffolding, repeated engineering tasks
  - **Why:** accelerates delivery and keeps architecture changes consistent

## 3) Routing policy (core)

All text requests follow this policy:

1. **Classifier stage** (Glimmer)
2. **Primary generation** (Spark)
3. **Escalation** (Wonder, only if needed)
4. **Fallback** (Spark Open) if cost/availability constraints apply

### Escalation gate

Escalate to Wonder only when:

- `quality = high`, and
- budget rules allow escalation, and
- classifier/request complexity indicates meaningful quality gain

### Strict budget mode

In strict mode:

- Primary = Spark Open
- Fallback = Spark
- Escalation = off

This is the main production lever for cost caps.

## 4) Model usage by feature

| Feature | Primary | Escalation | Fallback | Why this combination |
| --- | --- | --- | --- | --- |
| Translate | Spark | Wonder | Spark Open | Fast baseline, selective quality upgrade |
| Explore | Spark | Wonder | Spark Open | Guidance text benefits from occasional higher nuance |
| A situation | Spark | Wonder | Spark Open | Dialogue realism improves with targeted escalation |
| Dictation | Voice Transcribe | - | Browser speech | Reliability first; browser fallback for availability |
| Media visuals | Muse Image | - | Static assets | Optional generation path |
| Media crop/segmentation | SAM 3.1 | - | Manual crop | Quality visual framing |

## 5) Runtime parameters and why they exist

## Provider and model selection

- `MODEL_API_KEY`
  - chooses the provider: unset → offline stub, set → Meta Model API
- `MODEL_NAME`
  - default managed text model (Spark family by default)
- `META_MODEL_WONDER`, `META_MODEL_GLIMMER`, `META_MODEL_SPARK_OPEN`
  - explicit routing roles; avoids hardcoding

## Budget controls

- `MODEL_BUDGET_DAILY_USD`
  - hard daily spend guardrail
- `MODEL_BUDGET_ESCALATION_USD`
  - caps premium quality path separately
- `MODEL_ESCALATION_RATE_MAX`
  - limits Wonder usage ratio; protects cost drift

## Request-level controls

- `quality` (`standard|high`)
  - asks for baseline vs premium text quality
- `budget_mode` (`normal|tight|strict`)
  - immediate cost profile override for the request
- `require_managed` (`true|false`)
  - enforces managed-model path (compliance/product reasons)
- `estimated_input_tokens`, `estimated_output_tokens`
  - early cost estimate for routing and telemetry

## 6) Agent usage strategy

Use specialized agents by problem type:

- **Muse Code** for implementation and refactors
- **Quality/review agent** for regression checks before release
- **Security review agent** for security-sensitive changes
- **CI investigator agent** for failing checks

Why:

- Faster cycle time than one general agent doing everything
- Better quality via role specialization
- Lower total engineering cost from reduced rework

## 7) API contracts introduced for architecture

`POST /api/model-plan` returns planned routing:

- classifier model
- primary model
- escalation model + flag
- fallback model
- estimated cost units
- plain-language reason

This is a transparent “control-plane” endpoint for debugging and product tuning.

## 8) Production defaults (recommended)

- Provider: `meta`
- Default text model: `muse-spark-1.3`
- Escalation rate max: `0.10`
- Daily budget: `10 USD`
- Escalation budget: `2 USD`
- Default request quality: `standard`
- Default budget mode: `normal`

## 9) Why this design is optimized

- Keeps most traffic on a strong mid-cost model (Spark)
- Uses Wonder only when it adds clear value
- Uses Glimmer as cheap router to avoid unnecessary premium calls
- Keeps Spark Open as cost/fallback safety net
- Separates speech/media pipelines so text costs do not absorb everything
- Exposes knobs in config instead of code for rapid tuning without redeploy

## 10) Response cache

Running, not a later step. `POST /api/generate` checks an in-memory hash cache before the model call and returns `cached: true` on a repeat. The page keeps a separate `liveCache` for the current load. Speech is not cached. The rules are in [Where the cache runs](meta-model-architecture.md#where-the-cache-runs).

## 11) Next implementation steps

1. Add persistent telemetry (latency, cost units, escalation ratio)
2. Add quality heuristics to trigger Wonder only on measurable need
3. Add background jobs for batch generation on Spark Open
