"""Tests for Option B routed execution and the speech-to-text endpoint."""

import httpx
from fastapi.testclient import TestClient

from pt_pt_learning_companion.ai_models import (
    MetaTextClient,
    RoutedTextService,
    StubTextClient,
    build_text_client,
)
from pt_pt_learning_companion.app import create_app
from pt_pt_learning_companion.providers import StubModel
from pt_pt_learning_companion.speech import MetaTranscriber, Transcript, build_transcriber


class FailingThenStubClient:
    """Primary model raises; the fallback model succeeds."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, model, system, user, *, temperature=0.2, json_mode=False):
        self.calls.append(model)
        if len(self.calls) == 1:
            raise httpx.ConnectError("primary down")
        return StubTextClient().generate(model, system, user)


def _app(**kwargs):
    return create_app(StubModel(), **kwargs)


def test_generate_default_uses_spark_primary():
    service = RoutedTextService(StubTextClient(), confidence_threshold=0.6)
    client = TestClient(_app(text_service=service))
    response = client.post("/api/generate", json={"task": "translate", "text": "Bom dia."})
    assert response.status_code == 200
    body = response.json()
    assert body["route"]["model_used"] == "muse-spark-1.3"
    assert body["route"]["escalated"] is False
    assert body["route"]["used_fallback"] is False
    assert body["usage"]["total_tokens"] > 0


def test_generate_high_quality_low_confidence_escalates_to_wonder():
    # Low-confidence stub + quality=high should trigger the Wonder escalation path.
    service = RoutedTextService(StubTextClient(confidence=0.1), confidence_threshold=0.6)
    client = TestClient(_app(text_service=service))
    response = client.post(
        "/api/generate",
        json={"task": "explore", "text": "a restaurant in Porto", "quality": "high"},
    )
    assert response.status_code == 200
    route = response.json()["route"]
    assert route["escalated"] is True
    assert route["model_used"] == "muse-wonder"


def test_generate_primary_failure_falls_back_to_open_weights():
    service = RoutedTextService(FailingThenStubClient(), confidence_threshold=0.6)
    client = TestClient(_app(text_service=service))
    response = client.post("/api/generate", json={"task": "situation", "text": "doctor, payment"})
    assert response.status_code == 200
    route = response.json()["route"]
    assert route["used_fallback"] is True
    assert route["model_used"] == "muse-spark-open"


def test_generate_strict_budget_starts_on_open_weights():
    service = RoutedTextService(StubTextClient(), confidence_threshold=0.6)
    client = TestClient(_app(text_service=service))
    response = client.post(
        "/api/generate",
        json={"task": "translate", "text": "Olá", "budget_mode": "strict"},
    )
    assert response.status_code == 200
    assert response.json()["route"]["model_used"] == "muse-spark-open"


def test_generate_repeat_is_served_from_cache():
    class CountingClient:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, model, system, user, *, temperature=0.2, json_mode=False):
            self.calls += 1
            return StubTextClient().generate(model, system, user, temperature=temperature, json_mode=json_mode)

    counter = CountingClient()
    client = TestClient(_app(text_service=RoutedTextService(counter, confidence_threshold=0.6)))
    body = {"task": "translate", "text": "Bom dia."}
    first = client.post("/api/generate", json=body)
    second = client.post("/api/generate", json=body)
    other = client.post("/api/generate", json={"task": "translate", "text": "Boa noite."})
    assert first.status_code == second.status_code == other.status_code == 200
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert second.json()["text"] == first.json()["text"]
    assert other.json()["cached"] is False
    assert counter.calls == 2


def test_transcribe_returns_text_from_managed_provider():
    class FakeTranscriber:
        async def transcribe(self, audio, content_type, language):
            return Transcript(text="Bom dia, como está?", model="muse-voice-transcribe")

    client = TestClient(_app(transcriber=FakeTranscriber()))
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"fake-audio-bytes", "audio/webm")},
        data={"language": "pt-PT"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "Bom dia, como está?"
    assert body["model"] == "muse-voice-transcribe"


def test_transcribe_unavailable_returns_503_for_browser_fallback():
    class DownTranscriber:
        async def transcribe(self, audio, content_type, language):
            raise RuntimeError("no managed provider")

    client = TestClient(_app(transcriber=DownTranscriber()))
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"audio", "audio/webm")},
    )
    assert response.status_code == 503


def test_transcribe_rejects_empty_audio():
    class FakeTranscriber:
        async def transcribe(self, audio, content_type, language):
            return Transcript(text="x", model="m")

    client = TestClient(_app(transcriber=FakeTranscriber()))
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"", "audio/webm")},
    )
    assert response.status_code == 400


# --- Real-model wiring: a MODEL_API_KEY selects the live Meta clients. ---


def test_build_text_client_selects_meta_with_key(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    assert isinstance(build_text_client(), MetaTextClient)


def test_build_transcriber_selects_meta_with_key(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    assert isinstance(build_transcriber(), MetaTranscriber)


def test_build_defaults_to_stub_without_key(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    assert isinstance(build_text_client(), StubTextClient)
