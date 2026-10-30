"""Option B hybrid execution: run the routed model plan against text clients.

The router (`ai_router.plan_model_route`) chooses a path. This module executes it:

    Glimmer (classify/route)  ->  Spark (default)
                                   |-- low confidence + quality=high --> Wonder (escalate)
                                   |-- primary error / strict budget  --> Spark Open (fallback)

A stub client keeps the whole flow working with no API key.
"""

from dataclasses import dataclass
import os
from typing import Protocol

import httpx

from pt_pt_learning_companion.ai_router import (
    RouterConfig,
    build_router_config,
    model_base_url,
    plan_model_route,
    tls_verify,
)
from pt_pt_learning_companion.schemas import ModelPlanRequest, ModelPlanResponse


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    confidence: float = 1.0


@dataclass(frozen=True)
class RoutedResult:
    text: str
    model_used: str
    plan: ModelPlanResponse
    escalated: bool
    used_fallback: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class TextClient(Protocol):
    def generate(
        self,
        model: str,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> GenerationResult:
        """Return generated text and token usage for one model call."""


class StubTextClient:
    """Offline client so Option B routing runs without an API key.

    `confidence` is configurable so escalation behavior is testable.
    """

    def __init__(self, confidence: float = 1.0) -> None:
        self._confidence = confidence

    def generate(
        self,
        model: str,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> GenerationResult:
        del system, temperature, json_mode
        prompt_tokens = max(1, len(user) // 4)
        text = f"[stub:{model}] {user.strip()[:160]}"
        completion_tokens = max(1, len(text) // 4)
        return GenerationResult(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            confidence=self._confidence,
        )


class MetaTextClient:
    """Chat-completions client for the Meta Model API."""

    def __init__(self, *, base_url: str, api_key: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def generate(
        self,
        model: str,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> GenerationResult:
        payload: dict = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
            verify=tls_verify(),
        )
        response.raise_for_status()
        body = response.json()
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {}) or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
        return GenerationResult(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )


class RoutedTextService:
    """Execute the Option B plan: classify, run primary, escalate or fall back."""

    def __init__(
        self,
        client: TextClient,
        config: RouterConfig | None = None,
        *,
        confidence_threshold: float = 0.6,
    ) -> None:
        self.client = client
        self.config = config if config is not None else build_router_config()
        self.confidence_threshold = confidence_threshold

    def run(
        self,
        task: str,
        system: str,
        user: str,
        *,
        quality: str = "standard",
        budget_mode: str = "normal",
        require_managed: bool = False,
        estimated_input_tokens: int = 0,
        estimated_output_tokens: int = 0,
        json_mode: bool = False,
    ) -> RoutedResult:
        plan = plan_model_route(
            ModelPlanRequest(
                task=task,
                quality=quality,
                budget_mode=budget_mode,
                require_managed=require_managed,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=estimated_output_tokens,
            ),
            self.config,
        )

        escalated = False
        used_fallback = False
        try:
            result = self.client.generate(plan.primary_model, system, user, json_mode=json_mode)
        except (httpx.HTTPError, ValueError, KeyError):
            # Primary failed: degrade to the fallback (open-weights) path.
            result = self.client.generate(plan.fallback_model, system, user, json_mode=json_mode)
            used_fallback = True
        else:
            # Escalate only when the plan allows it and the primary looked unsure.
            if (
                plan.use_escalation
                and plan.escalation_model
                and result.confidence < self.confidence_threshold
            ):
                try:
                    result = self.client.generate(
                        plan.escalation_model, system, user, json_mode=json_mode
                    )
                    escalated = True
                except (httpx.HTTPError, ValueError, KeyError):
                    # Escalation failed: keep the primary result rather than erroring.
                    escalated = False

        return RoutedResult(
            text=result.text,
            model_used=result.model,
            plan=plan,
            escalated=escalated,
            used_fallback=used_fallback,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
        )


def build_text_client() -> TextClient:
    """Use the Meta Model API when MODEL_API_KEY is set; otherwise the offline stub."""
    api_key = os.environ.get("MODEL_API_KEY", "").strip()
    if not api_key:
        return StubTextClient()
    return MetaTextClient(
        base_url=model_base_url(),
        api_key=api_key,
    )


def build_text_service() -> RoutedTextService:
    return RoutedTextService(build_text_client())
