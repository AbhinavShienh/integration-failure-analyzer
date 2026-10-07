"""
Unit tests for DataPreprocessor.
"""

import pandas as pd
import pytest
from analyzer.preprocessor import DataPreprocessor

def test_clean_and_validate_handles_dirty_data():
    raw_data = [
        # Normal record
        {
            "interface": "Order_Create_Inbound",
            "source": "Shopify",
            "target": "S4HANA",
            "status_code": 500,
            "error_message": "Internal error occurred",
            "processing_time": 1200.0,
            "retry_count": 1
        },
        # Duplicate record
        {
            "interface": "Order_Create_Inbound",
            "source": "Shopify",
            "target": "S4HANA",
            "status_code": 500,
            "error_message": "Internal error occurred",
            "processing_time": 1200.0,
            "retry_count": 1
        },
        # Negative processing time and missing status code
        {
            "interface": "Customer_Master_Sync",
            "source": "Salesforce",
            "target": "S4HANA",
            "status_code": None,
            "error_message": "HTTP 401 Unauthorized token expired",
            "processing_time": -300.0,
            "retry_count": None
        },
        # Empty error message
        {
            "interface": "Invoice_Post_Out",
            "source": "S4HANA",
            "target": "CPI",
            "status_code": "504",
            "error_message": "",
            "processing_time": 62000.0,
            "retry_count": "3"
        }
    ]
    df = pd.DataFrame(raw_data)
    cleaned_df, audit = DataPreprocessor.clean_and_validate(df)

    # Verify deduplication
    assert audit["duplicates_removed"] == 1
    assert len(cleaned_df) == 3

    # Verify negative processing time fixed
    assert (cleaned_df["processing_time"] >= 0).all()

    # Verify missing status code extracted from message "HTTP 401"
    row_auth = cleaned_df[cleaned_df["interface"] == "Customer_Master_Sync"].iloc[0]
    assert row_auth["status_code"] == 401
    assert row_auth["retry_count"] == 0

    # Verify string status code parsed
    row_inv = cleaned_df[cleaned_df["interface"] == "Invoice_Post_Out"].iloc[0]
    assert row_inv["status_code"] == 504
    assert row_inv["retry_count"] == 3
    assert row_inv["error_message"] != ""

def test_generate_statistics():
    data = [
        {"interface": "IF_A", "source": "S1", "target": "T1", "status_code": 401, "error_message": "Auth err", "processing_time": 100.0, "retry_count": 0, "category": "Authentication/Authorization", "severity": "High"},
        {"interface": "IF_A", "source": "S1", "target": "T1", "status_code": 504, "error_message": "Timeout err", "processing_time": 500.0, "retry_count": 2, "category": "Timeout", "severity": "Critical"},
        {"interface": "IF_B", "source": "S2", "target": "T2", "status_code": 500, "error_message": "System err", "processing_time": 300.0, "retry_count": 1, "category": "Application/System error", "severity": "Critical"}
    ]
    df = pd.DataFrame(data)
    stats = DataPreprocessor.generate_statistics(df)

    assert stats["total_failures"] == 3
    assert stats["top_failing_interfaces"]["IF_A"] == 2
    assert stats["retry_stats"]["max"] == 2
    assert stats["retry_stats"]["mean"] == 1.0
    assert stats["processing_time_stats_ms"]["min"] == 100.0
    assert stats["processing_time_stats_ms"]["max"] == 500.0
    assert stats["category_distribution"]["Timeout"] == 1
    assert stats["severity_distribution"]["Critical"] == 2
