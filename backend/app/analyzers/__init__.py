"""Analyzer factory module for SCAMTRACE AI."""
from typing import Dict
from backend.app.analyzers.base import BaseAnalyzer, AnalysisResult
from backend.app.analyzers.sms import SMSAnalyzer
from backend.app.analyzers.url import URLAnalyzer
from backend.app.analyzers.apk import APKAnalyzer
from backend.app.analyzers.text import TextAnalyzer
from backend.app.analyzers.screenshot import ScreenshotAnalyzer

_ANALYZERS: Dict[str, BaseAnalyzer] = {
    "sms": SMSAnalyzer(),
    "url": URLAnalyzer(),
    "apk": APKAnalyzer(),
    "chat": TextAnalyzer(),
    "email_text": TextAnalyzer(),
    "phone_call": TextAnalyzer(),
    "call_log": TextAnalyzer(),
    "screenshot": ScreenshotAnalyzer(),
}


def get_analyzer(evidence_type: str) -> BaseAnalyzer:
    """Return the appropriate forensic analyzer instance for an evidence type."""
    norm_type = evidence_type.lower().strip()
    return _ANALYZERS.get(norm_type, _ANALYZERS["sms"])
