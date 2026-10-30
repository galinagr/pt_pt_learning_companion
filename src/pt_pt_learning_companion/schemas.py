"""Request and response shapes for a study turn."""

from pydantic import BaseModel, Field


class VocabularyItem(BaseModel):
    term: str
    explanation: str
    example: str


class Exercise(BaseModel):
    prompt: str
    answer: str


class StudyMaterial(BaseModel):
    translation: str
    vocabulary: list[VocabularyItem] = Field(min_length=1)
    exercises: list[Exercise] = Field(min_length=1)


class StudyRequest(BaseModel):
    document: str = Field(min_length=1, max_length=100_000)
    passage: str = Field(min_length=1, max_length=4_000)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=6_000)
    rate: float = Field(default=1, ge=0.5, le=1)


class ModelPlanRequest(BaseModel):
    task: str = Field(pattern="^(translate|explore|situation|transcribe|image|segment)$")
    quality: str = Field(default="standard", pattern="^(standard|high)$")
    budget_mode: str = Field(default="normal", pattern="^(normal|tight|strict)$")
    require_managed: bool = False
    estimated_input_tokens: int = Field(default=0, ge=0, le=200_000)
    estimated_output_tokens: int = Field(default=0, ge=0, le=200_000)


class ModelPlanResponse(BaseModel):
    task: str
    classifier_model: str
    primary_model: str
    fallback_model: str
    escalation_model: str | None = None
    use_escalation: bool
    cache_recommended: bool
    estimated_cost_units: float
    reason: str


class GenerateRequest(BaseModel):
    task: str = Field(pattern="^(translate|explore|situation)$")
    text: str = Field(min_length=1, max_length=6_000)
    quality: str = Field(default="standard", pattern="^(standard|high)$")
    budget_mode: str = Field(default="normal", pattern="^(normal|tight|strict)$")
    require_managed: bool = False


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class RouteInfo(BaseModel):
    classifier_model: str
    primary_model: str
    model_used: str
    escalated: bool
    used_fallback: bool
    cache_recommended: bool
    estimated_cost_units: float
    reason: str


class GenerateResponse(BaseModel):
    text: str
    route: RouteInfo
    usage: TokenUsage


class TranscribeResponse(BaseModel):
    text: str
    model: str
