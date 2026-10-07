"""
Synthetic Dataset Generator for Enterprise Integration Failures.
Generates realistic failure datasets across SAP S/4HANA, SAP CPI, Salesforce, Workday, etc.
Outputs both CSV and JSON formats, with realistic clean data and controlled edge cases for validation.
"""

import json
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Seed for reproducibility
random.seed(42)
np.random.seed(42)

INTERFACES = [
    {"name": "Customer_Master_Sync", "source": "Salesforce_CRM", "target": "S4HANA", "tier": "Tier-2"},
    {"name": "Order_Create_Inbound", "source": "Shopify_Storefront", "target": "S4HANA", "tier": "Tier-1"},
    {"name": "Invoice_Post_Out", "source": "S4HANA", "target": "SAP_CPI", "tier": "Tier-1"},
    {"name": "Payment_Status_Update", "source": "Payment_Stripe", "target": "S4HANA", "tier": "Tier-1"},
    {"name": "Inventory_Adjustment_Feed", "source": "WMS_Manhattan", "target": "S4HANA", "tier": "Tier-2"},
    {"name": "Employee_Onboarding_Event", "source": "Workday_HCM", "target": "ServiceNow", "tier": "Tier-3"},
    {"name": "Shipment_Confirmation_EDI", "source": "B2B_EDI_Partner", "target": "SAP_CPI", "tier": "Tier-2"},
    {"name": "Product_Catalog_Export", "source": "S4HANA", "target": "Salesforce_CRM", "tier": "Tier-3"},
    {"name": "Tax_Calculation_Call", "source": "SAP_CPI", "target": "TaxEngine_Vertex", "tier": "Tier-2"},
    {"name": "General_Ledger_Batch_Post", "source": "BillingEngine", "target": "S4HANA", "tier": "Tier-1"},
    {"name": "Vendor_Remittance_Advice", "source": "S4HANA", "target": "Banking_API", "tier": "Tier-2"},
    {"name": "Warehouse_Transfer_Order", "source": "S4HANA", "target": "WMS_Manhattan", "tier": "Tier-2"}
]

FAILURE_TEMPLATES = {
    "Authentication/Authorization": [
        (401, "Unauthorized: Bearer token expired or invalid JWT signature during OAuth handshake"),
        (401, "Unauthorized: Client credentials rejected by SAP Identity Authentication Service (IAS)"),
        (401, "HTTP 401 Unauthorized: Invalid API key provided in header x-api-key"),
        (401, "SAP RFC logon rejected: Technical communication user 'RFC_CPI_COMM' is locked"),
        (403, "Forbidden: Client certificate missing or not trusted in SAP CPI Keystore"),
        (403, "Forbidden: User lacks authorization for BAPI_SALESORDER_CREATEFROMDAT2 in S4HANA"),
        (403, "HTTP 403 Forbidden: Insufficient scopes for OAuth token on endpoint /api/v2/orders"),
        (401, "OAuth2 token refresh failed: invalid_grant - Refresh token revoked")
    ],
    "Connectivity": [
        (502, "Bad Gateway: Connection refused by target SAP S/4HANA host on port 8001"),
        (502, "Bad Gateway: SAP Cloud Connector subaccount tunnel 'hana-prd-s4' is offline"),
        (502, "Proxy Error: DNS lookup failed for internal host erp.corp.internal"),
        (503, "Service Unavailable: Target endpoint under maintenance window"),
        (503, "Service Unavailable: Backend connection pool exhausted (max 150 active connections)"),
        (503, "TCP connection reset by peer during TLS handshake with Vertex Tax Engine"),
        (502, "HTTP 502 Bad Gateway: Network socket prematurely closed by upstream server"),
        (503, "Service Unavailable: Circuit breaker open for downstream payment service")
    ],
    "Timeout": [
        (504, "Gateway Timeout: Upstream SAP S/4HANA took longer than 60000ms to respond to BAPI call"),
        (504, "Gateway Timeout: SAP CPI worker exceeded maximum route execution timeout (120s)"),
        (504, "Gateway Timeout: HTTP read timeout after 90000ms waiting for Salesforce bulk API response"),
        (408, "Request Timeout: Client connection dropped before request payload was fully received"),
        (408, "HTTP 408 Request Timeout: Socket read timed out after 45000ms waiting for WMS response"),
        (504, "Timeout: Target system did not respond within configured timeout of 30000ms"),
        (504, "Gateway Timeout: JDBC query execution timed out in database layer")
    ],
    "Validation/Data": [
        (400, "Bad Request: JSON schema validation error - missing mandatory field 'KUNNR' in customer payload"),
        (400, "Bad Request: Invalid date format in delivery_date '2026-31-02' - expected YYYY-MM-DD"),
        (400, "Bad Request: Request payload size 38MB exceeds maximum allowed message limit 10MB"),
        (422, "Unprocessable Entity: Currency code 'USDD' is not ISO-4217 compliant"),
        (422, "Unprocessable Entity: Postal code 'XYZ-999' invalid format for destination country 'DE'"),
        (400, "Bad Request: XML parse exception - mismatched closing tag </itemRecord> at line 48"),
        (422, "Validation Error: Quantity must be a positive integer greater than zero for line item 10"),
        (400, "Bad Request: Header Content-Type 'text/plain' not acceptable, expected 'application/json'")
    ],
    "Business error": [
        (409, "Conflict: Duplicate document error - Purchase Order 'PO-98231' already exists in S/4HANA"),
        (409, "Conflict: Concurrency version conflict updating Customer Master record 'CUST-10492'"),
        (422, "Business Rule Violation: Credit limit exceeded for customer 'ACME_CORP' (Limit: $50,000, Current Order: $68,000)"),
        (422, "Business Rule Violation: SAP Posting period 09/2026 is closed in company code 1000"),
        (422, "Business Rule Violation: Material 'MAT-8002' marked for deletion or blocked in plant 1010"),
        (422, "Business Error: Insufficient available warehouse stock in bin A-12 for SKU 'ELEC-902'"),
        (422, "Business Error: Employee effective date cannot be prior to hiring offer acceptance date"),
        (409, "Business Conflict: Invoice matching failed - PO line item amount mismatch greater than 2% tolerance")
    ],
    "Application/System error": [
        (500, "Internal Server Error: SAP ABAP runtime dump 'DYNPRO_NOT_FOUND' in function module /SAPAPO/BAPI"),
        (500, "Internal Server Error: OutOfMemoryError in Java mapping runtime in SAP Integration Suite"),
        (500, "Internal Server Error: SAP enqueue server lock table overflow (transaction SM12)"),
        (500, "Internal Server Error: IDoc status 51 - Application document not posted due to database deadlock"),
        (500, "Internal Server Error: NullPointerException in custom Groovy script step 'TransformOrder.groovy' line 42"),
        (500, "Internal Server Error: Database transaction rollback triggered by unhandled exception"),
        (500, "HTTP 500: System crash occurred during large batch file processing in middleware worker")
    ],
    "Unknown": [
        (599, "Unrecognized vendor response code 9999 from legacy gateway"),
        (999, "General anomaly detected: undefined status without protocol description"),
        (0, "Raw socket disconnect with unknown termination reason"),
        (499, "Client closed connection with unmapped upstream exception")
    ]
}

def generate_dataset(num_records=1200, include_dirty=True):
    records = []
    base_time = datetime(2026, 10, 1, 8, 0, 0)
    
    categories = list(FAILURE_TEMPLATES.keys())
    # Weights reflecting realistic enterprise incident frequencies
    cat_weights = [0.18, 0.20, 0.16, 0.22, 0.14, 0.08, 0.02]
    
    for i in range(num_records):
        # Pick category
        cat = random.choices(categories, weights=cat_weights, k=1)[0]
        status_code, template_msg = random.choice(FAILURE_TEMPLATES[cat])
        
        # Pick interface
        ifile = random.choice(INTERFACES)
        interface_name = ifile["name"]
        source = ifile["source"]
        target = ifile["target"]
        
        # Add random variations to error message to make it realistic
        variation_suffix = f" [Ref: MSG-{random.randint(10000, 99999)}]"
        error_msg = template_msg + variation_suffix
        
        # Timestamp
        time_offset = timedelta(
            days=random.randint(0, 6),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        timestamp = (base_time + time_offset).isoformat()
        
        # Processing time (ms) based on category
        if cat == "Timeout":
            proc_time = int(np.random.normal(65000, 15000))
            proc_time = max(30000, proc_time)
        elif cat == "Connectivity":
            proc_time = int(np.random.exponential(1200) + 150)
        elif cat == "Authentication/Authorization":
            proc_time = int(np.random.normal(350, 120))
            proc_time = max(50, proc_time)
        elif cat == "Validation/Data":
            proc_time = int(np.random.normal(450, 150))
            proc_time = max(60, proc_time)
        elif cat == "Business error":
            proc_time = int(np.random.normal(1800, 600))
            proc_time = max(200, proc_time)
        else:
            proc_time = int(np.random.normal(5000, 2500))
            proc_time = max(100, proc_time)
            
        # Retry count (higher for connectivity and timeout)
        if cat in ["Connectivity", "Timeout"]:
            retry_count = random.choices([0, 1, 2, 3, 4, 5], weights=[0.1, 0.2, 0.3, 0.25, 0.1, 0.05])[0]
        elif cat == "Business error":
            retry_count = random.choices([0, 1, 2], weights=[0.75, 0.2, 0.05])[0]
        elif cat == "Validation/Data":
            retry_count = random.choices([0, 1], weights=[0.9, 0.1])[0]
        else:
            retry_count = random.choices([0, 1, 2, 3], weights=[0.4, 0.3, 0.2, 0.1])[0]
            
        record = {
            "timestamp": timestamp,
            "interface": interface_name,
            "source": source,
            "target": target,
            "status_code": status_code,
            "error_message": error_msg,
            "processing_time": proc_time,
            "retry_count": retry_count,
            "true_category": cat  # Ground truth label for ML training
        }
        records.append(record)
        
    if include_dirty:
        # Add 30 intentionally dirty / edge-case records to test preprocessor validation
        dirty_records = [
            # Negative processing time
            {
                "timestamp": (base_time + timedelta(hours=1)).isoformat(),
                "interface": "Order_Create_Inbound",
                "source": "Shopify_Storefront",
                "target": "S4HANA",
                "status_code": 500,
                "error_message": "Internal Server Error: Database deadlock during order creation",
                "processing_time": -250,
                "retry_count": 2,
                "true_category": "Application/System error"
            },
            # Missing status code (None)
            {
                "timestamp": (base_time + timedelta(hours=2)).isoformat(),
                "interface": "Customer_Master_Sync",
                "source": "Salesforce_CRM",
                "target": "S4HANA",
                "status_code": None,
                "error_message": "Network reset connection lost mid-transfer",
                "processing_time": 1200,
                "retry_count": 1,
                "true_category": "Connectivity"
            },
            # Missing retry count (None)
            {
                "timestamp": (base_time + timedelta(hours=3)).isoformat(),
                "interface": "Invoice_Post_Out",
                "source": "S4HANA",
                "target": "SAP_CPI",
                "status_code": 401,
                "error_message": "Unauthorized client credentials invalid",
                "processing_time": 300,
                "retry_count": None,
                "true_category": "Authentication/Authorization"
            },
            # Excess whitespace in error message
            {
                "timestamp": (base_time + timedelta(hours=4)).isoformat(),
                "interface": "Tax_Calculation_Call ",
                "source": " SAP_CPI ",
                "target": "TaxEngine_Vertex",
                "status_code": 504,
                "error_message": "   Gateway Timeout: Read timeout after 60000ms   ",
                "processing_time": 60200,
                "retry_count": 3,
                "true_category": "Timeout"
            },
            # Null error message
            {
                "timestamp": (base_time + timedelta(hours=5)).isoformat(),
                "interface": "Payment_Status_Update",
                "source": "Payment_Stripe",
                "target": "S4HANA",
                "status_code": 503,
                "error_message": "",
                "processing_time": 500,
                "retry_count": 0,
                "true_category": "Connectivity"
            }
        ]
        # Duplicate records
        dirty_records.append(dirty_records[0].copy())
        records.extend(dirty_records)
        
    return records

if __name__ == "__main__":
    records = generate_dataset(num_records=1200, include_dirty=True)
    df = pd.DataFrame(records)
    
    # Save CSV
    csv_path = "data/synthetic_failures.csv"
    df.to_csv(csv_path, index=False)
    print(f"Generated {len(df)} records to {csv_path}")
    
    # Save JSON
    json_path = "data/synthetic_failures.json"
    with open(json_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Generated {len(records)} records to {json_path}")
