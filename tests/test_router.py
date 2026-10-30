from fastapi.testclient import TestClient

from pt_pt_learning_companion.app import create_app
from pt_pt_learning_companion.providers import StubModel


def test_model_plan_translate_standard():
    client = TestClient(create_app(StubModel()))
    response = client.post(
        "/api/model-plan",
        json={"task": "translate", "quality": "standard", "budget_mode": "normal"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["primary_model"] == "muse-spark-1.3"
    assert body["fallback_model"] == "muse-spark-open"
    assert body["escalation_model"] == "muse-wonder"
    assert body["use_escalation"] is False


def test_model_plan_translate_high_quality_enables_escalation():
    client = TestClient(create_app(StubModel()))
    response = client.post(
        "/api/model-plan",
        json={"task": "translate", "quality": "high", "budget_mode": "normal"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["use_escalation"] is True
    assert body["escalation_model"] == "muse-wonder"


def test_model_plan_strict_budget_prefers_open_weights():
    client = TestClient(create_app(StubModel()))
    response = client.post(
        "/api/model-plan",
        json={"task": "explore", "quality": "standard", "budget_mode": "strict"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["primary_model"] == "muse-spark-open"
    assert body["fallback_model"] == "muse-spark-1.3"
    assert body["escalation_model"] is None


def test_model_plan_transcribe_uses_voice_model():
    client = TestClient(create_app(StubModel()))
    response = client.post(
        "/api/model-plan",
        json={"task": "transcribe", "quality": "standard", "budget_mode": "normal"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["primary_model"] == "muse-voice-transcribe"
    assert body["fallback_model"] == "browser-speech-recognition"
