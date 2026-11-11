"""Base analyzer interface and common result data structures for SCAMTRACE AI."""
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TopFactor:
    feature: str
    contribution: float
    direction: str  # "suspicious" or "benign"
    value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature": self.feature,
            "contribution": round(self.contribution, 4),
            "direction": self.direction,
            "value": self.value,
        }


@dataclass
class AnalysisResult:
    label: str  # "benign" or "suspicious"
    score: float  # 0.0 to 1.0
    model_name: str
    model_version: str
    top_factors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "score": round(self.score, 4),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "top_factors": self.top_factors,
            "metadata": self.metadata,
        }


class BaseAnalyzer(ABC):
    """Abstract Base Class for all multimodal evidence analyzers."""

    @abstractmethod
    def analyze(self, raw_bytes: bytes, raw_text: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Execute purely offline forensic analysis and return structured result."""
        pass

