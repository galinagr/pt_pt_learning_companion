"""Model providers. The live provider is the Meta Model API (chat-completions protocol)."""

import json
import os
from typing import Protocol

import httpx

from pt_pt_learning_companion.ai_router import model_base_url, tls_verify
from pt_pt_learning_companion.schemas import Exercise, StudyMaterial, VocabularyItem

META_MODEL = "muse-spark-1.3"

STUDY_INSTRUCTIONS = """You help an English speaker study European Portuguese (pt-PT).
The learner selected one passage from a longer study text.
Use the full document only as context. Explain the selected passage.

Return JSON with this shape:
{
  "translation": "natural English translation of the passage",
  "vocabulary": [
    {"term": "pt-PT word or short phrase from the passage", "explanation": "plain English", "example": "a new pt-PT sentence"}
  ],
  "exercises": [
    {"prompt": "a short practice question in English about the passage", "answer": "the expected answer"}
  ]
}

Rules:
- vocabulary has 4 to 6 items taken from the passage
- exercises has exactly 3 items: one meaning question, one fill-the-blank, one short rewrite into pt-PT
- prefer European Portuguese spelling and vocabulary, not Brazilian
- explanations and exercise prompts are in English
- do not add keys beyond translation, vocabulary, and exercises
"""


class StudyModel(Protocol):
    def study(self, document: str, passage: str) -> StudyMaterial:
        """Return learning material for the selected passage."""


class StubModel:
    """Offline stand-in so the app runs before an API key is set."""

    def study(self, document: str, passage: str) -> StudyMaterial:
        del document
        clipped = passage.strip()
        return StudyMaterial(
            translation=f"[stub] English gloss for: {clipped}",
            vocabulary=[
                VocabularyItem(
                    term=clipped.split()[0],
                    explanation="Stub explanation. Set MODEL_API_KEY for a real gloss.",
                    example="Isto é uma frase de exemplo.",
                )
            ],
            exercises=[
                Exercise(
                    prompt=f"Translate this passage into English: {clipped}",
                    answer="See the translation above. The stub provider does not call a model.",
                )
            ],
        )


class ChatCompletionsModel:
    """Chat-completions client for the Meta Model API."""

    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def study(self, document: str, passage: str) -> StudyMaterial:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": STUDY_INSTRUCTIONS},
                {
                    "role": "user",
                    "content": (
                        "Document:\n"
                        f"{document}\n\n"
                        "Selected passage:\n"
                        f"{passage}"
                    ),
                },
            ],
        }
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
        content = response.json()["choices"][0]["message"]["content"]
        return StudyMaterial.model_validate(_load_json_object(content))


def build_model() -> StudyModel:
    """Use the Meta Model API when MODEL_API_KEY is set; otherwise the offline stub."""
    api_key = os.environ.get("MODEL_API_KEY", "").strip()
    if not api_key:
        return StubModel()
    return ChatCompletionsModel(
        base_url=model_base_url(),
        api_key=api_key,
        model=os.environ.get("MODEL_NAME", META_MODEL),
    )


def _load_json_object(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("model response was not a JSON object")
    return parsed
