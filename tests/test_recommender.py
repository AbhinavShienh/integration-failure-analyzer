"""
Unit tests for RecommendationEngine.
"""

import pytest
from analyzer.recommender import RecommendationEngine

def test_recommendation_auth_401():
    rec = RecommendationEngine.generate_recommendation(
        category="Authentication/Authorization",
        status_code=401,
        error_message="Unauthorized client invalid token",
        source="S4HANA",
        target="CRM"
    )
    assert "OAuth" in rec or "token" in rec.lower()

def test_recommendation_timeout_504():
    rec = RecommendationEngine.generate_recommendation(
        category="Timeout",
        status_code=504,
        error_message="Gateway Timeout after 60000ms",
        source="Shopify",
        target="S4HANA"
    )
    assert "timeout" in rec.lower()
    assert "cpi" in rec.lower() or "target-system" in rec.lower()

def test_recommendation_lock_table_sm12():
    rec = RecommendationEngine.generate_recommendation(
        category="Application/System error",
        status_code=500,
        error_message="SAP enqueue server lock table overflow (SM12)"
    )
    assert "SM12" in rec
    assert "lock" in rec.lower()

def test_recommendation_kunnr_mandatory():
    rec = RecommendationEngine.generate_recommendation(
        category="Validation/Data",
        status_code=400,
        error_message="Missing mandatory field 'KUNNR' in payload"
    )
    assert "KUNNR" in rec or "mandatory" in rec.lower()
