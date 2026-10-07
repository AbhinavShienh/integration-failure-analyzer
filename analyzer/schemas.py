"""
Pydantic schemas and data models for Integration Failure Analyzer.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FailureInput(BaseModel):
    interface: str = Field(..., description="Integration interface name, e.g. Customer_Master_Sync", examples=["Customer_Master_Sync"])
    source: Optional[str] = Field("Unknown", description="Source system, e.g. S4HANA, Salesforce", examples=["S4HANA"])
    target: Optional[str] = Field("Unknown", description="Target system, e.g. CRM, SAP_CPI", examples=["CRM"])
    status_code: Optional[Any] = Field(None, description="HTTP status or error code, e.g. 401, 504, 500", examples=[401])
    error_message: Optional[str] = Field("", description="Error message / exception stack or return string", examples=["Unauthorized client"])
    processing_time: Optional[float] = Field(0.0, description="Processing time in milliseconds", examples=[250.0])
    retry_count: Optional[int] = Field(0, description="Number of retries attempted", examples=[3])
    timestamp: Optional[str] = Field(None, description="ISO timestamp of the event", examples=["2026-10-07T10:00:00Z"])

class SeverityInfo(BaseModel):
    level: str = Field(..., description="Severity level: Critical, High, Medium, Low")
    badge: str = Field(..., description="Display badge: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low")
    score: float = Field(..., description="Calculated severity numerical score (0 - 100)")
    reasoning: str = Field(..., description="Detailed explanation of the assigned severity")

class ClassificationComparison(BaseModel):
    rule_category: str = Field(..., description="Classification category from rule-based engine")
    rule_reason: str = Field(..., description="Rule that matched")
    ml_category: Optional[str] = Field(None, description="Classification category from ML model")
    ml_confidence: Optional[float] = Field(None, description="Confidence score of ML prediction (0.0 - 1.0)")
    agreement: bool = Field(..., description="True if rule-based and ML predictions agree")

class FailureAnalysisResult(BaseModel):
    category: str = Field(..., description="Final resolved failure category")
    severity: str = Field(..., description="Final severity level: Critical, High, Medium, Low")
    severity_badge: str = Field(..., description="Severity badge: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low")
    confidence: float = Field(..., description="Confidence score of the classification (0.0 - 1.0)")
    recommendation: str = Field(..., description="Targeted root-cause fix and troubleshooting recommendation")
    reasoning: str = Field(..., description="Severity and classification reasoning")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadata, timing, retries, source/target, and engine comparison")

class BatchAnalysisRequest(BaseModel):
    failures: List[FailureInput]

class BatchAnalysisResponse(BaseModel):
    total_processed: int
    results: List[FailureAnalysisResult]

class PreprocessingSummary(BaseModel):
    total_records: int
    cleaned_records: int
    duplicates_removed: int
    missing_status_codes_imputed: int
    missing_messages_fixed: int
    negative_processing_times_fixed: int
    invalid_retries_fixed: int

class DatasetStatistics(BaseModel):
    total_failures: int
    category_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    top_failing_interfaces: Dict[str, int]
    status_code_distribution: Dict[str, int]
    source_distribution: Dict[str, int]
    target_distribution: Dict[str, int]
    retry_stats: Dict[str, float]
    processing_time_stats_ms: Dict[str, float]
