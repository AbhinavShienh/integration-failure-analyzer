"""
FastAPI REST API for Integration Failure Analyzer.
Full OpenAPI/Swagger documentation with tagged endpoints, rich descriptions,
request body examples, and complete response schemas.
"""

import os
import json
from typing import Dict, Any
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from analyzer.service import IntegrationFailureAnalyzer
from analyzer.schemas import (
    FailureInput,
    FailureAnalysisResult,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    DatasetStatistics
)

# ─────────────────────────── Tag Metadata ────────────────────────────
tags_metadata = [
    {
        "name": "Analysis",
        "description": (
            "Core analysis endpoints. Submit an integration failure record "
            "and receive back the **failure category**, **severity level** (🔴🟠🟡🟢), "
            "**confidence score**, and an **actionable root-cause recommendation** "
            "tailored to SAP S/4HANA, SAP CPI, Salesforce, and other enterprise platforms."
        ),
    },
    {
        "name": "File Ingestion",
        "description": (
            "Upload a `.csv` or `.json` failure log file. "
            "The engine will **validate, clean, and deduplicate** the dataset, "
            "then classify every record and return aggregate statistics alongside a "
            "per-record classification table."
        ),
    },
    {
        "name": "Analytics",
        "description": (
            "Aggregated dataset metrics: category distribution, severity breakdown, "
            "top failing interfaces, status code frequencies, and processing-time percentiles."
        ),
    },
    {
        "name": "System",
        "description": "Health check and service readiness probes.",
    },
    {
        "name": "Dashboard",
        "description": "Interactive web dashboard UI rendered server-side.",
    },
]

# ─────────────────────────── App Init ────────────────────────────────
app = FastAPI(
    title="Integration Failure Analyzer API",
    description="""...""",
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url=None,
    redoc_url=None,
    contact={
        "name": "Integration Failure Analyzer",
    },
    license_info={
        "name": "MIT",
    },
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

analyzer = IntegrationFailureAnalyzer()

DEFAULT_DATA_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "synthetic_failures.csv")
cached_stats: Dict[str, Any] = {}

def load_initial_stats():
    global cached_stats
    if os.path.exists(DEFAULT_DATA_PATH):
        try:
            df = analyzer.preprocessor.load_data(DEFAULT_DATA_PATH)
            _, _, stats = analyzer.process_and_analyze_dataframe(df)
            cached_stats = stats
        except Exception as e:
            print(f"Warning: Failed to load initial dataset stats: {e}")

load_initial_stats()


# ─────────────────────────── Endpoints ───────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="Service health check",
    response_description="Service status and ML model readiness",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "Integration Failure Analyzer",
                        "ml_model_loaded": True
                    }
                }
            }
        }
    }
)
def health_check():
    """
    Returns service liveness status and whether the ML classification model is loaded.

    Use this for **Kubernetes readiness/liveness probes** or monitoring health checks.
    """
    return {
        "status": "healthy",
        "service": "Integration Failure Analyzer",
        "ml_model_loaded": analyzer.ml_classifier.pipeline is not None
    }


@app.post(
    "/analyze",
    response_model=FailureAnalysisResult,
    tags=["Analysis"],
    summary="Analyze a single integration failure",
    response_description="Complete diagnosis: category, severity badge, confidence, recommendation, and engine comparison",
    responses={
        200: {
            "description": "Successful analysis result",
            "content": {
                "application/json": {
                    "example": {
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
                                "rule_reason": "Matched keyword pattern and HTTP 401",
                                "rule_confidence": 0.98,
                                "ml_category": "Authentication/Authorization",
                                "ml_confidence": 0.978,
                                "agreement": True
                            }
                        }
                    }
                }
            }
        },
        422: {"description": "Validation error — required field `interface` is missing or malformed"},
        500: {"description": "Internal analysis engine error"}
    }
)
def analyze_single_failure(
    failure: FailureInput = Body(
        ...,
        openapi_extra={
            "examples": {
                "auth_401": {
                    "summary": "🔴 HTTP 401 — OAuth Token Expired",
                    "description": "Customer master sync failing due to an expired OAuth bearer token. Tier-2 interface with 3 retries exhausted.",
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
                "timeout_504": {
                    "summary": "🔴 HTTP 504 — CPI Gateway Timeout (Tier-1)",
                    "description": "Order creation timing out waiting for SAP S/4HANA BAPI response. Tier-1 critical interface — highest severity.",
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
                "sm12_lock_500": {
                    "summary": "🔴 HTTP 500 — SAP SM12 Lock Table Overflow",
                    "description": "General ledger batch posting crashing due to SAP enqueue server lock table overflow.",
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
                "idoc_status51": {
                    "summary": "🔴 HTTP 500 — IDoc Status 51 (Document Not Posted)",
                    "description": "Invoice posting IDoc failing with status 51 due to a database deadlock.",
                    "value": {
                        "interface": "Invoice_Post_Out",
                        "source": "S4HANA",
                        "target": "SAP_CPI",
                        "status_code": 500,
                        "error_message": "IDoc status 51: Application document not posted due to database deadlock in posting engine",
                        "processing_time": 4300,
                        "retry_count": 3,
                        "timestamp": "2026-10-07T06:45:00Z"
                    }
                },
                "tunnel_502": {
                    "summary": "🟠 HTTP 502 — Cloud Connector Tunnel Offline",
                    "description": "Payment status update blocked because Cloud Connector subaccount tunnel is offline.",
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
                "cert_403": {
                    "summary": "🟠 HTTP 403 — Client Certificate Not Trusted in CPI Keystore",
                    "description": "mTLS certificate for Invoice posting is missing or expired in the SAP CPI keystore.",
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
                "pool_503": {
                    "summary": "🟠 HTTP 503 — Connection Pool Exhausted",
                    "description": "Backend connection pool for order creation is fully exhausted.",
                    "value": {
                        "interface": "Order_Create_Inbound",
                        "source": "Shopify_Storefront",
                        "target": "S4HANA",
                        "status_code": 503,
                        "error_message": "Service Unavailable: Backend connection pool exhausted — max 150 active connections reached",
                        "processing_time": 1500,
                        "retry_count": 4,
                        "timestamp": "2026-10-07T07:15:00Z"
                    }
                },
                "abap_dump_500": {
                    "summary": "🟠 HTTP 500 — SAP ABAP Runtime Dump ST22",
                    "description": "ABAP runtime exception DYNPRO_NOT_FOUND in function module call.",
                    "value": {
                        "interface": "Order_Create_Inbound",
                        "source": "Shopify_Storefront",
                        "target": "S4HANA",
                        "status_code": 500,
                        "error_message": "Internal Server Error: SAP ABAP runtime dump DYNPRO_NOT_FOUND in function module BAPI_SALESORDER_CREATEFROMDAT2",
                        "processing_time": 2100,
                        "retry_count": 2,
                        "timestamp": "2026-10-07T10:00:00Z"
                    }
                },
                "credit_422": {
                    "summary": "🟡 HTTP 422 — Credit Limit Exceeded",
                    "description": "SAP S/4HANA FSCM credit limit rule triggered for high-value order.",
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
                "period_422": {
                    "summary": "🟡 HTTP 422 — SAP Posting Period Closed",
                    "description": "Fiscal posting period is closed in company code 1000 for September 2026.",
                    "value": {
                        "interface": "General_Ledger_Batch_Post",
                        "source": "BillingEngine",
                        "target": "S4HANA",
                        "status_code": 422,
                        "error_message": "Business Rule Violation: SAP Posting period 09/2026 is closed in company code 1000",
                        "processing_time": 900,
                        "retry_count": 1,
                        "timestamp": "2026-10-07T23:00:00Z"
                    }
                },
                "kunnr_400": {
                    "summary": "🟡 HTTP 400 — Missing Mandatory Field KUNNR",
                    "description": "Payload from Salesforce missing the SAP customer number (KUNNR).",
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
                "duplicate_409": {
                    "summary": "🟡 HTTP 409 — Duplicate Purchase Order",
                    "description": "PO-98231 already exists in S/4HANA — idempotency check failed.",
                    "value": {
                        "interface": "Order_Create_Inbound",
                        "source": "Shopify_Storefront",
                        "target": "S4HANA",
                        "status_code": 409,
                        "error_message": "Conflict: Duplicate document error — Purchase Order PO-98231 already exists in SAP S/4HANA",
                        "processing_time": 700,
                        "retry_count": 1,
                        "timestamp": "2026-10-07T15:00:00Z"
                    }
                },
                "xml_parse_400": {
                    "summary": "🟢 HTTP 400 — XML Parse Error in EDI Payload",
                    "description": "Malformed XML from B2B EDI partner with a mismatched closing tag.",
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
                },
                "payload_size_400": {
                    "summary": "🟢 HTTP 400 — Payload Too Large",
                    "description": "Product catalog export exceeds the 10 MB CPI message size limit.",
                    "value": {
                        "interface": "Product_Catalog_Export",
                        "source": "S4HANA",
                        "target": "Salesforce_CRM",
                        "status_code": 400,
                        "error_message": "Bad Request: Request payload size 38MB exceeds maximum allowed message limit of 10MB on CPI",
                        "processing_time": 620,
                        "retry_count": 0,
                        "timestamp": "2026-10-07T17:30:00Z"
                    }
                },
                "unknown_599": {
                    "summary": "🟢 Code 599 — Unknown Legacy Gateway Error",
                    "description": "Unrecognized vendor response code from a legacy banking gateway.",
                    "value": {
                        "interface": "Vendor_Remittance_Advice",
                        "source": "S4HANA",
                        "target": "Banking_API",
                        "status_code": 599,
                        "error_message": "Unrecognized vendor response code 9999 from legacy banking gateway — no protocol mapping found",
                        "processing_time": 400,
                        "retry_count": 0,
                        "timestamp": "2026-10-07T18:00:00Z"
                    }
                }
            }
        }
    )
):
    """
    ## Analyze a Single Integration Failure

    Submit one integration failure record and receive a complete diagnosis:

    | Output Field | Description |
    |---|---|
    | `category` | Failure classification (7 categories) |
    | `severity` / `severity_badge` | 🔴🟠🟡🟢 severity level |
    | `confidence` | Classification confidence 0.0 – 1.0 |
    | `recommendation` | Actionable root-cause fix |
    | `reasoning` | Explanation of severity score |
    | `details.comparison` | Rule engine vs ML model side-by-side |

    ### Classification Logic
    Two engines run in parallel:
    1. **Rule-Based Engine** — regex patterns + HTTP status code heuristics tuned for SAP CPI and S/4HANA terminology
    2. **ML Classifier** — TF-IDF (n-grams 1–2) + Logistic Regression trained on 1,200+ synthetic enterprise failures

    The engine with the higher confidence wins. If they agree, `details.comparison.agreement = true`.

    ### Severity Scoring (100-point model)
    - **Interface business criticality** (Tier-1 payment/order flows score highest)
    - **Failure category impact** (System crash > Connectivity > Auth > Validation)
    - **Retry exhaustion** (≥ 3 retries = dead-lettered, +25 pts)
    - **Processing latency anomaly** (≥ 30s = worker starvation, +10 pts)

    ### 💡 Tip
    Use the **dropdown examples** in Swagger UI (the selector next to *"Example Value"*) to quickly load and test all 14 pre-built failure scenarios.
    """
    try:
        result = analyzer.analyze_single(failure)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post(
    "/analyze/batch",
    response_model=BatchAnalysisResponse,
    tags=["Analysis"],
    summary="Analyze multiple failures in one request",
    response_description="Array of analysis results, one per input failure record",
    responses={
        200: {
            "description": "Batch analysis complete",
            "content": {
                "application/json": {
                    "example": {
                        "total_processed": 2,
                        "results": [
                            {
                                "category": "Timeout",
                                "severity": "Critical",
                                "severity_badge": "🔴 Critical",
                                "confidence": 0.98,
                                "recommendation": "HTTP 504 → Gateway Timeout → Check target-system availability, database query performance, and increase CPI route timeout configuration.",
                                "reasoning": "Severity score is 95/100 (Critical).",
                                "details": {}
                            },
                            {
                                "category": "Validation/Data",
                                "severity": "Medium",
                                "severity_badge": "🟡 Medium",
                                "confidence": 0.98,
                                "recommendation": "Payload missing mandatory field (e.g. KUNNR/Customer Number); check source mapping in CPI.",
                                "reasoning": "Severity score is 30/100 (Low).",
                                "details": {}
                            }
                        ]
                    }
                }
            }
        },
        422: {"description": "Validation error in one or more failure records"},
        500: {"description": "Batch analysis engine error"}
    }
)
def analyze_batch_failures(request: BatchAnalysisRequest):
    """
    ## Analyze Multiple Integration Failures in One Request

    Submit an array of failure records and get back a classified result for each one.

    Useful for:
    - **Bulk triage** of a failure queue after an incident
    - **Programmatic analysis** of exported CPI monitoring logs
    - **Batch scoring** of historical failure data for reporting

    Results are returned **in the same order** as the input array.

    ### Example use case
    Export a failed message list from **SAP CPI Monitoring** → paste the array here →
    receive priority-sorted triage recommendations instantly.

    > **Tip:** Use the pre-built *"Mixed severity batch — 3 failures"* example to see how
    > a Timeout, a Validation error, and a System error are handled simultaneously.
    """
    try:
        return analyzer.analyze_batch(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@app.post(
    "/analyze/file",
    tags=["File Ingestion"],
    summary="Upload and analyze a CSV or JSON failure log file",
    response_description="Cleaning audit, aggregate statistics, and top 100 classified records",
    responses={
        200: {
            "description": "File processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "filename": "sap_cpi_failures.csv",
                        "cleaning_audit": {
                            "total_records": 1206,
                            "cleaned_records": 1205,
                            "duplicates_removed": 1,
                            "missing_status_codes_imputed": 1,
                            "missing_messages_fixed": 1,
                            "negative_processing_times_fixed": 1,
                            "invalid_retries_fixed": 1
                        },
                        "statistics": {
                            "total_failures": 1205,
                            "category_distribution": {
                                "Validation/Data": 262,
                                "Connectivity": 239,
                                "Authentication/Authorization": 216
                            },
                            "severity_distribution": {
                                "Critical": 289,
                                "High": 412,
                                "Medium": 380,
                                "Low": 124
                            }
                        },
                        "sample_results": []
                    }
                }
            }
        },
        400: {"description": "Invalid file format or corrupted file"},
        422: {"description": "Unsupported file type (only .csv and .json accepted)"}
    }
)
async def analyze_file(
    file: UploadFile = File(
        ...,
        description=(
            "Upload a `.csv` or `.json` failure log file.\n\n"
            "**CSV format** — must include these columns (extras are ignored):\n"
            "`interface`, `source`, `target`, `status_code`, `error_message`, "
            "`processing_time`, `retry_count`\n\n"
            "**JSON format** — array of objects with the same field names.\n\n"
            "The engine will automatically:\n"
            "- Remove exact duplicate rows\n"
            "- Impute missing `status_code` values by extracting HTTP codes from the error message text\n"
            "- Fix negative `processing_time` values\n"
            "- Default null `retry_count` to 0\n"
            "- Replace empty `error_message` with a placeholder\n\n"
            "**Sample file:** `data/synthetic_failures.csv` in the project root."
        )
    )
):
    """
    ## Upload & Analyze a Failure Log File

    Upload a `.csv` or `.json` integration failure log and receive:

    1. **Cleaning Audit** — counts of duplicates removed, nulls imputed, and anomalies fixed
    2. **Aggregate Statistics** — category distribution, severity breakdown, top interfaces, status codes, latency percentiles
    3. **Classified Records** — top 100 records with `category`, `severity`, `confidence`, and `recommendation` attached

    ### Accepted CSV Columns
    | Column | Required | Description |
    |---|---|---|
    | `interface` | ✅ | Interface name |
    | `source` | ✅ | Source system |
    | `target` | ✅ | Target system |
    | `status_code` | ✅ | HTTP / error code |
    | `error_message` | ✅ | Error text |
    | `processing_time` | optional | Duration in ms |
    | `retry_count` | optional | Retry attempts |
    | `timestamp` | optional | ISO timestamp |

    ### JSON Array Format
    ```json
    [
      {
        "interface": "Order_Create_Inbound",
        "source": "Shopify_Storefront",
        "target": "S4HANA",
        "status_code": 504,
        "error_message": "Gateway Timeout after 60000ms",
        "processing_time": 62400,
        "retry_count": 3
      }
    ]
    ```

    > **Try it:** The project ships with `data/synthetic_failures.csv` (1,206 records). Upload it here to see the full pipeline in action.
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="No filename provided.")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".csv", ".json"]:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Only .csv and .json are accepted."
        )
    try:
        content = await file.read()
        df = analyzer.preprocessor.load_data(content)
        cleaned_df, audit, stats = analyzer.process_and_analyze_dataframe(df)

        global cached_stats
        cached_stats = stats

        records = cleaned_df.head(100).to_dict(orient="records")

        return {
            "filename": file.filename,
            "cleaning_audit": audit,
            "statistics": stats,
            "sample_results": records
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing '{file.filename}': {str(e)}")


@app.get(
    "/stats",
    tags=["Analytics"],
    summary="Get aggregate failure dataset statistics",
    response_description="Category distribution, severity breakdown, top interfaces, status codes, retry and latency metrics",
    responses={
        200: {
            "description": "Current dataset statistics",
            "content": {
                "application/json": {
                    "example": {
                        "total_failures": 1205,
                        "category_distribution": {
                            "Validation/Data": 262,
                            "Connectivity": 239,
                            "Authentication/Authorization": 216,
                            "Business error": 170,
                            "Timeout": 192,
                            "Application/System error": 98,
                            "Unknown": 28
                        },
                        "severity_distribution": {
                            "Critical": 289,
                            "High": 412,
                            "Medium": 380,
                            "Low": 124
                        },
                        "top_failing_interfaces": {
                            "Order_Create_Inbound": 112,
                            "Customer_Master_Sync": 108,
                            "Invoice_Post_Out": 98
                        },
                        "status_code_distribution": {
                            "400": 180,
                            "401": 160,
                            "422": 180,
                            "500": 98,
                            "502": 120,
                            "503": 119,
                            "504": 120
                        },
                        "retry_stats": {
                            "mean": 1.42,
                            "max": 5,
                            "rate_retried_pct": 62.3
                        },
                        "processing_time_stats_ms": {
                            "min": 55.0,
                            "mean": 12400.0,
                            "median": 1800.0,
                            "p95": 63000.0,
                            "max": 95000.0
                        }
                    }
                }
            }
        }
    }
)
def get_dataset_statistics():
    """
    ## Aggregate Dataset Statistics

    Returns pre-computed metrics across all failure records in the currently loaded dataset.

    Statistics refresh automatically when a new file is uploaded via `POST /analyze/file`.

    | Metric | Description |
    |---|---|
    | `category_distribution` | Count per failure category |
    | `severity_distribution` | Count per severity level (Critical/High/Medium/Low) |
    | `top_failing_interfaces` | Top 10 interfaces by failure volume |
    | `status_code_distribution` | HTTP/error code frequency |
    | `source_distribution` | Top 8 source systems |
    | `target_distribution` | Top 8 target systems |
    | `retry_stats` | Mean retries, max retries, % of failures retried |
    | `processing_time_stats_ms` | Min, mean, median, p95, max in milliseconds |
    """
    if not cached_stats:
        load_initial_stats()
    return cached_stats


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"], include_in_schema=False)
def render_dashboard(request: Request):
    """Renders the interactive web dashboard UI."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"stats": cached_stats}
    )
