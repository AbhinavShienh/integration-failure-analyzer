"""
FastAPI REST API for Integration Failure Analyzer.
"""

import os
from typing import Dict, Any
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Body
from fastapi.responses import HTMLResponse
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

# ─────────────────────────── App Init ────────────────────────────────
app = FastAPI(
    title="Integration Failure Analyzer API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

analyzer = IntegrationFailureAnalyzer()

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


# ─────────────────────────── Endpoints ───────────────────────────────

@app.get("/health")
def health_check():
    """
    Returns service liveness status and whether the ML classification model is loaded.
    """
    return {
        "status": "healthy",
        "service": "Integration Failure Analyzer",
        "ml_model_loaded": analyzer.ml_classifier.pipeline is not None
    }


@app.post("/analyze", response_model=FailureAnalysisResult)
def analyze_single_failure(failure: FailureInput = Body(...)):
    """
    Analyze a single integration failure record and return a complete diagnosis.
    """
    try:
        result = analyzer.analyze_single(failure)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze/batch", response_model=BatchAnalysisResponse)
def analyze_batch_failures(request: BatchAnalysisRequest):
    """
    Analyze multiple integration failures in one request.
    """
    try:
        return analyzer.analyze_batch(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@app.post("/analyze/file")
async def analyze_file(file: UploadFile = File(...)):
    """
    Upload a .csv or .json failure log file. The engine will validate, clean,
    and deduplicate the dataset, then classify every record.
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="No filename provided.")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".csv", ".json"]:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Only .csv and .json are accepted."
        )
    try:
        content = await file.read()
        df = analyzer.preprocessor.load_data(content)
        cleaned_df, audit, stats = analyzer.process_and_analyze_dataframe(df)

        global cached_stats
        cached_stats = stats

        records = cleaned_df.head(100).to_dict(orient="records")

        return {
            "filename": file.filename,
            "cleaning_audit": audit,
            "statistics": stats,
            "sample_results": records
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing '{file.filename}': {str(e)}")


@app.get("/stats")
def get_dataset_statistics():
    """
    Returns pre-computed metrics across all failure records in the currently loaded dataset.
    """
    if not cached_stats:
        load_initial_stats()
    return cached_stats


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def render_dashboard(request: Request):
    """
    Renders the interactive web dashboard UI.
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"stats": cached_stats}
    )
