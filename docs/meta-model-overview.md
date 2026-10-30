# Meta Model Overview for PT-PT Learning Companion

This is a practical catalog of the Meta models/agents we plan to use, with **when to use**, **advantages**, **trade-offs**, and **recommended role** in this product.

> Note: pricing/capability signals are based on public Meta pages at the time of writing and can change.

## Official documentation

- **Meta Model API reference:** https://dev.meta.ai/docs/api-reference
- **Model catalog / descriptions:** https://dev.meta.ai/docs/models
- **Token usage & billing:** https://dev.meta.ai/docs/usage
- Per model: [Muse Spark](https://dev.meta.ai/docs/models/muse-spark) · [Muse Wonder](https://dev.meta.ai/docs/models/muse-wonder) · [Muse Image](https://dev.meta.ai/docs/models/muse-image) · [Muse Voice Transcribe](https://dev.meta.ai/docs/models/muse-voice-transcribe) · [SAM 3.1](https://dev.meta.ai/docs/models/sam-3-1) · [Muse Glimmer](https://dev.meta.ai/docs/models/muse-glimmer) · [Muse Spark Open](https://dev.meta.ai/docs/models/muse-spark-open) · [Muse Code](https://dev.meta.ai/docs/muse-code)

See [Tracking token usage](meta-model-architecture.md#tracking-token-usage) for how and where this app records consumption.

## 1) Muse Spark 1.3 (managed)

## Best role

- Default managed text model for `Translate`, `Explore`, `A situation`

## When to use

- Most interactive user requests
- Standard quality mode
- Tool-calling and long-horizon but still cost-sensitive workflows

## Why

- Strong baseline for coding/agentic patterns and multimodal perception
- 1M context window is suitable for larger context assembly workflows

## Advantages

- Good quality/performance balance
- Broad capability; reliable default
- Works cleanly in managed API path

## Trade-offs

- Higher cost than open-weights local routing options
- Premium quality still may require Wonder escalation

## 2) Muse Wonder (managed)

## Best role

- Selective escalation path for high-quality output

## When to use

- `quality=high`
- Nuance-heavy phrasing and difficult multi-step outputs
- Recovery from lower-confidence default generation

## Why

- Frontier-level quality for demanding agentic/coding tasks

## Advantages

- Highest expected answer quality in difficult cases
- Better long-running and multi-agent decomposition behavior

## Trade-offs

- Highest token cost
- Must be gated by strict escalation policy

## 3) Muse Image (managed)

## Best role

- Optional visual generation for product assets

## When to use

- Branded onboarding cards, social preview images, content variants
- Controlled image edit/composition workflows

## Why

- Designed for agentic image generation/editing and production volume pricing

## Advantages

- Low per-image cost signal for scale use cases
- Supports iterative edits and composition

## Trade-offs

- Not required for core translation/situation flows
- Adds media workflow complexity

## 4) Muse Voice Transcribe (managed)

## Best role

- Primary production dictation/transcription backend

## When to use

- User dictation where consistency matters
- Streaming transcription with stronger operational control

## Why

- Competitive streaming transcription accuracy and latency signals
- Better production consistency than browser-only speech

## Advantages

- Predictable quality and behavior
- Speaker-aware capabilities for advanced scenarios

## Trade-offs

- Additional runtime cost
- Needs fallback for resilience

## 5) SAM 3.1 (managed)

## Best role

- Segmentation/cropping/tracking for image/video assets

## When to use

- Demo media prep
- Object-level crop and tracking pipelines

## Why

- Purpose-built segmentation/tracking model with unified API envelope

## Advantages

- Pixel-level masks + tracking in one model
- Good fit for visual automation workflows

## Trade-offs

- Extra component for non-core language UX
- Requires integration in media pipeline

## 6) Muse Glimmer (open model)

## Best role

- Low-cost classifier/router and local always-on agent

## When to use

- Task routing, quality gate pre-checks, language intent checks
- Local/on-device agent scenarios

## Why

- Open model tuned for agentic workflows and failure recovery

## Advantages

- Lower cost routing stage
- Deployment flexibility (local/self-host/provider marketplace)
- Reduces unnecessary premium calls

## Trade-offs

- Adds routing complexity
- Output quality for final user text may be lower than Spark/Wonder

## 7) Muse Spark Open (open-weight)

## Best role

- Fallback and strict-budget primary model

## When to use

- `budget_mode=strict`
- Managed outage/quota constraints
- Batch/background generation

## Why

- Open-weight control + strong agentic/coding capability

## Advantages

- Better vendor portability and infrastructure control
- Strong resilience and cost lever

## Trade-offs

- Requires hosting/ops maturity if self-run
- Quality/latency can vary by deployment stack

## 8) Muse Code (coding agent)

## Best role

- Engineering acceleration, implementation, refactors, test scaffolding

## When to use

- Complex multi-file changes
- Repeatable architecture rollout tasks
- CI fix and review loops

## Why

- Built for coding workflows with multi-agent collaboration and auditability

## Advantages

- Faster iteration for development team
- Better visibility of code actions and decisions

## Trade-offs

- Not a runtime model for end-user requests
- Requires process discipline to keep changes reviewable

## Product-specific recommendations

1. **Default text path:** Spark
2. **Escalation path:** Wonder only when `quality=high` or low-confidence cases
3. **Router stage:** Glimmer first for cost-aware decisioning
4. **Fallback path:** Spark Open for strict budget and outages
5. **Speech path:** Voice Transcribe primary, browser fallback
6. **Media path:** Muse Image + SAM 3.1 only when visual pipeline is needed

## Quick parameter guidance

- Keep `quality=standard` by default
- Use `budget_mode=normal` by default
- Use `budget_mode=tight|strict` for cost protection
- Cap Wonder escalation with `MODEL_ESCALATION_RATE_MAX`
- Track:
  - escalation ratio
  - fallback ratio
  - latency p95
  - estimated cost units
