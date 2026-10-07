"""
Unified Service Orchestrator for Integration Failure Analyzer.
Coordinates data preprocessing, rule classification, ML classification,
severity scoring, and root cause recommendation.
"""

from typing import Dict, Any, List, Union, Tuple
import pandas as pd

from .schemas import (
    FailureInput,
    FailureAnalysisResult,
    ClassificationComparison,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    DatasetStatistics
)
from .preprocessor import DataPreprocessor
from .classifier_rules import RuleBasedClassifier
from .classifier_ml import MLClassifier
from .severity_engine import SeverityEngine
from .recommender import RecommendationEngine

class IntegrationFailureAnalyzer:
    """End-to-end integration failure analysis engine."""

    def __init__(self, ml_model_path: str = None):
        self.preprocessor = DataPreprocessor()
        self.rule_classifier = RuleBasedClassifier()
        self.severity_engine = SeverityEngine()
        self.recommender = RecommendationEngine()
        self.ml_classifier = MLClassifier(model_path=ml_model_path)

    def analyze_single(self, failure: Union[FailureInput, Dict[str, Any]]) -> FailureAnalysisResult:
        """
        Analyzes an individual failure log record.
        Runs rule-based and ML classifiers, reconciles findings,
        scores severity, and generates recommendations.
        """
        if isinstance(failure, dict):
            failure = FailureInput(**failure)

        # 1. Clean individual inputs
        status = 0
        if failure.status_code is not None:
            try:
                status = int(failure.status_code)
            except (ValueError, TypeError):
                status = 0

        retries = max(0, failure.retry_count or 0)
        proc_time = max(0.0, float(failure.processing_time or 0.0))
        err_msg = str(failure.error_message or "").strip()
        iface = str(failure.interface or "").strip()
        src = str(failure.source or "Unknown").strip()
        tgt = str(failure.target or "Unknown").strip()

        # 2. Rule-based classification
        rule_cat, rule_conf, rule_reason = self.rule_classifier.classify(
            status_code=status,
            error_message=err_msg,
            interface=iface
        )

        # 3. ML classification
        ml_cat, ml_conf = self.ml_classifier.predict_single(
            interface=iface,
            source=src,
            target=tgt,
            status_code=status,
            error_message=err_msg
        )

        # 4. Reconciliation / Comparison
        agreement = (rule_cat == ml_cat)
        
        # Primary category selection:
        # If rule found a specific category with confidence >= 0.85, use it.
        # If rule was Unknown but ML has reasonable confidence, use ML.
        # Otherwise, if ML confidence > 0.85 and rule is generic, use ML.
        if rule_cat != "Unknown" and rule_conf >= 0.85:
            final_cat = rule_cat
            final_conf = rule_conf
        elif rule_cat == "Unknown" and ml_conf >= 0.50 and ml_cat != "Unknown":
            final_cat = ml_cat
            final_conf = ml_conf
        elif ml_conf > rule_conf and ml_cat != "Unknown":
            final_cat = ml_cat
            final_conf = ml_conf
        else:
            final_cat = rule_cat
            final_conf = rule_conf

        # 5. Severity scoring
        severity, badge, score, reasoning = self.severity_engine.evaluate(
            category=final_cat,
            interface=iface,
            status_code=status,
            retry_count=retries,
            processing_time=proc_time
        )

        # 6. Recommendation
        recommendation = self.recommender.generate_recommendation(
            category=final_cat,
            status_code=status,
            error_message=err_msg,
            source=src,
            target=tgt
        )

        return FailureAnalysisResult(
            category=final_cat,
            severity=severity,
            severity_badge=badge,
            confidence=round(final_conf, 2),
            recommendation=recommendation,
            reasoning=reasoning,
            details={
                "interface": iface,
                "source": src,
                "target": tgt,
                "status_code": status,
                "retry_count": retries,
                "processing_time_ms": proc_time,
                "severity_score": score,
                "comparison": {
                    "rule_category": rule_cat,
                    "rule_reason": rule_reason,
                    "rule_confidence": rule_conf,
                    "ml_category": ml_cat,
                    "ml_confidence": ml_conf,
                    "agreement": agreement
                }
            }
        )

    def analyze_batch(self, request: BatchAnalysisRequest) -> BatchAnalysisResponse:
        """Analyzes a list of failure inputs."""
        results = [self.analyze_single(f) for f in request.failures]
        return BatchAnalysisResponse(
            total_processed=len(results),
            results=results
        )

    def process_and_analyze_dataframe(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
        """
        Cleans dataset, classifies all records, attaches severity/recommendations,
        and computes complete aggregate statistics.
        """
        cleaned_df, audit = self.preprocessor.clean_and_validate(df)

        categories = []
        severities = []
        severity_badges = []
        confidences = []
        recommendations = []
        reasonings = []

        for _, row in cleaned_df.iterrows():
            result = self.analyze_single(FailureInput(
                interface=row.get("interface", ""),
                source=row.get("source", ""),
                target=row.get("target", ""),
                status_code=row.get("status_code", 0),
                error_message=row.get("error_message", ""),
                processing_time=row.get("processing_time", 0.0),
                retry_count=row.get("retry_count", 0),
                timestamp=row.get("timestamp", None)
            ))
            categories.append(result.category)
            severities.append(result.severity)
            severity_badges.append(result.severity_badge)
            confidences.append(result.confidence)
            recommendations.append(result.recommendation)
            reasonings.append(result.reasoning)

        cleaned_df["category"] = categories
        cleaned_df["severity"] = severities
        cleaned_df["severity_badge"] = severity_badges
        cleaned_df["confidence"] = confidences
        cleaned_df["recommendation"] = recommendations
        cleaned_df["severity_reasoning"] = reasonings

        stats = self.preprocessor.generate_statistics(cleaned_df)

        return cleaned_df, audit, stats
