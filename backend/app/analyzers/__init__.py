"""Analyzer factory module for SCAMTRACE AI.
Analyzers are lazily instantiated to ensure instant cold starts.
"""
from typing import Dict, Optional
from backend.app.analyzers.base import BaseAnalyzer, AnalysisResult

_ANALYZER_INSTANCES: Dict[str, BaseAnalyzer] = {}


def get_analyzer(evidence_type: str) -> BaseAnalyzer:
    """Return the appropriate forensic analyzer instance for an evidence type (lazily loaded)."""
    norm_type = (evidence_type or "sms").lower().strip()

    if norm_type not in _ANALYZER_INSTANCES:
        if norm_type == "sms":
            from backend.app.analyzers.sms import SMSAnalyzer
            _ANALYZER_INSTANCES[norm_type] = SMSAnalyzer()
        elif norm_type == "url":
            from backend.app.analyzers.url import URLAnalyzer
            _ANALYZER_INSTANCES[norm_type] = URLAnalyzer()
        elif norm_type == "apk":
            from backend.app.analyzers.apk import APKAnalyzer
            _ANALYZER_INSTANCES[norm_type] = APKAnalyzer()
        elif norm_type in ("chat", "email_text", "phone_call", "call_log"):
            from backend.app.analyzers.text import TextAnalyzer
            _ANALYZER_INSTANCES[norm_type] = TextAnalyzer()
        elif norm_type == "screenshot":
            from backend.app.analyzers.screenshot import ScreenshotAnalyzer
            _ANALYZER_INSTANCES[norm_type] = ScreenshotAnalyzer()
        else:
            from backend.app.analyzers.sms import SMSAnalyzer
            _ANALYZER_INSTANCES[norm_type] = SMSAnalyzer()

    return _ANALYZER_INSTANCES[norm_type]

