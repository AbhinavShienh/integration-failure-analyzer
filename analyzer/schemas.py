"""
Pydantic schemas and data models for Integration Failure Analyzer.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FailureInput(BaseModel):
    """
    Single integration failure input record.
    Supply either via the structured form fields OR paste raw JSON directly.
    """
    interface: str = Field(
        ...,
        description="Integration interface / flow name. Identifies the specific integration scenario, e.g. Customer_Master_Sync, Order_Create_Inbound, Invoice_Post_Out."
    )
    source: Optional[str] = Field(
        "Unknown",
        description="Source system name. The originating system that triggered the integration, e.g. S4HANA, Salesforce_CRM, Shopify_Storefront, Workday_HCM."
    )
    target: Optional[str] = Field(
        "Unknown",
        description="Target system name. The downstream system the message is being delivered to, e.g. S4HANA, SAP_CPI, ServiceNow, WMS_Manhattan."
    )
    status_code: Optional[Any] = Field(
        None,
        description="HTTP status code or vendor error code. Standard HTTP codes: 400, 401, 403, 408, 409, 422, 500, 502, 503, 504. Non-standard vendor codes like 599 or 0 are also accepted."
    )
    error_message: Optional[str] = Field(
        "",
        description="Full error message, exception text, or stack trace. The richer the error message, the more precise the classification. SAP-specific tokens like SM12, ST22, KUNNR, IDoc status 51 trigger specialized recommendations."
    )
    processing_time: Optional[float] = Field(
        0.0,
        description="End-to-end processing duration in milliseconds. Used in severity calculation — values >= 30,000 ms indicate worker starvation or database hangs and increase severity score."
    )
    retry_count: Optional[int] = Field(
        0,
        description="Number of automatic retry attempts made. Values >= 3 indicate dead-lettered failures where automated self-healing has been exhausted, significantly increasing severity."
    )
    timestamp: Optional[str] = Field(
        None,
        description="ISO 8601 event timestamp. When the failure occurred, e.g. 2026-10-07T08:14:00Z. Optional — defaults to current time if omitted."
    )


class SeverityInfo(BaseModel):
    level: str = Field(..., description="Severity level string: Critical, High, Medium, or Low.")
    badge: str = Field(..., description="Severity badge with emoji: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low.")
    score: float = Field(..., description="Numerical severity score from 0 to 100 computed by the multi-factor scoring engine.")
    reasoning: str = Field(..., description="Human-readable explanation of exactly which factors contributed to this severity score.")


class ClassificationComparison(BaseModel):
    rule_category: str = Field(..., description="Category predicted by the deterministic rule-based engine (regex + status code heuristics).")
    rule_reason: str = Field(..., description="The specific rule or regex pattern that matched and drove the rule-based classification.")
    rule_confidence: Optional[float] = Field(None, description="Confidence score of rule-based classification (0.0 – 1.0).")
    ml_category: Optional[str] = Field(None, description="Category predicted by the TF-IDF + Logistic Regression ML model.")
    ml_confidence: Optional[float] = Field(None, description="Probability confidence of ML model prediction (0.0 – 1.0).")
    agreement: bool = Field(..., description="true if both rule-based and ML engines produced the same category prediction.")


class FailureAnalysisResult(BaseModel):
    """
    Complete analysis result for a single integration failure.
    """
    category: str = Field(
        ...,
        description="Final failure category resolved by combining rule-based and ML predictions. One of: Authentication/Authorization, Connectivity, Timeout, Validation/Data, Business error, Application/System error, Unknown."
    )
    severity: str = Field(..., description="Severity level string: Critical, High, Medium, or Low.")
    severity_badge: str = Field(..., description="Severity badge with emoji: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low.")
    confidence: float = Field(..., description="Overall classification confidence (0.0 – 1.0). Derived from whichever engine (rule or ML) provided the stronger signal.")
    recommendation: str = Field(..., description="Root-cause recommendation — actionable troubleshooting steps referencing specific SAP transactions (SM12, ST22, BD87, OB52), CPI settings, or API configurations.")
    reasoning: str = Field(..., description="Severity reasoning — human-readable explanation of the 100-point multi-factor score breakdown covering interface criticality, category impact, retry exhaustion, and latency anomaly.")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extended metadata: includes interface, source, target, status_code, retry_count, processing_time_ms, severity_score, and comparison object showing rule vs ML engine breakdown."
    )


class BatchAnalysisRequest(BaseModel):
    """
    Batch request containing multiple failure records for simultaneous analysis.
    """
    failures: List[FailureInput] = Field(
        ...,
        description="List of failure input records to analyze simultaneously. Each record follows the same schema as the /analyze endpoint. No practical limit on batch size."
    )


class BatchAnalysisResponse(BaseModel):
    total_processed: int = Field(..., description="Total number of failure records processed in this batch.")
    results: List[FailureAnalysisResult] = Field(..., description="Ordered list of analysis results, one per input failure record.")


class PreprocessingSummary(BaseModel):
    total_records: int = Field(..., description="Total records found in the uploaded file before any cleaning.")
    cleaned_records: int = Field(..., description="Records remaining after deduplication and validation.")
    duplicates_removed: int = Field(..., description="Exact duplicate rows removed during preprocessing.")
    missing_status_codes_imputed: int = Field(..., description="Records where status_code was null — extracted from error message text via regex.")
    missing_messages_fixed: int = Field(..., description="Records where error_message was empty — replaced with a default placeholder.")
    negative_processing_times_fixed: int = Field(..., description="Records where processing_time was negative — corrected to absolute value.")
    invalid_retries_fixed: int = Field(..., description="Records where retry_count was null or non-integer — defaulted to 0.")


class DatasetStatistics(BaseModel):
    total_failures: int = Field(..., description="Total number of failure records in the dataset.")
    category_distribution: Dict[str, int] = Field(..., description="Count of failures per classification category.")
    severity_distribution: Dict[str, int] = Field(..., description="Count of failures per severity level (Critical, High, Medium, Low).")
    top_failing_interfaces: Dict[str, int] = Field(..., description="Top 10 interfaces ranked by failure count.")
    status_code_distribution: Dict[str, int] = Field(..., description="Count of occurrences per HTTP/error status code.")
    source_distribution: Dict[str, int] = Field(..., description="Top 8 source systems ranked by failure count.")
    target_distribution: Dict[str, int] = Field(..., description="Top 8 target systems ranked by failure count.")
    retry_stats: Dict[str, float] = Field(..., description="Retry statistics: mean, max, and percentage of failures that were retried at least once.")
    processing_time_stats_ms: Dict[str, float] = Field(..., description="Processing time distribution in ms: min, mean, median, p95 (95th percentile), max.")
