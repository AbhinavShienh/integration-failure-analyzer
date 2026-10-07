"""
Root-Cause Recommendation Engine for Integration Failure Analyzer.
Generates targeted, actionable engineering and operational resolutions for enterprise integration failures.
"""

import re
from typing import Dict, Any

class RecommendationEngine:
    """Generates context-aware root cause resolutions based on status codes, category, and error context."""

    @classmethod
    def generate_recommendation(
        cls,
        category: str,
        status_code: int,
        error_message: str,
        source: str = "",
        target: str = ""
    ) -> str:
        """
        Generates targeted troubleshooting steps and resolution advice.
        """
        status = int(status_code) if status_code else 0
        msg_lower = (error_message or "").lower()

        # Specific keyword-level deep recommendations
        if "lock table overflow" in msg_lower or "sm12" in msg_lower:
            return "Check SAP transaction SM12 for orphaned enqueue locks; verify lock table sizing parameters (enque/table_size) in S/4HANA profile."

        if "idoc status 51" in msg_lower:
            return "Inspect transaction BD87 in S/4HANA to review IDoc status 51 error details; reprocess after resolving business document locking or master data dependencies."

        if "abap runtime dump" in msg_lower or "dynpro" in msg_lower or "st22" in msg_lower:
            return "Access SAP transaction ST22 to analyze the ABAP runtime dump and call stack; verify function module interface compatibility and transport status."

        if "cloud connector" in msg_lower or "tunnel" in msg_lower:
            return "Check SAP BTP Cloud Connector administration UI: verify subaccount tunnel status, resource mapping permissions, and local network route."

        if "posting period" in msg_lower:
            return "Check SAP financial posting period status via transaction OB52 or MMPV; open current posting period for the target company code."

        if "credit limit" in msg_lower:
            return "Customer credit limit exceeded in SAP S/4HANA (FSCM/FD32); request credit limit release or hold order for finance manager approval."

        if "kunnr" in msg_lower or "mandatory field" in msg_lower:
            return "Payload missing mandatory field (e.g. KUNNR/Customer Number); check source mapping in CPI or ensure upstream system populates required business partner keys."

        if "groovy" in msg_lower or "nullpointerexception" in msg_lower or "java mapping" in msg_lower:
            return "Inspect middleware script step: ensure null-safe navigation on optional XML/JSON nodes and review CPI message processing log in monitoring tile."

        # Category-level resolutions
        if category == "Authentication/Authorization":
            if status == 401 or "token" in msg_lower or "oauth" in msg_lower:
                return "HTTP 401 → Authentication failure → Check OAuth client credentials, token expiry, and ensure technical communication user is unlocked."
            elif status == 403 or "forbidden" in msg_lower or "certificate" in msg_lower:
                return "HTTP 403 → Authorization failure → Verify client certificate in CPI Keystore and check authorization roles/scopes assigned to the service principal."
            return "Authentication/Authorization error → Verify credentials, API keys, and access permissions between source and target systems."

        if category == "Timeout":
            if status == 504:
                return "HTTP 504 → Gateway Timeout → Check target-system availability, database query performance, and increase CPI route timeout configuration."
            elif status == 408:
                return "HTTP 408 → Request Timeout → Check network latency and client payload transmission speed; optimize large payload streaming."
            return "Timeout error → Check downstream system responsiveness, thread availability, and adjust middleware timeout thresholds."

        if category == "Connectivity":
            if status == 502:
                return "HTTP 502 → Bad Gateway → Verify target service DNS resolution, reverse proxy status, and verify target host:port is listening."
            elif status == 503:
                return "HTTP 503 → Service Unavailable → Target system is temporarily down or in a maintenance window; check health-check endpoint and circuit breaker."
            return "Connectivity error → Verify network routes, firewall ingress/egress rules, and backend connection pool utilization."

        if category == "Validation/Data":
            if status == 400:
                return "HTTP 400 → Bad Request → Validate request JSON/XML against OpenAPI/XSD schema specification and verify Content-Type header."
            elif status == 422:
                return "HTTP 422 → Unprocessable Entity → Correct invalid data formats, date patterns, or non-compliant ISO code values in the payload."
            return "Validation error → Inspect source payload schema, data type constraints, and required field mappings."

        if category == "Business error":
            if status == 409:
                return "HTTP 409 → Document Conflict → Duplicate business document detected; verify idempotency key or idempotency check in integration flow."
            return "Business logic violation → Validate business rules against target ERP master data state (pricing, inventory, status flags)."

        if category == "Application/System error":
            return "HTTP 500 → Application/System error → Inspect target application server logs (e.g., ST22 dumps, CPI trace) and review database deadlock monitors."

        # Fallback
        return "Unknown failure type → Review raw payload and correlate integration message GUID in middleware monitoring logs for root cause analysis."
