"""HTTP app: one page, one study endpoint, and European Portuguese speech."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from pt_pt_learning_companion.ai_models import RoutedTextService, build_text_service
from pt_pt_learning_companion.ai_router import build_router_config, plan_model_route
from pt_pt_learning_companion.providers import StudyModel, build_model
from pt_pt_learning_companion.response_cache import ResponseCache
from pt_pt_learning_companion.schemas import (
    GenerateRequest,
    GenerateResponse,
    ModelPlanRequest,
    ModelPlanResponse,
    RouteInfo,
    SpeakRequest,
    StudyMaterial,
    StudyRequest,
    TokenUsage,
    TranscribeResponse,
)
from pt_pt_learning_companion.speech import Transcriber, build_transcriber, synthesize

GENERATE_INSTRUCTIONS = {
    "translate": (
        "You translate between English and European Portuguese (pt-PT). "
        'Return JSON only: {"pairs":[{"en":"...","pt":"..."}]}. '
        "One pair per sentence. No markdown."
    ),
    "explore": (
        "You write a practical guide about a place, in English and European Portuguese (pt-PT). "
        'Return JSON only: {"pairs":[{"en":"...","pt":"..."}],"options":[{"id":"history","label":"History"}],"more":[{"id":"name","label":"The name"}]}. '
        "On the first answer, include 4 options and leave more empty. "
        "On a follow-up, pairs answer that topic and more lists 2 or 3 deeper choices. "
        "On a deeper choice or a question, pairs answer it and more is empty. "
        "Obey the length line: short stays under 500 characters, long under 1000. No markdown."
    ),
    "situation": (
        "You prepare a real-life dialog in English and European Portuguese (pt-PT) from the user's keywords. "
        'Return JSON only: {"pairs":[{"en":"...","pt":"..."}],"options":[{"id":"pay","label":"Paying"}]}. '
        "On the first answer, include 4 distinct next-step options. "
        "When the user names a chosen topic, pairs are the lines for that topic only and options is empty. "
        "No markdown."
    ),
}

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"
PREVIEW_FILE = STATIC_DIR.parent / "preview" / "index.html"
DOWNLOADS_DIR = Path.home() / "Downloads"
Speaker = Callable[[str, float], Awaitable[bytes]]


def create_app(
    model: StudyModel | None = None,
    speaker: Speaker | None = None,
    text_service: RoutedTextService | None = None,
    transcriber: Transcriber | None = None,
    response_cache: ResponseCache | None = None,
) -> FastAPI:
    # Load a local .env (git-ignored) so MODEL_API_KEY etc. reach the process.
    # Existing environment variables win; nothing is overwritten.
    load_dotenv()
    study_model = model if model is not None else build_model()
    router_config = build_router_config()
    speak = speaker if speaker is not None else synthesize
    routed = text_service if text_service is not None else build_text_service()
    speech_to_text = transcriber if transcriber is not None else build_transcriber()
    cache = response_cache if response_cache is not None else ResponseCache()
    app = FastAPI(title="PT-PT Learning Companion", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8000", "http://localhost:8000", "null"],
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    if DOWNLOADS_DIR.is_dir():
        app.mount("/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(PREVIEW_FILE)

    @app.get("/api/editorial-videos")
    def editorial_videos() -> dict[str, list[dict[str, str]]]:
        return {"videos": _home_videos(limit=3)}

    @app.post("/api/speak")
    async def speak_portuguese(body: SpeakRequest) -> Response:
        try:
            audio = await speak(body.text.strip(), body.rate)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="European Portuguese speech did not start.") from exc
        return Response(content=audio, media_type="audio/mpeg")

    @app.post("/api/study", response_model=StudyMaterial)
    def study(body: StudyRequest) -> StudyMaterial:
        if _compact(body.passage) not in _compact(body.document):
            raise HTTPException(status_code=400, detail="Select a passage from the uploaded text.")
        try:
            return study_model.study(body.document, body.passage.strip())
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="The model provider request failed.") from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=502, detail="The model provider returned an unusable response.") from exc

    @app.post("/api/model-plan", response_model=ModelPlanResponse)
    def model_plan(body: ModelPlanRequest) -> ModelPlanResponse:
        return plan_model_route(body, router_config)

    @app.post("/api/generate", response_model=GenerateResponse)
    def generate(body: GenerateRequest) -> GenerateResponse:
        system = GENERATE_INSTRUCTIONS[body.task]
        key = cache.key(body, system)
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            result = routed.run(
                task=body.task,
                system=system,
                user=body.text.strip(),
                quality=body.quality,
                budget_mode=body.budget_mode,
                require_managed=body.require_managed,
                estimated_input_tokens=len(body.text) // 4,
                json_mode=True,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="The model provider request failed.") from exc
        response = GenerateResponse(
            text=result.text,
            route=RouteInfo(
                classifier_model=result.plan.classifier_model,
                primary_model=result.plan.primary_model,
                model_used=result.model_used,
                escalated=result.escalated,
                used_fallback=result.used_fallback,
                cache_recommended=result.plan.cache_recommended,
                estimated_cost_units=result.plan.estimated_cost_units,
                reason=result.plan.reason,
            ),
            usage=TokenUsage(
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens,
            ),
        )
        if result.plan.cache_recommended:
            cache.put(key, response)
        return response

    @app.post("/api/transcribe", response_model=TranscribeResponse)
    async def transcribe(
        file: UploadFile = File(...),
        language: str = Form("pt-PT"),
    ) -> TranscribeResponse:
        audio = await file.read()
        if not audio:
            raise HTTPException(status_code=400, detail="Send a non-empty audio clip.")
        try:
            result = await speech_to_text.transcribe(
                audio, file.content_type or "application/octet-stream", language
            )
        except Exception as exc:
            # Managed path unavailable: 503 tells the client to use browser speech (Option B fallback).
            raise HTTPException(
                status_code=503,
                detail="Managed transcription is unavailable. Use browser dictation.",
            ) from exc
        return TranscribeResponse(text=result.text, model=result.model)

    return app


def _compact(text: str) -> str:
    return " ".join(text.split())


def _home_videos(limit: int = 3) -> list[dict[str, str]]:
    if not DOWNLOADS_DIR.is_dir():
        return []
    files = [path for path in DOWNLOADS_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".mp4"]
    if not files:
        return []
    selected = sorted(
        files,
        key=lambda path: (
            0 if "mixkit" in path.name.lower() else 1,
            -path.stat().st_mtime,
        ),
    )[:limit]
    return [{"name": path.name, "url": "/downloads/" + quote(path.name)} for path in selected]


app = create_app()
