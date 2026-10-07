"""
Pydantic schemas and data models for Integration Failure Analyzer.
Includes full OpenAPI examples for Swagger UI.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FailureInput(BaseModel):
    """
    Single integration failure input record.
    Supply either via the structured form fields OR paste raw JSON directly.
    """
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "🔴 HTTP 401 — OAuth Token Expired",
                    "description": "Customer master sync failing due to expired OAuth bearer token.",
                    "value": {
                        "interface": "Customer_Master_Sync",
                        "source": "Salesforce_CRM",
                        "target": "S4HANA",
                        "status_code": 401,
                        "error_message": "Unauthorized client: Bearer token expired or invalid JWT signature during OAuth handshake",
                        "processing_time": 320,
                        "retry_count": 3,
                        "timestamp": "2026-10-07T08:14:00Z"
                    }
                },
                {
                    "summary": "🔴 HTTP 504 — CPI Gateway Timeout",
                    "description": "Order creation flow timing out waiting for S/4HANA BAPI response.",
                    "value": {
                        "interface": "Order_Create_Inbound",
                        "source": "Shopify_Storefront",
                        "target": "S4HANA",
                        "status_code": 504,
                        "error_message": "Gateway Timeout: Upstream SAP S/4HANA took longer than 60000ms to respond to BAPI call",
                        "processing_time": 62400,
                        "retry_count": 4,
                        "timestamp": "2026-10-07T09:22:11Z"
                    }
                },
                {
                    "summary": "🔴 HTTP 500 — SAP SM12 Lock Table Overflow",
                    "description": "General ledger batch posting crashing SAP enqueue server.",
                    "value": {
                        "interface": "General_Ledger_Batch_Post",
                        "source": "BillingEngine",
                        "target": "S4HANA",
                        "status_code": 500,
                        "error_message": "Internal Server Error: SAP enqueue server lock table overflow (transaction SM12)",
                        "processing_time": 85000,
                        "retry_count": 4,
                        "timestamp": "2026-10-07T02:01:45Z"
                    }
                },
                {
                    "summary": "🟠 HTTP 502 — Cloud Connector Tunnel Offline",
                    "description": "Payment status update blocked due to Cloud Connector tunnel being offline.",
                    "value": {
                        "interface": "Payment_Status_Update",
                        "source": "Payment_Stripe",
                        "target": "S4HANA",
                        "status_code": 502,
                        "error_message": "Bad Gateway: SAP Cloud Connector subaccount tunnel hana-prd-s4 is offline",
                        "processing_time": 950,
                        "retry_count": 3,
                        "timestamp": "2026-10-07T11:05:30Z"
                    }
                },
                {
                    "summary": "🟠 HTTP 403 — Client Certificate Not Trusted",
                    "description": "Invoice posting to CPI rejected because mTLS certificate is missing from keystore.",
                    "value": {
                        "interface": "Invoice_Post_Out",
                        "source": "S4HANA",
                        "target": "SAP_CPI",
                        "status_code": 403,
                        "error_message": "Forbidden: Client certificate missing or not trusted in SAP CPI Keystore",
                        "processing_time": 420,
                        "retry_count": 2,
                        "timestamp": "2026-10-07T13:45:00Z"
                    }
                },
                {
                    "summary": "🟡 HTTP 422 — Credit Limit Exceeded",
                    "description": "Order blocked at S/4HANA due to customer credit limit breach.",
                    "value": {
                        "interface": "Order_Create_Inbound",
                        "source": "Shopify_Storefront",
                        "target": "S4HANA",
                        "status_code": 422,
                        "error_message": "Business Rule Violation: Credit limit exceeded for customer ACME_CORP (Limit: $50,000, Current Order: $68,000)",
                        "processing_time": 1950,
                        "retry_count": 0,
                        "timestamp": "2026-10-07T14:12:00Z"
                    }
                },
                {
                    "summary": "🟡 HTTP 400 — Missing Mandatory Field KUNNR",
                    "description": "Payload missing the SAP customer number (KUNNR) causing schema validation failure.",
                    "value": {
                        "interface": "Customer_Master_Sync",
                        "source": "Salesforce_CRM",
                        "target": "S4HANA",
                        "status_code": 400,
                        "error_message": "Bad Request: JSON schema validation error - missing mandatory field KUNNR in customer payload",
                        "processing_time": 180,
                        "retry_count": 0,
                        "timestamp": "2026-10-07T10:30:00Z"
                    }
                },
                {
                    "summary": "🟢 HTTP 400 — XML Parse Error",
                    "description": "Malformed EDI XML payload with mismatched closing tag.",
                    "value": {
                        "interface": "Shipment_Confirmation_EDI",
                        "source": "B2B_EDI_Partner",
                        "target": "SAP_CPI",
                        "status_code": 400,
                        "error_message": "XML parse exception — mismatched closing tag </itemRecord> at line 48 in EDI payload",
                        "processing_time": 300,
                        "retry_count": 0,
                        "timestamp": "2026-10-07T16:00:00Z"
                    }
                }
            ]
        }
    }

    interface: str = Field(
        ...,
        description="**Integration interface / flow name.** Identifies the specific integration scenario, e.g. `Customer_Master_Sync`, `Order_Create_Inbound`, `Invoice_Post_Out`.",
        examples=["Customer_Master_Sync"]
    )
    source: Optional[str] = Field(
        "Unknown",
        description="**Source system name.** The originating system that triggered the integration, e.g. `S4HANA`, `Salesforce_CRM`, `Shopify_Storefront`, `Workday_HCM`.",
        examples=["Salesforce_CRM"]
    )
    target: Optional[str] = Field(
        "Unknown",
        description="**Target system name.** The downstream system the message is being delivered to, e.g. `S4HANA`, `SAP_CPI`, `ServiceNow`, `WMS_Manhattan`.",
        examples=["S4HANA"]
    )
    status_code: Optional[Any] = Field(
        None,
        description="**HTTP status code or vendor error code.** Standard HTTP codes: `400`, `401`, `403`, `408`, `409`, `422`, `500`, `502`, `503`, `504`. Non-standard vendor codes like `599` or `0` are also accepted.",
        examples=[401]
    )
    error_message: Optional[str] = Field(
        "",
        description="**Full error message, exception text, or stack trace.** The richer the error message, the more precise the classification. SAP-specific tokens like `SM12`, `ST22`, `KUNNR`, `IDoc status 51` trigger specialized recommendations.",
        examples=["Unauthorized client: Bearer token expired or invalid JWT signature during OAuth handshake"]
    )
    processing_time: Optional[float] = Field(
        0.0,
        description="**End-to-end processing duration in milliseconds.** Used in severity calculation — values ≥ 30,000 ms indicate worker starvation or database hangs and increase severity score.",
        examples=[320.0]
    )
    retry_count: Optional[int] = Field(
        0,
        description="**Number of automatic retry attempts made.** Values ≥ 3 indicate dead-lettered failures where automated self-healing has been exhausted, significantly increasing severity.",
        examples=[3]
    )
    timestamp: Optional[str] = Field(
        None,
        description="**ISO 8601 event timestamp.** When the failure occurred, e.g. `2026-10-07T08:14:00Z`. Optional — defaults to current time if omitted.",
        examples=["2026-10-07T08:14:00Z"]
    )


class SeverityInfo(BaseModel):
    level: str = Field(..., description="Severity level string: `Critical`, `High`, `Medium`, or `Low`.")
    badge: str = Field(..., description="Severity badge with emoji: `🔴 Critical`, `🟠 High`, `🟡 Medium`, `🟢 Low`.")
    score: float = Field(..., description="Numerical severity score from **0 to 100** computed by the multi-factor scoring engine.")
    reasoning: str = Field(..., description="Human-readable explanation of exactly which factors contributed to this severity score.")


class ClassificationComparison(BaseModel):
    rule_category: str = Field(..., description="Category predicted by the **deterministic rule-based engine** (regex + status code heuristics).")
    rule_reason: str = Field(..., description="The specific rule or regex pattern that matched and drove the rule-based classification.")
    rule_confidence: Optional[float] = Field(None, description="Confidence score of rule-based classification (0.0 – 1.0).")
    ml_category: Optional[str] = Field(None, description="Category predicted by the **TF-IDF + Logistic Regression ML model**.")
    ml_confidence: Optional[float] = Field(None, description="Probability confidence of ML model prediction (0.0 – 1.0).")
    agreement: bool = Field(..., description="`true` if both rule-based and ML engines produced the same category prediction.")


class FailureAnalysisResult(BaseModel):
    """
    Complete analysis result for a single integration failure.
    """
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "category": "Authentication/Authorization",
                    "severity": "High",
                    "severity_badge": "🟠 High",
                    "confidence": 0.98,
                    "recommendation": "HTTP 401 → Authentication failure → Check OAuth client credentials, token expiry, and ensure technical communication user is unlocked.",
                    "reasoning": "Severity score is 65/100 (High). Key factors: Interface 'Customer_Master_Sync' is Tier-2 core operational; Authentication failure blocks subsequent automated API calls; Retries exhausted (3 attempts); automatic recovery failed.",
                    "details": {
                        "interface": "Customer_Master_Sync",
                        "source": "Salesforce_CRM",
                        "target": "S4HANA",
                        "status_code": 401,
                        "retry_count": 3,
                        "processing_time_ms": 320.0,
                        "severity_score": 65.0,
                        "comparison": {
                            "rule_category": "Authentication/Authorization",
                            "rule_reason": "Matched keyword pattern in error message and HTTP 401",
                            "rule_confidence": 0.98,
                            "ml_category": "Authentication/Authorization",
                            "ml_confidence": 0.978,
                            "agreement": True
                        }
                    }
                }
            ]
        }
    }

    category: str = Field(
        ...,
        description="**Final failure category** resolved by combining rule-based and ML predictions. One of: `Authentication/Authorization`, `Connectivity`, `Timeout`, `Validation/Data`, `Business error`, `Application/System error`, `Unknown`."
    )
    severity: str = Field(..., description="**Severity level string**: `Critical`, `High`, `Medium`, or `Low`.")
    severity_badge: str = Field(..., description="**Severity badge with emoji**: `🔴 Critical`, `🟠 High`, `🟡 Medium`, `🟢 Low`.")
    confidence: float = Field(..., description="**Overall classification confidence** (0.0 – 1.0). Derived from whichever engine (rule or ML) provided the stronger signal.")
    recommendation: str = Field(..., description="**Root-cause recommendation** — actionable troubleshooting steps referencing specific SAP transactions (SM12, ST22, BD87, OB52), CPI settings, or API configurations.")
    reasoning: str = Field(..., description="**Severity reasoning** — human-readable explanation of the 100-point multi-factor score breakdown covering interface criticality, category impact, retry exhaustion, and latency anomaly.")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="**Extended metadata**: includes `interface`, `source`, `target`, `status_code`, `retry_count`, `processing_time_ms`, `severity_score`, and `comparison` object showing rule vs ML engine breakdown."
    )


class BatchAnalysisRequest(BaseModel):
    """
    Batch request containing multiple failure records for simultaneous analysis.
    """
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Mixed severity batch — 3 failures",
                    "value": {
                        "failures": [
                            {
                                "interface": "Order_Create_Inbound",
                                "source": "Shopify_Storefront",
                                "target": "S4HANA",
                                "status_code": 504,
                                "error_message": "Gateway Timeout: Upstream SAP S/4HANA took longer than 60000ms to respond",
                                "processing_time": 62400,
                                "retry_count": 4
                            },
                            {
                                "interface": "Customer_Master_Sync",
                                "source": "Salesforce_CRM",
                                "target": "S4HANA",
                                "status_code": 400,
                                "error_message": "Bad Request: JSON schema validation error - missing mandatory field KUNNR",
                                "processing_time": 180,
                                "retry_count": 0
                            },
                            {
                                "interface": "Invoice_Post_Out",
                                "source": "S4HANA",
                                "target": "SAP_CPI",
                                "status_code": 500,
                                "error_message": "Internal Server Error: SAP enqueue server lock table overflow (transaction SM12)",
                                "processing_time": 85000,
                                "retry_count": 4
                            }
                        ]
                    }
                }
            ]
        }
    }
    failures: List[FailureInput] = Field(
        ...,
        description="**List of failure input records** to analyze simultaneously. Each record follows the same schema as the `/analyze` endpoint. No practical limit on batch size."
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
