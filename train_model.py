"""
Model Training & Evaluation Script.
Trains TF-IDF + Logistic Regression classifier on synthetic failure data,
evaluates performance, saves the model, and compares with rule-based classification.
"""

import os
import json
import pandas as pd
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

from analyzer.preprocessor import DataPreprocessor
from analyzer.classifier_ml import MLClassifier
from analyzer.classifier_rules import RuleBasedClassifier

def main():
    print("=" * 70)
    print(" 🚀 TRAINING INTEGRATION FAILURE CLASSIFIER")
    print("=" * 70)

    dataset_path = "data/synthetic_failures.csv"
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found. Run data/generate_dataset.py first.")
        return

    print(f"Loading dataset from {dataset_path}...")
    raw_df = DataPreprocessor.load_data(dataset_path)
    cleaned_df, audit = DataPreprocessor.clean_and_validate(raw_df)
    print(f"Data cleaned: {audit['cleaned_records']} records ready. Removed {audit['duplicates_removed']} duplicates.")

    # Train ML Classifier
    ml = MLClassifier()
    metrics = ml.train(cleaned_df, label_col="true_category", test_size=0.2, random_state=42)

    print("\n--- Model Training & Test Evaluation ---")
    print(f"Training Samples: {metrics['train_samples']}")
    print(f"Testing Samples:  {metrics['test_samples']}")
    print(f"Accuracy:         {metrics['accuracy'] * 100:.2f}%")
    print(f"Macro F1-Score:   {metrics['macro_f1'] * 100:.2f}%")
    print("\nPer-class Metrics:")
    for cls_name, vals in metrics["classification_report"].items():
        if isinstance(vals, dict):
            print(f"  {cls_name.ljust(30)}: Precision={vals['precision']:.2f}, Recall={vals['recall']:.2f}, F1={vals['f1-score']:.2f}")

    print(f"\nModel serialized successfully to: {ml.model_path}")

    # Comparative evaluation: Rule-Based vs ML vs Ground Truth
    print("\n" + "=" * 70)
    print(" 🔍 COMPARATIVE BENCHMARK: RULE-BASED VS ML VS GROUND TRUTH")
    print("=" * 70)

    rule_preds = []
    ml_preds = []
    ground_truth = []

    for _, row in cleaned_df.iterrows():
        gt = row["true_category"]
        ground_truth.append(gt)

        # Rule classifier
        rcat, _, _ = RuleBasedClassifier.classify(
            status_code=row["status_code"],
            error_message=row["error_message"],
            interface=row["interface"]
        )
        rule_preds.append(rcat)

        # ML classifier
        mcat, _ = ml.predict_single(
            interface=row["interface"],
            source=row["source"],
            target=row["target"],
            status_code=row["status_code"],
            error_message=row["error_message"]
        )
        ml_preds.append(mcat)

    rule_acc = accuracy_score(ground_truth, rule_preds)
    ml_acc = accuracy_score(ground_truth, ml_preds)
    agreement = sum(r == m for r, m in zip(rule_preds, ml_preds)) / len(ground_truth)

    print(f"Rule-Based Accuracy vs Ground Truth: {rule_acc * 100:.2f}%")
    print(f"ML Classifier Accuracy vs Ground Truth: {ml_acc * 100:.2f}%")
    print(f"Rule-Based & ML Model Agreement Rate: {agreement * 100:.2f}%")
    print("=" * 70)

if __name__ == "__main__":
    main()
