"""Cost-aware model routing for Meta-first AI architecture."""

from dataclasses import dataclass
import os
from pathlib import Path

from pt_pt_learning_companion.schemas import ModelPlanRequest, ModelPlanResponse

# Single source of truth for the Meta Model API base URL. Override with
# the MODEL_BASE_URL environment variable; the literal lives only here.
DEFAULT_MODEL_BASE_URL = "https://api.meta.ai/v1"


def model_base_url() -> str:
    """Return the Model API base URL from the env, falling back to the default."""
    return os.environ.get("MODEL_BASE_URL", "").strip() or DEFAULT_MODEL_BASE_URL


def tls_verify() -> str | bool:
    """CA bundle for Model API calls. Verification stays on.

    A corporate TLS proxy re-signs api.meta.ai. Point MODEL_CA_BUNDLE at that
    CA, or drop it in .certs/trust-bundle.pem. Otherwise use the default store.
    """
    override = os.environ.get("MODEL_CA_BUNDLE", "").strip()
    if override:
        return override
    bundle = Path(__file__).resolve().parents[2] / ".certs" / "trust-bundle.pem"
    if bundle.is_file():
        return str(bundle)
    return True


@dataclass(frozen=True)
class RouterConfig:
    spark: str
    wonder: str
    image: str
    transcribe: str
    sam: str
    glimmer: str
    spark_open: str
    budget_daily_usd: float
    budget_escalation_usd: float
    escalation_rate_max: float


def build_router_config() -> RouterConfig:
    return RouterConfig(
        spark=os.environ.get("MODEL_NAME", "muse-spark-1.3"),
        wonder=os.environ.get("META_MODEL_WONDER", "muse-wonder"),
        image=os.environ.get("META_MODEL_IMAGE", "muse-image"),
        transcribe=os.environ.get("META_MODEL_TRANSCRIBE", "muse-voice-transcribe"),
        sam=os.environ.get("META_MODEL_SAM", "sam-3-1"),
        glimmer=os.environ.get("META_MODEL_GLIMMER", "muse-glimmer"),
        spark_open=os.environ.get("META_MODEL_SPARK_OPEN", "muse-spark-open"),
        budget_daily_usd=_float_env("MODEL_BUDGET_DAILY_USD", 10.0),
        budget_escalation_usd=_float_env("MODEL_BUDGET_ESCALATION_USD", 2.0),
        escalation_rate_max=_float_env("MODEL_ESCALATION_RATE_MAX", 0.10),
    )


def plan_model_route(request: ModelPlanRequest, config: RouterConfig) -> ModelPlanResponse:
    if request.task == "transcribe":
        return ModelPlanResponse(
            task=request.task,
            classifier_model=config.glimmer,
            primary_model=config.transcribe,
            fallback_model="browser-speech-recognition",
            escalation_model=None,
            use_escalation=False,
            cache_recommended=False,
            estimated_cost_units=_estimated_units(config.transcribe, request),
            reason="Speech flow uses Muse Voice Transcribe, with browser speech fallback.",
        )
    if request.task == "image":
        return ModelPlanResponse(
            task=request.task,
            classifier_model=config.glimmer,
            primary_model=config.image,
            fallback_model="static-assets",
            escalation_model=None,
            use_escalation=False,
            cache_recommended=True,
            estimated_cost_units=_estimated_units(config.image, request),
            reason="Visual generation uses Muse Image, with static assets fallback.",
        )
    if request.task == "segment":
        return ModelPlanResponse(
            task=request.task,
            classifier_model=config.glimmer,
            primary_model=config.sam,
            fallback_model="manual-crop",
            escalation_model=None,
            use_escalation=False,
            cache_recommended=True,
            estimated_cost_units=_estimated_units(config.sam, request),
            reason="Scene segmentation and crop flow uses SAM 3.1.",
        )

    # Text tasks: translate, explore, situation.
    primary_model = config.spark
    fallback_model = config.spark_open
    escalation_model = config.wonder
    use_escalation = False
    cache_recommended = request.task in {"translate", "explore", "situation"}

    if request.budget_mode == "strict" and not request.require_managed:
        primary_model = config.spark_open
        fallback_model = config.spark
        escalation_model = None
        reason = "Strict budget mode prefers open-weights model first."
    elif request.budget_mode == "tight":
        use_escalation = False
        reason = "Tight budget mode disables Wonder escalation for cost control."
    else:
        escalation_allowed = request.quality == "high" and config.escalation_rate_max > 0
        if escalation_allowed:
            use_escalation = True
            reason = "High-quality request enables Wonder escalation when needed."
        else:
            reason = "Standard quality uses Spark with Spark Open fallback."

    if request.require_managed:
        primary_model = config.spark
        fallback_model = config.wonder
        if request.quality == "high":
            use_escalation = True
        reason = "Managed-only mode routes to Meta managed models."

    return ModelPlanResponse(
        task=request.task,
        classifier_model=config.glimmer,
        primary_model=primary_model,
        fallback_model=fallback_model,
        escalation_model=escalation_model,
        use_escalation=use_escalation,
        cache_recommended=cache_recommended,
        estimated_cost_units=_estimated_units(primary_model, request),
        reason=reason,
    )


def _estimated_units(model: str, request: ModelPlanRequest) -> float:
    token_thousands = (request.estimated_input_tokens + request.estimated_output_tokens) / 1000.0
    if token_thousands <= 0:
        token_thousands = 1.0
    unit = _model_unit_cost(model)
    return round(token_thousands * unit, 3)


def _model_unit_cost(model: str) -> float:
    low = model.lower()
    if "wonder" in low:
        return 3.5
    if "spark-open" in low or "glimmer" in low:
        return 0.4
    if "voice" in low or "transcribe" in low:
        return 1.2
    if "image" in low or "sam" in low:
        return 2.2
    return 1.0


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
