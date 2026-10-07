"""
FastAPI REST API and Web Dashboard for Integration Failure Analyzer.
Exposes endpoints for single failure analysis, batch analysis, file processing,
and statistical analytics, alongside a rich interactive dashboard.
"""

import os
import json
from typing import Dict, Any, List
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from analyzer.service import IntegrationFailureAnalyzer
from analyzer.schemas import (
    FailureInput,
    FailureAnalysisResult,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    DatasetStatistics
)

app = FastAPI(
    title="Integration Failure Analyzer API",
    description="Intelligent root-cause diagnosis, severity scoring, and classification for SAP & Enterprise Integrations.",
    version="1.0.0"
)

# Enable CORS for dashboard and third-party integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory configurations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Initialize Analyzer Service
analyzer = IntegrationFailureAnalyzer()

# Preload baseline statistics from synthetic dataset if available
DEFAULT_DATA_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "synthetic_failures.csv")
cached_stats: Dict[str, Any] = {}

def load_initial_stats():
    global cached_stats
    if os.path.exists(DEFAULT_DATA_PATH):
        try:
            df = analyzer.preprocessor.load_data(DEFAULT_DATA_PATH)
            _, _, stats = analyzer.process_and_analyze_dataframe(df)
            cached_stats = stats
        except Exception as e:
            print(f"Warning: Failed to load initial dataset stats: {e}")

load_initial_stats()

@app.get("/health", tags=["System"])
def health_check():
    """Healthcheck endpoint."""
    return {
        "status": "healthy",
        "service": "Integration Failure Analyzer",
        "ml_model_loaded": analyzer.ml_classifier.pipeline is not None
    }

@app.post("/analyze", response_model=FailureAnalysisResult, tags=["Analysis"])
def analyze_single_failure(failure: FailureInput):
    """
    Analyzes a single integration failure record.
    Returns failure category, severity score, confidence, and root-cause resolution.
    """
    try:
        result = analyzer.analyze_single(failure)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/analyze/batch", response_model=BatchAnalysisResponse, tags=["Analysis"])
def analyze_batch_failures(request: BatchAnalysisRequest):
    """
    Analyzes multiple integration failures in a single batch request.
    """
    try:
        return analyzer.analyze_batch(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@app.post("/analyze/file", tags=["File Ingestion"])
async def analyze_file(file: UploadFile = File(...)):
    """
    Upload a CSV or JSON failure log file.
    Validates, cleans data, handles missing values, classifies all failures,
    and returns cleaning audit logs, summary statistics, and classified failure records.
    """
    try:
        content = await file.read()
        df = analyzer.preprocessor.load_data(content)
        cleaned_df, audit, stats = analyzer.process_and_analyze_dataframe(df)
        
        # Update cached stats with latest uploaded data
        global cached_stats
        cached_stats = stats

        # Convert top 100 classified records for response payload
        records = cleaned_df.head(100).to_dict(orient="records")

        return {
            "filename": file.filename,
            "cleaning_audit": audit,
            "statistics": stats,
            "sample_results": records
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file '{file.filename}': {str(e)}")

@app.get("/stats", tags=["Analytics"])
def get_dataset_statistics():
    """
    Returns aggregate statistics across the failure dataset:
    category breakdown, severity distribution, top failing interfaces, and latency percentiles.
    """
    if not cached_stats:
        load_initial_stats()
    return cached_stats

@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
def render_dashboard(request: Request):
    """Renders the interactive web dashboard UI."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"stats": cached_stats}
    )
