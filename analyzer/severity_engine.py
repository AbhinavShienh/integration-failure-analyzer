"""
Severity Prediction Engine for Integration Failure Analyzer.
Assigns severity levels (Critical, High, Medium, Low) using transparent,
explainable multi-factor scoring based on business criticality, failure category,
retry exhaustion, and processing latency.
"""

from typing import Dict, Any, Tuple

TIER_1_INTERFACES = {
    "order_create_inbound", "payment_status_update", "invoice_post_out",
    "general_ledger_batch_post", "billing_engine", "payment_gateway"
}

TIER_2_INTERFACES = {
    "customer_master_sync", "inventory_adjustment_feed", "shipment_confirmation_edi",
    "tax_calculation_call", "warehouse_transfer_order", "vendor_remittance_advice"
}

CATEGORY_WEIGHTS = {
    "Application/System error": 35,
    "Connectivity": 25,
    "Timeout": 25,
    "Authentication/Authorization": 20,
    "Business error": 15,
    "Validation/Data": 10,
    "Unknown": 10
}

class SeverityEngine:
    """Predicts severity and generates explainable reasoning for integration incidents."""

    @classmethod
    def evaluate(
        cls,
        category: str,
        interface: str,
        status_code: int,
        retry_count: int,
        processing_time: float
    ) -> Tuple[str, str, float, str]:
        """
        Evaluates failure severity.
        Returns:
            (severity: str, badge: str, score: float, reasoning: str)
        """
        score = 0.0
        reasons = []

        iface_norm = str(interface or "").strip().lower()

        # 1. Business Criticality of Interface
        if any(t1 in iface_norm for t1 in TIER_1_INTERFACES):
            score += 35
            reasons.append(f"Interface '{interface}' is Tier-1 mission-critical (revenue/financial impact)")
        elif any(t2 in iface_norm for t2 in TIER_2_INTERFACES):
            score += 20
            reasons.append(f"Interface '{interface}' is Tier-2 core operational")
        else:
            score += 10
            reasons.append(f"Interface '{interface}' is standard background integration")

        # 2. Failure Category Impact
        cat_weight = CATEGORY_WEIGHTS.get(category, 10)
        score += cat_weight
        if category == "Application/System error":
            reasons.append("Application/System error indicates backend crash, deadlock, or resource exhaustion")
        elif category in ["Connectivity", "Timeout"]:
            reasons.append(f"{category} blocks pipeline queue and causes upstream backpressure")
        elif category == "Authentication/Authorization":
            reasons.append("Authentication failure blocks subsequent automated API calls")
        elif category == "Business error":
            reasons.append("Business rule conflict affects specific record processing")
        elif category == "Validation/Data":
            reasons.append("Data validation error isolated to incoming request payload")

        # 3. Retry Exhaustion
        retries = max(0, int(retry_count or 0))
        if retries >= 3:
            score += 25
            reasons.append(f"Retries exhausted ({retries} attempts); automatic recovery failed")
        elif retries == 2:
            score += 15
            reasons.append(f"Repeated failure ({retries} attempts)")
        elif retries == 1:
            score += 5
            reasons.append("First retry attempt failed")
        else:
            reasons.append("Initial failure (0 retries); automated retry may still succeed")

        # 4. Processing Time Anomaly
        proc_time = float(processing_time or 0.0)
        if proc_time >= 30000:
            score += 10
            reasons.append(f"Extreme processing latency ({proc_time:,.0f}ms) indicates worker starvation")
        elif proc_time >= 10000:
            score += 5
            reasons.append(f"High processing latency ({proc_time:,.0f}ms)")

        # Map numerical score to Severity Level
        if score >= 75:
            severity = "Critical"
            badge = "🔴 Critical"
        elif score >= 55:
            severity = "High"
            badge = "🟠 High"
        elif score >= 35:
            severity = "Medium"
            badge = "🟡 Medium"
        else:
            severity = "Low"
            badge = "🟢 Low"

        explanation = f"Severity score is {score:.0f}/100 ({severity}). Key factors: " + "; ".join(reasons) + "."
        return severity, badge, score, explanation
