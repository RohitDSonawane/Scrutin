from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from app.tools.lib import transcribe

# ── Schemas ────────────────────────────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    media_url_or_path: str = Field(description="Direct URL to YouTube/TikTok or local media path.")

class TranscribeResponse(BaseModel):
    success: bool
    transcript: str
    provider: str  # "groq" | "openai"
    error_message: Optional[str] = None

class ImageAnalysisRequest(BaseModel):
    image_path: str = Field(description="Local file path to the claim image.")

class ImageAnalysisResponse(BaseModel):
    is_manipulated: bool
    manipulation_score: float = Field(description="TruFor forgery score (0.0 to 1.0).")
    predicted_country: Optional[str] = Field(None, description="StreetCLIP country location prediction.")
    gps_coordinates: Optional[str] = Field(None, description="EXIF metadata coordinates.")
    perceptual_hash: Optional[str] = Field(None, description="Image perceptual hash (pHash) for fast-path duplicate verification.")


# ── Tool functions ─────────────────────────────────────────────────────────────

def transcribe_media(request: TranscribeRequest, config: dict) -> TranscribeResponse:
    """Wrapper around lib/transcribe.py."""
    try:
        ok, text, provider = transcribe.transcribe_media(request.media_url_or_path, config)
        return TranscribeResponse(success=ok, transcript=text, provider=provider)
    except Exception as e:
        return TranscribeResponse(success=False, transcript="", provider="failed", error_message=str(e))


def analyze_image(request: ImageAnalysisRequest) -> ImageAnalysisResponse:
    """Stub image forensics analysis tool."""
    return ImageAnalysisResponse(
        is_manipulated=False,
        manipulation_score=0.0,
        predicted_country=None,
        gps_coordinates=None,
        perceptual_hash="PHASH_STUB",
    )
