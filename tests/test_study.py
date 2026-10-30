import json

import httpx
from fastapi.testclient import TestClient

from pt_pt_learning_companion.app import create_app
from pt_pt_learning_companion.providers import (
    ChatCompletionsModel,
    StubModel,
    _load_json_object,
    build_model,
)
from pt_pt_learning_companion.schemas import StudyMaterial


DOCUMENT = "O comboio para o Porto parte da plataforma nove."
PASSAGE = "plataforma nove"


def test_stub_studies_a_passage_from_the_document():
    client = TestClient(create_app(StubModel()))
    response = client.post("/api/study", json={"document": DOCUMENT, "passage": PASSAGE})
    assert response.status_code == 200
    body = StudyMaterial.model_validate(response.json())
    assert PASSAGE in body.translation
    assert body.vocabulary
    assert body.exercises


def test_passage_outside_the_document_is_rejected():
    client = TestClient(create_app(StubModel()))
    response = client.post(
        "/api/study",
        json={"document": DOCUMENT, "passage": "uma frase que não está no texto"},
    )
    assert response.status_code == 400


def test_whitespace_differences_still_match():
    client = TestClient(create_app(StubModel()))
    response = client.post(
        "/api/study",
        json={"document": "O   comboio\npara o Porto", "passage": "comboio para o Porto"},
    )
    assert response.status_code == 200


def test_index_page_is_served():
    client = TestClient(create_app(StubModel()))
    response = client.get("/")
    assert response.status_code == 200
    assert "PT-PT Learning Companion" in response.text


def test_speak_returns_audio_from_the_portuguese_voice():
    async def speaker(text: str, rate: float) -> bytes:
        assert text == "do bilhete"
        assert rate == 0.5
        return b"ID3portuguese"

    client = TestClient(create_app(StubModel(), speaker))
    response = client.post("/api/speak", json={"text": "do bilhete", "rate": 0.5})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.content == b"ID3portuguese"


def test_fenced_model_json_parses():
    raw = """```json
{"translation": "platform nine", "vocabulary": [{"term": "nove", "explanation": "nine", "example": "São nove."}], "exercises": [{"prompt": "Say nine", "answer": "nove"}]}
```"""
    material = StudyMaterial.model_validate(_load_json_object(raw))
    assert material.translation == "platform nine"


def test_provider_factory_defaults_to_stub(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    assert isinstance(build_model(), StubModel)


def test_key_selects_live_model(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    assert isinstance(build_model(), ChatCompletionsModel)


def test_live_provider_posts_chat_completions(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "translation": "platform nine",
                                "vocabulary": [
                                    {
                                        "term": "nove",
                                        "explanation": "nine",
                                        "example": "São nove horas.",
                                    }
                                ],
                                "exercises": [{"prompt": "How do you say nine?", "answer": "nove"}],
                            }
                        )
                    }
                }
            ]
        }
        return httpx.Response(200, json=payload)

    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("MODEL_NAME", "muse-spark-1.3")
    model = build_model()

    def routed_post(url, **kwargs):
        kwargs.pop("verify", None)
        client = httpx.Client(transport=httpx.MockTransport(handler))
        try:
            return client.post(url, **kwargs)
        finally:
            client.close()

    monkeypatch.setattr(httpx, "post", routed_post)
    material = model.study(DOCUMENT, PASSAGE)
    assert material.translation == "platform nine"
    assert captured["url"] == "https://api.meta.ai/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"]["model"] == "muse-spark-1.3"
