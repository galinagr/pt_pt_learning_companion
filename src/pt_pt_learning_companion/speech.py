"""European Portuguese speech.

- Text-to-speech uses the public European Portuguese neural voice (no key stored).
- Speech-to-text (dictation) uses Muse Voice Transcribe via the Meta Model API,
  with a browser-native fallback handled on the client (ADR 0002, Option B hybrid).
"""

from dataclasses import dataclass
import os
from typing import Protocol

import edge_tts
import httpx

from pt_pt_learning_companion.ai_router import model_base_url, tls_verify

VOICE = "pt-PT-RaquelNeural"
TRANSCRIBE_MODEL = "muse-voice-transcribe"


def _rate(speed: float) -> str:
    percent = round((speed - 1) * 100)
    return f"{percent:+d}%"


async def synthesize(text: str, speed: float = 1) -> bytes:
    communicate = edge_tts.Communicate(text, VOICE, rate=_rate(speed))
    chunks: list[bytes] = []
    async for piece in communicate.stream():
        if piece["type"] == "audio":
            chunks.append(piece["data"])
    if not chunks:
        raise RuntimeError("The Portuguese voice returned no audio.")
    return b"".join(chunks)


@dataclass(frozen=True)
class Transcript:
    text: str
    model: str


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, content_type: str, language: str) -> Transcript:
        """Return a transcript for one audio clip."""


class StubTranscriber:
    """Offline stand-in. Signals that no managed speech provider is configured."""

    async def transcribe(self, audio: bytes, content_type: str, language: str) -> Transcript:
        del audio, content_type, language
        raise RuntimeError("No managed transcription provider is configured.")


class MetaTranscriber:
    """Muse Voice Transcribe via the Meta Model API (audio transcription route)."""

    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def transcribe(self, audio: bytes, content_type: str, language: str) -> Transcript:
        async with httpx.AsyncClient(timeout=self.timeout, verify=tls_verify()) as client:
            response = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("audio", audio, content_type or "application/octet-stream")},
                data={"model": self.model, "language": language.split("-")[0]},
            )
        response.raise_for_status()
        body = response.json()
        text = (body.get("text") or "").strip()
        if not text:
            raise RuntimeError("Transcription returned no text.")
        return Transcript(text=text, model=self.model)


def build_transcriber() -> Transcriber:
    """Use Muse Voice Transcribe when MODEL_API_KEY is set; otherwise the offline stub."""
    api_key = os.environ.get("MODEL_API_KEY", "").strip()
    if not api_key:
        return StubTranscriber()
    return MetaTranscriber(
        base_url=model_base_url(),
        api_key=api_key,
        model=os.environ.get("META_MODEL_TRANSCRIBE", TRANSCRIBE_MODEL),
    )
