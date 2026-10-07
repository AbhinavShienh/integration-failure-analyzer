"""
Unit tests for FastAPI endpoints.
"""

import io
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["ml_model_loaded"] is True

def test_analyze_endpoint_prompt_example():
    """Tests the exact example from the user specification."""
    payload = {
        "interface": "Customer_Master_Sync",
        "source": "S4HANA",
        "target": "CRM",
        "status_code": 401,
        "error_message": "Unauthorized client",
        "retry_count": 3
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Category, severity, confidence, recommendation
    assert "Authentication" in data["category"]
    assert data["severity"] in ["High", "Critical"]
    assert data["confidence"] >= 0.80
    assert "OAuth" in data["recommendation"] or "token" in data["recommendation"].lower()
    assert "reasoning" in data
    assert "details" in data

def test_analyze_batch_endpoint():
    payload = {
        "failures": [
            {
                "interface": "Order_Create_Inbound",
                "source": "Shopify",
                "target": "S4HANA",
                "status_code": 504,
                "error_message": "Gateway Timeout after 60000ms",
                "retry_count": 4,
                "processing_time": 62000
            },
            {
                "interface": "Customer_Master_Sync",
                "source": "Salesforce",
                "target": "S4HANA",
                "status_code": 400,
                "error_message": "Missing mandatory field 'KUNNR'",
                "retry_count": 0,
                "processing_time": 150
            }
        ]
    }
    response = client.post("/analyze/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert data["results"][0]["category"] == "Timeout"
    assert data["results"][1]["category"] == "Validation/Data"

def test_analyze_file_csv_upload():
    csv_content = (
        "interface,source,target,status_code,error_message,processing_time,retry_count\n"
        "Customer_Master_Sync,Salesforce,S4HANA,401,Unauthorized Bearer token expired,300,1\n"
        "Order_Create_Inbound,Shopify,S4HANA,500,Internal Server Error: DB crash,2500,3\n"
    )
    files = {"file": ("test_failures.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/analyze/file", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_failures.csv"
    assert data["cleaning_audit"]["total_records"] == 2
    assert len(data["sample_results"]) == 2

def test_get_stats():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_failures" in data
    assert "category_distribution" in data

def test_dashboard_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Integration Failure Analyzer" in response.text
