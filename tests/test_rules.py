"""
Unit tests for RuleBasedClassifier.
"""

import pytest
from analyzer.classifier_rules import (
    RuleBasedClassifier,
    CATEGORY_AUTH,
    CATEGORY_CONNECTIVITY,
    CATEGORY_TIMEOUT,
    CATEGORY_VALIDATION,
    CATEGORY_BUSINESS,
    CATEGORY_SYSTEM,
    CATEGORY_UNKNOWN
)

def test_rule_classification_authentication():
    cat, conf, _ = RuleBasedClassifier.classify(
        status_code=401,
        error_message="Unauthorized client: Bearer token expired"
    )
    assert cat == CATEGORY_AUTH
    assert conf >= 0.90

    cat2, conf2, _ = RuleBasedClassifier.classify(
        status_code=403,
        error_message="Forbidden: User lacks authorization for BAPI_SALESORDER"
    )
    assert cat2 == CATEGORY_AUTH
    assert conf2 >= 0.90

def test_rule_classification_timeout():
    cat, conf, _ = RuleBasedClassifier.classify(
        status_code=504,
        error_message="Gateway Timeout: Upstream S/4HANA took longer than 60000ms"
    )
    assert cat == CATEGORY_TIMEOUT
    assert conf >= 0.90

def test_rule_classification_connectivity():
    cat, conf, _ = RuleBasedClassifier.classify(
        status_code=502,
        error_message="Bad Gateway: Connection refused by target S/4HANA host on port 8001"
    )
    assert cat == CATEGORY_CONNECTIVITY
    assert conf >= 0.90

def test_rule_classification_validation():
    cat, conf, _ = RuleBasedClassifier.classify(
        status_code=400,
        error_message="Bad Request: Missing mandatory field 'KUNNR' in customer object"
    )
    assert cat == CATEGORY_VALIDATION
    assert conf >= 0.90

def test_rule_classification_business():
    cat, conf, _ = RuleBasedClassifier.classify(
        status_code=422,
        error_message="Business Rule Violation: Credit limit exceeded for customer 'ACME_CORP'"
    )
    assert cat == CATEGORY_BUSINESS
    assert conf >= 0.90

def test_rule_classification_system():
    cat, conf, _ = RuleBasedClassifier.classify(
        status_code=500,
        error_message="Internal Server Error: SAP ABAP runtime dump 'DYNPRO_NOT_FOUND'"
    )
    assert cat == CATEGORY_SYSTEM
    assert conf >= 0.90

def test_rule_classification_unknown():
    cat, conf, _ = RuleBasedClassifier.classify(
        status_code=999,
        error_message="Random unexpected string without recognizable patterns"
    )
    assert cat == CATEGORY_UNKNOWN
    assert conf <= 0.50
