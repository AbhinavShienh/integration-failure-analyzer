"""
Unit tests for SeverityEngine.
"""

import pytest
from analyzer.severity_engine import SeverityEngine

def test_critical_severity():
    # Tier-1 interface + System Error + retries exhausted >= 3
    sev, badge, score, reasoning = SeverityEngine.evaluate(
        category="Application/System error",
        interface="Order_Create_Inbound",
        status_code=500,
        retry_count=3,
        processing_time=1200.0
    )
    assert sev == "Critical"
    assert "🔴" in badge
    assert score >= 75
    assert "Tier-1 mission-critical" in reasoning
    assert "Retries exhausted" in reasoning

def test_high_severity():
    # Tier-1 interface + Auth error + retries 3
    sev, badge, score, reasoning = SeverityEngine.evaluate(
        category="Authentication/Authorization",
        interface="Order_Create_Inbound",
        status_code=401,
        retry_count=2,
        processing_time=300.0
    )
    assert sev in ["High", "Critical"]
    assert score >= 55

def test_medium_severity():
    # Tier-2 interface + Validation error + 1 retry
    sev, badge, score, reasoning = SeverityEngine.evaluate(
        category="Validation/Data",
        interface="Customer_Master_Sync",
        status_code=400,
        retry_count=1,
        processing_time=200.0
    )
    assert sev in ["Medium", "Low"]
    assert "Customer_Master_Sync" in reasoning

def test_low_severity():
    # Tier-3 background interface + Validation error + 0 retries
    sev, badge, score, reasoning = SeverityEngine.evaluate(
        category="Validation/Data",
        interface="Employee_Onboarding_Event",
        status_code=400,
        retry_count=0,
        processing_time=150.0
    )
    assert sev == "Low"
    assert "🟢" in badge
    assert score < 35
