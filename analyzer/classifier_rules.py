"""
Rule-Based Failure Classifier for Enterprise Integrations.
Categorizes errors using deterministic status code mappings, keyword heuristics,
and regex pattern matching specifically tuned for SAP S/4HANA, SAP CPI, and standard APIs.
"""

import re
from typing import Dict, Any, Tuple

# Classification categories
CATEGORY_AUTH = "Authentication/Authorization"
CATEGORY_CONNECTIVITY = "Connectivity"
CATEGORY_TIMEOUT = "Timeout"
CATEGORY_VALIDATION = "Validation/Data"
CATEGORY_BUSINESS = "Business error"
CATEGORY_SYSTEM = "Application/System error"
CATEGORY_UNKNOWN = "Unknown"

# Pattern definitions
PATTERNS = {
    CATEGORY_AUTH: [
        r"\b(?:unauthori[sz]ed|unauthenticated|forbidden|access\s+denied)\b",
        r"\b(?:oauth|jwt|bearer\s+token|invalid\s+grant|refresh\s+token)\b",
        r"\b(?:client\s+credentials|identity\s+authentication|ias)\b",
        r"\b(?:keystore|client\s+certificate|truststore)\b",
        r"\b(?:rfc\s+logon\s+rejected|communication\s+user.*locked)\b",
        r"\b(?:insufficient\s+scopes|api\s+key|lacks\s+authorization)\b"
    ],
    CATEGORY_TIMEOUT: [
        r"\b(?:gateway\s+timeout|request\s+timeout|socket\s+timeout|read\s+timeout)\b",
        r"\b(?:timed?\s*out|timeout\s+exceeded|transaction\s+timeout)\b",
        r"\b(?:did\s+not\s+respond\s+within|route\s+execution\s+timeout)\b"
    ],
    CATEGORY_CONNECTIVITY: [
        r"\b(?:bad\s+gateway|service\s+unavailable|connection\s+refused)\b",
        r"\b(?:cloud\s+connector.*offline|subaccount\s+tunnel.*offline)\b",
        r"\b(?:dns\s+lookup\s+failed|host\s+unreachable|cannot\s+resolve\s+host)\b",
        r"\b(?:circuit\s+breaker\s+open|connection\s+pool\s+exhausted)\b",
        r"\b(?:tcp\s+connection\s+reset|socket\s+prematurely\s+closed|network\s+socket)\b",
        r"\b(?:maintenance\s+window|proxy\s+error)\b"
    ],
    CATEGORY_VALIDATION: [
        r"\b(?:schema\s+validation|missing\s+mandatory|mandatory\s+field)\b",
        r"\b(?:bad\s+request|unprocessable\s+entity|invalid\s+format|invalid\s+date)\b",
        r"\b(?:xml\s+parse\s+exception|json\s+parse|json\s+schema)\b",
        r"\b(?:payload\s+size.*exceeds|content-type.*not\s+acceptable)\b",
        r"\b(?:not\s+iso-\d+|invalid\s+postal\s+code|quantity\s+must\s+be)\b"
    ],
    CATEGORY_BUSINESS: [
        r"\b(?:business\s+rule\s+violation|business\s+conflict|business\s+error)\b",
        r"\b(?:credit\s+limit\s+exceeded|posting\s+period.*closed)\b",
        r"\b(?:duplicate\s+document|already\s+exists|concurrency\s+version\s+conflict)\b",
        r"\b(?:marked\s+for\s+deletion|insufficient\s+.*stock|available\s+warehouse\s+stock)\b",
        r"\b(?:invoice\s+matching\s+failed|tolerance\s+exceeded)\b",
        r"\b(?:effective\s+date\s+cannot\s+be\s+prior)\b"
    ],
    CATEGORY_SYSTEM: [
        r"\b(?:internal\s+server\s+error|runtime\s+dump|dynpro_not_found)\b",
        r"\b(?:outofmemoryerror|java\s+mapping\s+runtime|nullpointerexception)\b",
        r"\b(?:lock\s+table\s+overflow|sm12|enqueue\s+server)\b",
        r"\b(?:idoc\s+status\s+51|database\s+deadlock|transaction\s+rollback)\b",
        r"\b(?:system\s+crash|unhandled\s+exception|abap\s+dump)\b"
    ]
}

class RuleBasedClassifier:
    """Classifies integration failures based on deterministic status codes and text heuristics."""

    @classmethod
    def classify(cls, status_code: int, error_message: str, interface: str = "") -> Tuple[str, float, str]:
        """
        Classifies an integration failure.
        Returns:
            (category: str, confidence: float, matched_rule: str)
        """
        status = int(status_code) if status_code else 0
        msg = (error_message or "").lower()
        iface = (interface or "").lower()
        combined_text = f"{msg} {iface}"

        # 1. Match message regex against known categories
        for cat, pattern_list in PATTERNS.items():
            for pat in pattern_list:
                if re.search(pat, combined_text, re.IGNORECASE):
                    # Check status code alignment for high confidence
                    if cat == CATEGORY_AUTH and status in [401, 403]:
                        return cat, 0.98, f"Matched keyword '{pat}' and HTTP {status}"
                    if cat == CATEGORY_TIMEOUT and status in [408, 504]:
                        return cat, 0.98, f"Matched timeout keyword '{pat}' and HTTP {status}"
                    if cat == CATEGORY_CONNECTIVITY and status in [502, 503]:
                        return cat, 0.98, f"Matched connectivity keyword '{pat}' and HTTP {status}"
                    if cat == CATEGORY_VALIDATION and status in [400, 422]:
                        return cat, 0.98, f"Matched data validation keyword '{pat}' and HTTP {status}"
                    if cat == CATEGORY_BUSINESS and status in [409, 422]:
                        return cat, 0.98, f"Matched business error keyword '{pat}' and HTTP {status}"
                    if cat == CATEGORY_SYSTEM and status in [500]:
                        return cat, 0.98, f"Matched system error keyword '{pat}' and HTTP {status}"
                    # Strong message match without direct status alignment
                    return cat, 0.88, f"Matched keyword pattern '{pat}' in error message"

        # 2. Strict status code fallback if no specific message keyword matched
        if status in [401, 403]:
            return CATEGORY_AUTH, 0.85, f"Categorized by HTTP {status} (Unauthorized/Forbidden)"
        if status in [408, 504]:
            return CATEGORY_TIMEOUT, 0.85, f"Categorized by HTTP {status} (Request/Gateway Timeout)"
        if status in [502, 503]:
            return CATEGORY_CONNECTIVITY, 0.85, f"Categorized by HTTP {status} (Bad Gateway/Service Unavailable)"
        if status == 400:
            return CATEGORY_VALIDATION, 0.80, f"Categorized by HTTP {status} (Bad Request / Schema validation)"
        if status == 409:
            return CATEGORY_BUSINESS, 0.80, f"Categorized by HTTP {status} (Conflict / Business Duplicate)"
        if status == 422:
            return CATEGORY_VALIDATION, 0.75, f"Categorized by HTTP {status} (Unprocessable Entity)"
        if status == 500:
            return CATEGORY_SYSTEM, 0.80, f"Categorized by HTTP {status} (Internal Server Error)"

        # 3. Default to Unknown
        return CATEGORY_UNKNOWN, 0.40, "No matching error code or keyword pattern identified"
