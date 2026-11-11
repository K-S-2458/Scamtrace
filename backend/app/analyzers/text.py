"""Chat and email text analyzer for SCAMTRACE AI.
Leverages the text classification model and extracts textual structure hints.
"""
from typing import Any, Dict, Optional

from backend.app.analyzers.base import AnalysisResult, BaseAnalyzer
from backend.app.analyzers.sms import SMSAnalyzer


class TextAnalyzer(BaseAnalyzer):
    """Forensic analyzer for chat messages and email text."""

    def __init__(self):
        self.sms_analyzer = SMSAnalyzer()
        self.model_name = "Text_TFIDF_LogisticRegression"
        self.model_version = "1.0.0"

    def analyze(self, raw_bytes: bytes, raw_text: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Analyze chat or email text using underlying n-gram text classifier."""
        res = self.sms_analyzer.analyze(raw_bytes, raw_text, metadata)
        # Adapt model name for tracking
        res.model_name = self.model_name
        res.model_version = self.model_version
        return res

