from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from passport_data_model import DocumentType


DETECTION_MODEL_NAME = "PP-OCRv6_small_det"
PASSPORT_RECOGNITION_MODEL_NAME = "cyrillic_PP-OCRv5_mobile_rec"
ENGLISH_RECOGNITION_MODEL_NAME = "en_PP-OCRv5_mobile_rec"


@dataclass(frozen=True)
class OcrModelProfile:
    detection_model_name: str
    recognition_model_name: str


PASSPORT_PROFILE = OcrModelProfile(
    detection_model_name=DETECTION_MODEL_NAME,
    recognition_model_name=PASSPORT_RECOGNITION_MODEL_NAME,
)
RESIDENCE_PERMIT_PROFILE = OcrModelProfile(
    detection_model_name=DETECTION_MODEL_NAME,
    recognition_model_name=ENGLISH_RECOGNITION_MODEL_NAME,
)
OCR_MODEL_PROFILES = (PASSPORT_PROFILE, RESIDENCE_PERMIT_PROFILE)
PRIMARY_PROFILES: dict[DocumentType, OcrModelProfile] = {
    "passport": PASSPORT_PROFILE,
    "uaeResidencePermit": RESIDENCE_PERMIT_PROFILE,
}


def get_primary_profile(document_type: DocumentType) -> OcrModelProfile:
    return PRIMARY_PROFILES[document_type]


def get_required_model_names() -> tuple[str, ...]:
    return (
        DETECTION_MODEL_NAME,
        PASSPORT_RECOGNITION_MODEL_NAME,
        ENGLISH_RECOGNITION_MODEL_NAME,
    )


def create_pipeline_settings(
    profile: OcrModelProfile, model_root: Path | None = None
) -> dict[str, Any]:
    settings: dict[str, Any] = {
        "device": "cpu",
        "text_detection_model_name": profile.detection_model_name,
        "text_recognition_model_name": profile.recognition_model_name,
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
    }

    if model_root is not None:
        settings.update(
            {
                "text_detection_model_dir": str(
                    model_root / profile.detection_model_name
                ),
                "text_recognition_model_dir": str(
                    model_root / profile.recognition_model_name
                ),
            }
        )

    return settings
