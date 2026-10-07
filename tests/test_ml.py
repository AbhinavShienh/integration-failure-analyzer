"""
Unit tests for MLClassifier.
"""

import os
import pytest
import pandas as pd
from analyzer.classifier_ml import MLClassifier, DEFAULT_MODEL_PATH

def test_feature_text_construction():
    text = MLClassifier.build_feature_text(
        interface="Customer_Master_Sync",
        source="Salesforce",
        target="S4HANA",
        status_code=401,
        error_message="Unauthorized token invalid"
    )
    assert "STATUS_401" in text
    assert "IFACE_Customer_Master_Sync" in text
    assert "SRC_Salesforce" in text
    assert "TGT_S4HANA" in text
    assert "Unauthorized" in text

def test_ml_prediction_with_trained_model():
    ml = MLClassifier()
    assert ml.pipeline is not None, "Model should be loaded"

    # Test Auth prediction
    cat, conf = ml.predict_single(
        interface="Customer_Master_Sync",
        source="Salesforce_CRM",
        target="S4HANA",
        status_code=401,
        error_message="Unauthorized client: Bearer token expired"
    )
    assert cat == "Authentication/Authorization"
    assert conf > 0.50

    # Test Timeout prediction
    cat, conf = ml.predict_single(
        interface="Order_Create_Inbound",
        source="Shopify",
        target="S4HANA",
        status_code=504,
        error_message="Gateway Timeout: Target did not respond within 60000ms"
    )
    assert cat == "Timeout"
    assert conf > 0.50

def test_ml_batch_prediction():
    ml = MLClassifier()
    df = pd.DataFrame([
        {
            "interface": "Customer_Master_Sync",
            "source": "Salesforce",
            "target": "S4HANA",
            "status_code": 401,
            "error_message": "Unauthorized client token expired"
        },
        {
            "interface": "Invoice_Post_Out",
            "source": "S4HANA",
            "target": "CPI",
            "status_code": 502,
            "error_message": "Bad Gateway: Connection refused by target"
        }
    ])
    preds, confs = ml.predict_batch(df)
    assert len(preds) == 2
    assert preds[0] == "Authentication/Authorization"
    assert preds[1] == "Connectivity"
    assert confs[0] > 0.50
    assert confs[1] > 0.50
