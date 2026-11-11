"""Screenshot metadata analyzer for SCAMTRACE AI.
Extracts cryptographic hash, image dimensions, and MIME properties without OCR.
"""
import hashlib
import io
from typing import Any, Dict, Optional

from backend.app.analyzers.base import AnalysisResult, BaseAnalyzer

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ScreenshotAnalyzer(BaseAnalyzer):
    """Forensic metadata analyzer for screenshot and image artifacts."""

    def __init__(self):
        self.model_name = "ImageMetadata_Deterministic"
        self.model_version = "1.0.0"

    def analyze(self, raw_bytes: bytes, raw_text: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Inspect image bytes and extract dimensions and cryptographic digest."""
        sha256 = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else ""
        width = None
        height = None
        img_format = "UNKNOWN"

        if raw_bytes and HAS_PIL:
            try:
                with Image.open(io.BytesIO(raw_bytes)) as img:
                    width, height = img.size
                    img_format = img.format or "UNKNOWN"
            except Exception:
                pass

        meta = {
            "sha256": sha256,
            "size_bytes": len(raw_bytes),
            "width": width,
            "height": height,
            "format": img_format,
            "ocr_performed": False,
        }

        top_factors = []
        if width and height:
            top_factors.append({
                "feature": "dimensions",
                "contribution": 0.0,
                "direction": "benign",
                "value": f"{width}x{height}",
            })

        return AnalysisResult(
            label="benign",
            score=0.0,
            model_name=self.model_name,
            model_version=self.model_version,
            top_factors=top_factors,
            metadata=meta,
        )

