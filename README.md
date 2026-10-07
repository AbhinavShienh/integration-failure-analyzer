# Enterprise Integration Failure Analyzer ⚡

An enterprise-grade, Python-based root-cause diagnosis, classification, and severity scoring engine for middleware and cloud integrations across **SAP S/4HANA**, **SAP Integration Suite (CPI)**, **Salesforce**, **Workday**, and third-party APIs.

---

## 📑 Table of Contents
1. [Overview](#-overview)
2. [System Architecture](#-system-architecture)
3. [Synthetic Dataset](#-synthetic-dataset)
4. [Failure Classification Engine](#-failure-classification-engine)
5. [Severity Prediction Engine](#-severity-prediction-engine)
6. [Root-Cause Recommendation Engine](#-root-cause-recommendation-engine)
7. [AI / Machine Learning Component](#-ai--machine-learning-component)
8. [REST API Documentation](#-rest-api-documentation)
9. [Interactive Web Dashboard](#-interactive-web-dashboard)
10. [Setup & Quickstart Guide](#-setup--quickstart-guide)
11. [Running Tests](#-running-tests)

---

## 🔍 Overview

Modern enterprise architectures process millions of messages daily across ERPs (e.g., SAP S/4HANA), middleware brokers (e.g., SAP Cloud Integration / CPI), CRM, WMS, and payment gateways. When integration incidents occur, triage engineers face opaque error messages, cryptic HTTP codes, and cascading queue blockages.

The **Integration Failure Analyzer** automates triage by:
- **Ingesting & Cleaning** messy telemetry files (CSV/JSON), resolving nulls, duplicate events, and invalid timestamps.
- **Categorizing Failures** using both deterministic rule heuristics and a trained Machine Learning model (TF-IDF + Logistic Regression).
- **Assigning Severity** (🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low) with transparent, multi-factor scoring (business criticality, retry exhaustion, system crash vs format errors).
- **Generating Root-Cause Actions** with actionable, ERP-specific troubleshooting checklists (e.g., SAP SM12 enqueue locks, ST22 dumps, BD87 IDocs, OAuth token expiry, CPI route timeout limits).
- **Exposing a REST API & Dashboard** via FastAPI and a modern interactive UI.

---

## 🏛 System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["1. Ingestion Layer"]
        CSV[Synthetic CSV Log] --> DP[Data Preprocessor]
        JSON[Synthetic JSON Log] --> DP
        API_IN[FastAPI REST Request] --> DP
    end

    subgraph Preprocessing["2. Validation & Cleaning"]
        DP --> DEDUP[Deduplication Engine]
        DEDUP --> IMPUTE[Null Imputation & Latency Normalization]
        IMPUTE --> STATS[Descriptive Analytics Engine]
    end

    subgraph Classification["3. Classification Engines"]
        IMPUTE --> RULE[Rule-Based Classifier<br/>Deterministic Regex & Status Codes]
        IMPUTE --> ML[ML Classifier<br/>TF-IDF + Logistic Regression]
        RULE --> RECON[Reconciliation & Consensus Arbiter]
        ML --> RECON
    end

    subgraph Reasoning["4. Scoring & Prescriptions"]
        RECON --> SEV[Multi-Factor Severity Engine<br/>🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low]
        RECON --> REC[Root-Cause Recommendation Engine<br/>SAP S/4HANA / CPI Guidance]
    end

    subgraph Delivery["5. Delivery & Interfaces"]
        SEV --> API_OUT[FastAPI REST API<br/>/analyze, /analyze/batch, /stats]
        REC --> API_OUT
        API_OUT --> DASH[Interactive Web Dashboard<br/>KPIs, Chart.js, File Drag & Drop]
    end
```

---

## 📊 Synthetic Dataset

The project includes an enterprise synthetic dataset generator (`data/generate_dataset.py`) producing **1,200+ realistic failure events** modeled after real SAP, CPI, and third-party API incidents:

- **Sources & Targets**: `S4HANA`, `SAP_CPI`, `Salesforce_CRM`, `Workday_HCM`, `ServiceNow`, `B2B_EDI_Partner`, `Payment_Stripe`, `WMS_Manhattan`, `TaxEngine_Vertex`.
- **Interfaces**:
  - `Customer_Master_Sync` (Tier-2)
  - `Order_Create_Inbound` (Tier-1 Critical)
  - `Invoice_Post_Out` (Tier-1 Critical)
  - `Payment_Status_Update` (Tier-1 Critical)
  - `General_Ledger_Batch_Post` (Tier-1 Critical)
  - `Warehouse_Transfer_Order`, `Inventory_Adjustment_Feed`, `Tax_Calculation_Call`, etc.
- **Edge cases intentionally modeled**:
  - Missing HTTP status codes (extracted via regex from error text)
  - Negative processing latency values (`-250ms`)
  - Duplicate error telemetry rows
  - Null retry counts and trailing whitespace

---

## 🏷 Failure Classification Engine

Failures are classified into 7 standardized operational buckets:

| Category | Description | Primary Identifiers |
| :--- | :--- | :--- |
| **Authentication/Authorization** | OAuth expiry, invalid API keys, locked RFC communication users | HTTP 401, 403, `invalid_grant`, `RFC logon rejected`, `keystore` |
| **Connectivity** | Network partitions, offline Cloud Connector tunnels, DNS failures | HTTP 502, 503, `connection refused`, `tunnel offline`, `circuit breaker` |
| **Timeout** | Gateway timeouts, socket drops, slow upstream queries | HTTP 504, 408, `route execution timeout`, `socket read timed out` |
| **Validation/Data** | Missing mandatory fields (e.g. `KUNNR`), malformed JSON/XML, ISO schema mismatch | HTTP 400, 422, `missing mandatory field`, `XML parse exception` |
| **Business error** | Credit limit breaches, closed posting periods, duplicate POs | HTTP 409, 422, `credit limit exceeded`, `posting period closed`, `duplicate` |
| **Application/System error** | Memory exhaustion, deadlocks, SAP ABAP dumps, SM12 lock overflow | HTTP 500, `ST22 dump`, `lock table overflow`, `IDoc status 51`, `OutOfMemory` |
| **Unknown** | Unmapped legacy codes or unclassified custom payloads | Undefined status, raw disconnects |

---

## ⚖️ Severity Prediction Engine

Severity is computed dynamically using a transparent **100-point multi-factor model**:

$$
\text{Severity Score} = \text{Interface Criticality} + \text{Category Weight} + \text{Retry Penalty} + \text{Latency Penalty}
$$

### Scoring Weights:
1. **Business Criticality**:
   - **Tier-1 Flow** (`Order_Create_Inbound`, `Payment_Status_Update`, `Invoice_Post_Out`): **+35 pts**
   - **Tier-2 Flow** (`Customer_Master_Sync`, `Inventory_Adjustment_Feed`): **+20 pts**
   - **Tier-3 Flow** (`Employee_Onboarding_Event`): **+10 pts**
2. **Failure Category**:
   - Application/System Error: **+35 pts**
   - Connectivity / Timeout: **+25 pts**
   - Authentication/Authorization: **+20 pts**
   - Business Error: **+15 pts**
   - Validation/Data: **+10 pts**
3. **Retry Exhaustion**:
   - Retries $\ge 3$ (Dead-lettered, automated healing failed): **+25 pts**
   - Retries $= 2$: **+15 pts**
   - Retries $= 1$: **+5 pts**
   - Retries $= 0$: **0 pts**
4. **Latency Anomaly**:
   - Processing time $\ge 30,000\text{ ms}$: **+10 pts**
   - Processing time $\ge 10,000\text{ ms}$: **+5 pts**

### Tier Mapping:
- **🔴 Critical** ($\ge 75$ pts): Immediate pager duty alert. Example: Tier-1 Order flow failing with HTTP 500 crash and 3 retries exhausted.
- **🟠 High** ($55 - 74$ pts): High business impact requiring same-day triage.
- **🟡 Medium** ($35 - 54$ pts): Record-level discrepancy or transient issue.
- **🟢 Low** ($< 35$ pts): Non-critical schema error or initial attempt.

Every result returns an explainable **`reasoning`** string detailing each weighted factor.

---

## 💡 Root-Cause Recommendation Engine

Provides precise, actionable engineering checklists:
- **HTTP 401**: Check OAuth client credentials, token expiry, and verify technical communication user (`RFC_CPI_COMM`) in SAP IAS.
- **HTTP 504**: Verify target-system responsiveness, database query execution times, and increase timeout parameters in SAP CPI HTTP adapter.
- **HTTP 502**: Inspect SAP Cloud Connector subaccount tunnel status (`hana-prd-s4`) and check firewall ingress rules.
- **SM12 Lock Overflow**: Access SAP transaction `SM12` to release orphaned enqueue locks; review `enque/table_size` sizing profile parameter.
- **IDoc Status 51**: Run transaction `BD87` in S/4HANA to review error status; check for concurrent master data locking.
- **Missing KUNNR**: Check CPI mapping step or upstream Salesforce trigger to ensure mandatory customer identifier is populated.

---

## 🤖 AI / Machine Learning Component

- **Feature Engineering**: Synthesizes structured fields into an information-dense text representation:
  `STATUS_401 IFACE_Customer_Master_Sync SRC_Salesforce_CRM TGT_S4HANA Unauthorized client Bearer token expired`
- **Vectorization**: `TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)`
- **Model**: `LogisticRegression(class_weight='balanced', C=2.0, max_iter=1000)`
- **Inference**: Computes calibrated class probabilities via `predict_proba()` to output a true **Confidence Score (0.0 to 1.0)**.
- **Benchmark Results**:
  - **ML Accuracy on Holdout Test Set**: **100.0%**
  - **Macro F1-Score**: **1.00**
  - **Rule-Based Accuracy**: **99.92%**
  - **Ensemble Agreement Rate**: **99.92%**

---

## 🚀 REST API Documentation

### 1. Single Failure Analysis
**Endpoint**: `POST /analyze`

#### Sample Request:
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "Customer_Master_Sync",
    "source": "S4HANA",
    "target": "CRM",
    "status_code": 401,
    "error_message": "Unauthorized client",
    "retry_count": 3,
    "processing_time": 320
  }'
```

#### Sample Response:
```json
{
  "category": "Authentication/Authorization",
  "severity": "High",
  "severity_badge": "🟠 High",
  "confidence": 0.98,
  "recommendation": "HTTP 401 → Authentication failure → Check OAuth client credentials, token expiry, and ensure technical communication user is unlocked.",
  "reasoning": "Severity score is 65/100 (High). Key factors: Interface 'Customer_Master_Sync' is Tier-2 core operational; Authentication failure blocks subsequent automated API calls; Retries exhausted (3 attempts); automatic recovery failed.",
  "details": {
    "interface": "Customer_Master_Sync",
    "source": "S4HANA",
    "target": "CRM",
    "status_code": 401,
    "retry_count": 3,
    "processing_time_ms": 320.0,
    "severity_score": 65.0,
    "comparison": {
      "rule_category": "Authentication/Authorization",
      "rule_reason": "Matched keyword '\\b(?:unauthori[sz]ed|unauthenticated|forbidden|access\\s+denied)\\b' and HTTP 401",
      "rule_confidence": 0.98,
      "ml_category": "Authentication/Authorization",
      "ml_confidence": 0.978,
      "agreement": true
    }
  }
}
```

---

### 2. Batch Analysis
**Endpoint**: `POST /analyze/batch`

#### Sample Request:
```bash
curl -X POST "http://localhost:8000/analyze/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "failures": [
      {
        "interface": "Order_Create_Inbound",
        "source": "Shopify",
        "target": "S4HANA",
        "status_code": 504,
        "error_message": "Gateway Timeout after 60000ms",
        "retry_count": 3
      },
      {
        "interface": "Customer_Master_Sync",
        "source": "Salesforce",
        "target": "S4HANA",
        "status_code": 400,
        "error_message": "Missing mandatory field KUNNR",
        "retry_count": 0
      }
    ]
  }'
```

---

### 3. File Ingestion & Quality Audit
**Endpoint**: `POST /analyze/file`
Uploads a `.csv` or `.json` file, cleans anomalies, imputes null values, and returns full classification and cleaning audit.

```bash
curl -X POST "http://localhost:8000/analyze/file" \
  -F "file=@data/synthetic_failures.csv"
```

---

### 4. Dataset Statistics
**Endpoint**: `GET /stats`
Returns aggregated failure counts, severity distribution, top failing interfaces, and processing latency percentiles.

---

## 🖥 Interactive Web Dashboard

When running the application, navigate to **`http://localhost:8000/`** to access the web dashboard:
- **KPI Ribbon**: Real-time counters for Total Failures, Critical Incidents, High Incidents, Latency, and Retry Exhaustion.
- **Interactive Single Failure Diagnoser**: One-click presets (e.g. *401 OAuth Expiry*, *504 CPI Timeout*, *500 SM12 Lock Table*) with live diagnosis and recommendation render.
- **Visual Analytics**: Interactive Chart.js graphs for Category Breakdown, Severity Distributions, and Top Failing Interfaces.
- **Drag & Drop File Upload**: Upload CSV/JSON logs, inspect data quality metrics, and search/filter classified failures in a responsive table.
- **Interactive Swagger Documentation**: Live API testbed at **`http://localhost:8000/docs`**.

---

## 🛠 Setup & Quickstart Guide

### 1. Clone & Setup Environment
```bash
git clone <repository_url>
cd integration_failure_analyzer

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate Synthetic Dataset & Train ML Model
```bash
# Generate 1,200+ synthetic failures
python data/generate_dataset.py

# Train and evaluate TF-IDF + Logistic Regression model
python train_model.py
```

### 3. Launch the Server & Dashboard
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser.

---

## 🧪 Running Tests

The test suite includes **26 comprehensive unit tests** testing data preprocessing, rule classification, ML inference, multi-factor severity scoring, root-cause recommendations, and FastAPI endpoints:

```bash
pytest -v
```

---

## 📦 Project Structure

```plaintext
integration_failure_analyzer/
├── README.md                      # Comprehensive documentation
├── requirements.txt               # Dependencies
├── pytest.ini                     # Pytest configuration
├── train_model.py                 # ML training & benchmark script
├── data/
│   ├── generate_dataset.py        # Synthetic dataset generator
│   ├── synthetic_failures.csv     # Generated CSV failures
│   └── synthetic_failures.json    # Generated JSON failures
├── analyzer/
│   ├── __init__.py                # Package exports
│   ├── schemas.py                 # Pydantic input/output models
│   ├── preprocessor.py            # Data validation, cleaning & stats
│   ├── classifier_rules.py        # Rule-based regex & status classifier
│   ├── classifier_ml.py           # TF-IDF + Logistic Regression classifier
│   ├── severity_engine.py         # 100-point explainable severity engine
│   ├── recommender.py             # Context-aware resolution checklists
│   ├── service.py                 # Unified service orchestrator
│   └── models/
│       └── failure_classifier.joblib # Serialized ML model
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application & endpoints
│   ├── templates/
│   │   └── index.html             # Interactive Web Dashboard UI
│   └── static/
│       ├── style.css              # Dashboard styling
│       └── app.js                 # Dashboard frontend logic & charts
└── tests/
    ├── __init__.py
    ├── test_api.py                # FastAPI endpoint tests
    ├── test_ml.py                 # ML model & pipeline tests
    ├── test_preprocessor.py       # Data cleaning & statistics tests
    ├── test_recommender.py        # Root-cause recommendation tests
    ├── test_rules.py              # Rule classification tests
    └── test_severity.py           # Multi-factor severity scoring tests
```
