"""
Machine Learning Classifier for Integration Failure Analyzer.
Uses TF-IDF feature extraction combined with Logistic Regression (scikit-learn)
to classify enterprise integration failure logs with confidence estimation.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score

DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "failure_classifier.joblib")

class MLClassifier:
    """TF-IDF + Logistic Regression Failure Classifier."""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.pipeline: Optional[Pipeline] = None
        if os.path.exists(self.model_path):
            self.load()

    @staticmethod
    def build_feature_text(
        interface: str,
        source: str,
        target: str,
        status_code: Any,
        error_message: str
    ) -> str:
        """
        Combines textual metadata and status code token into an enriched feature text string.
        Example: 'STATUS_401 IFACE_Customer_Master_Sync SRC_Salesforce_CRM TGT_S4HANA Unauthorized client Bearer token expired'
        """
        status_token = f"STATUS_{status_code}" if status_code else "STATUS_UNKNOWN"
        iface_token = f"IFACE_{str(interface).strip()}"
        src_token = f"SRC_{str(source).strip()}"
        tgt_token = f"TGT_{str(target).strip()}"
        msg_token = str(error_message).strip()
        return f"{status_token} {iface_token} {src_token} {tgt_token} {msg_token}"

    def train(
        self,
        df: pd.DataFrame,
        label_col: str = "true_category",
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        Trains the TF-IDF + Logistic Regression pipeline on the given dataset.
        Saves the resulting artifact to self.model_path.
        """
        # Ensure feature text column exists
        texts = [
            self.build_feature_text(
                row.get("interface", ""),
                row.get("source", ""),
                row.get("target", ""),
                row.get("status_code", 0),
                row.get("error_message", "")
            )
            for _, row in df.iterrows()
        ]
        labels = df[label_col].values

        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=random_state, stratify=labels
        )

        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=2,
                sublinear_tf=True,
                stop_words="english"
            )),
            ("clf", LogisticRegression(
                C=2.0,
                max_iter=1000,
                class_weight="balanced",
                random_state=random_state
            ))
        ])

        pipeline.fit(X_train, y_train)
        self.pipeline = pipeline

        # Evaluate on test set
        y_pred = pipeline.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
        report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.pipeline, self.model_path)

        return {
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "classification_report": report_dict,
            "classes": list(pipeline.classes_)
        }

    def load(self):
        """Loads serialized model from disk."""
        if os.path.exists(self.model_path):
            self.pipeline = joblib.load(self.model_path)
        else:
            raise FileNotFoundError(f"Model file not found at {self.model_path}")

    def predict_single(
        self,
        interface: str,
        source: str,
        target: str,
        status_code: Any,
        error_message: str
    ) -> Tuple[str, float]:
        """
        Predicts category and probability confidence for a single failure instance.
        Returns:
            (predicted_category: str, confidence_score: float)
        """
        if self.pipeline is None:
            # Fallback if model not yet trained or loaded
            return "Unknown", 0.0

        feature_text = self.build_feature_text(interface, source, target, status_code, error_message)
        probas = self.pipeline.predict_proba([feature_text])[0]
        classes = self.pipeline.classes_
        top_idx = int(np.argmax(probas))
        category = str(classes[top_idx])
        confidence = float(probas[top_idx])

        return category, round(confidence, 3)

    def predict_batch(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Vectorized batch prediction.
        Returns:
            (predictions: np.ndarray, confidences: np.ndarray)
        """
        if self.pipeline is None:
            return np.array(["Unknown"] * len(df)), np.zeros(len(df))

        texts = [
            self.build_feature_text(
                row.get("interface", ""),
                row.get("source", ""),
                row.get("target", ""),
                row.get("status_code", 0),
                row.get("error_message", "")
            )
            for _, row in df.iterrows()
        ]
        probas = self.pipeline.predict_proba(texts)
        classes = self.pipeline.classes_
        top_indices = np.argmax(probas, axis=1)
        preds = classes[top_indices]
        confidences = probas[np.arange(len(df)), top_indices]

        return preds, np.round(confidences, 3)
