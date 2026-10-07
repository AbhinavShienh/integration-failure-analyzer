"""
Data Preprocessor for Integration Failure Analyzer.
Handles file ingestion (CSV/JSON), schema validation, cleaning, missing values, and descriptive statistics.
"""

import json
import re
from typing import Tuple, Dict, Any, Union, List
import pandas as pd
import numpy as np

class DataPreprocessor:
    """Preprocesses, cleans, and computes statistics for integration failure logs."""

    @staticmethod
    def load_data(file_source: Union[str, bytes, list, pd.DataFrame]) -> pd.DataFrame:
        """Loads data from a file path (CSV/JSON), bytes, raw list of dicts, or existing DataFrame."""
        if isinstance(file_source, pd.DataFrame):
            return file_source.copy()

        if isinstance(file_source, list):
            return pd.DataFrame(file_source)

        if isinstance(file_source, bytes):
            # Attempt to parse as JSON first, then CSV
            try:
                data = json.loads(file_source.decode("utf-8"))
                return pd.DataFrame(data)
            except Exception:
                import io
                return pd.read_csv(io.BytesIO(file_source))

        if isinstance(file_source, str):
            if file_source.endswith(".json"):
                with open(file_source, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return pd.DataFrame(data)
            elif file_source.endswith(".csv"):
                return pd.read_csv(file_source)
            else:
                # Try JSON string
                try:
                    data = json.loads(file_source)
                    return pd.DataFrame(data)
                except Exception:
                    # Fallback to reading CSV from path or string buffer
                    import io
                    return pd.read_csv(io.StringIO(file_source))

        raise ValueError(f"Unsupported data source type: {type(file_source)}")

    @staticmethod
    def clean_and_validate(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """
        Cleans and validates the dataset:
        - Drops exact duplicates
        - Normalizes whitespace
        - Fixes invalid/negative processing times
        - Fixes missing or invalid status codes
        - Defaults missing retries
        - Returns cleaned DataFrame and cleaning audit metrics.
        """
        df = df.copy()
        initial_len = len(df)
        audit = {
            "total_records": initial_len,
            "duplicates_removed": 0,
            "missing_status_codes_imputed": 0,
            "missing_messages_fixed": 0,
            "negative_processing_times_fixed": 0,
            "invalid_retries_fixed": 0
        }

        # Deduplication
        df.drop_duplicates(inplace=True)
        audit["duplicates_removed"] = initial_len - len(df)

        # Ensure required columns exist
        for col in ["interface", "source", "target", "status_code", "error_message", "processing_time", "retry_count"]:
            if col not in df.columns:
                df[col] = np.nan

        # Normalize string columns
        for str_col in ["interface", "source", "target", "error_message"]:
            df[str_col] = df[str_col].astype(str).str.strip()
            df[str_col] = df[str_col].replace({"nan": "", "None": "", "null": ""})

        # Fix empty error messages
        empty_msg_mask = (df["error_message"] == "") | (df["error_message"].isna())
        audit["missing_messages_fixed"] = int(empty_msg_mask.sum())
        df.loc[empty_msg_mask, "error_message"] = "Unspecified integration error occurred"

        # Fix status codes: attempt to parse integer, else extract from error message or set 0
        def fix_status_code(row):
            val = row["status_code"]
            if pd.notna(val) and str(val).strip() not in ["", "nan", "None"]:
                try:
                    return int(float(str(val).strip()))
                except (ValueError, TypeError):
                    pass
            # Try to extract HTTP status code from error message (e.g., 'HTTP 401', 'status: 504')
            msg = str(row["error_message"])
            match = re.search(r'\b(?:HTTP|status|code)?\s*([1-5]\d{2})\b', msg, re.IGNORECASE)
            if match:
                return int(match.group(1))
            return 0  # 0 represents unknown / unmapped

        old_status_na = df["status_code"].isna() | (df["status_code"].astype(str).str.strip().isin(["", "nan", "None"]))
        audit["missing_status_codes_imputed"] = int(old_status_na.sum())
        df["status_code"] = df.apply(fix_status_code, axis=1).astype(int)

        # Fix processing times: must be non-negative float
        def fix_processing_time(val):
            try:
                v = float(val)
                return max(0.0, v)
            except (ValueError, TypeError):
                return 0.0

        neg_proc_mask = df["processing_time"].apply(lambda x: pd.isna(x) or (isinstance(x, (int, float)) and x < 0))
        audit["negative_processing_times_fixed"] = int(neg_proc_mask.sum())
        df["processing_time"] = df["processing_time"].apply(fix_processing_time)

        # If all processing times are 0 or empty, median is 0; otherwise impute missing with median
        non_zero_median = df.loc[df["processing_time"] > 0, "processing_time"].median()
        if pd.isna(non_zero_median):
            non_zero_median = 500.0
        df.loc[df["processing_time"] == 0.0, "processing_time"] = non_zero_median

        # Fix retry count
        def fix_retry_count(val):
            try:
                v = int(float(val))
                return max(0, v)
            except (ValueError, TypeError):
                return 0

        invalid_retry_mask = df["retry_count"].apply(lambda x: pd.isna(x) or str(x).strip() in ["", "nan", "None"])
        audit["invalid_retries_fixed"] = int(invalid_retry_mask.sum())
        df["retry_count"] = df["retry_count"].apply(fix_retry_count).astype(int)

        # Clean timestamp
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            df["timestamp"] = df["timestamp"].fillna("2026-10-07T00:00:00Z")
        else:
            df["timestamp"] = "2026-10-07T00:00:00Z"

        audit["cleaned_records"] = len(df)
        return df, audit

    @staticmethod
    def generate_statistics(df: pd.DataFrame) -> Dict[str, Any]:
        """Generates statistical metrics across integration failure records."""
        total = len(df)
        if total == 0:
            return {
                "total_failures": 0,
                "top_failing_interfaces": {},
                "status_code_distribution": {},
                "source_distribution": {},
                "target_distribution": {},
                "retry_stats": {"mean": 0, "max": 0, "rate_retried_pct": 0},
                "processing_time_stats_ms": {"mean": 0, "median": 0, "p95": 0, "max": 0}
            }

        top_interfaces = df["interface"].value_counts().head(10).to_dict()
        status_dist = df["status_code"].value_counts().to_dict()
        status_dist_str = {str(k): int(v) for k, v in status_dist.items()}
        source_dist = df["source"].value_counts().head(8).to_dict()
        target_dist = df["target"].value_counts().head(8).to_dict()

        retried_count = int((df["retry_count"] > 0).sum())
        retry_stats = {
            "mean": float(round(df["retry_count"].mean(), 2)),
            "max": int(df["retry_count"].max()),
            "rate_retried_pct": float(round((retried_count / total) * 100, 2))
        }

        proc_stats = {
            "min": float(round(df["processing_time"].min(), 1)),
            "mean": float(round(df["processing_time"].mean(), 1)),
            "median": float(round(df["processing_time"].median(), 1)),
            "p95": float(round(df["processing_time"].quantile(0.95), 1)),
            "max": float(round(df["processing_time"].max(), 1))
        }

        stats = {
            "total_failures": total,
            "top_failing_interfaces": top_interfaces,
            "status_code_distribution": status_dist_str,
            "source_distribution": source_dist,
            "target_distribution": target_dist,
            "retry_stats": retry_stats,
            "processing_time_stats_ms": proc_stats
        }

        if "category" in df.columns:
            stats["category_distribution"] = df["category"].value_counts().to_dict()
        if "severity" in df.columns:
            stats["severity_distribution"] = df["severity"].value_counts().to_dict()

        return stats
