"""FastAPI main application — serves API + frontend static files.

Architecture follows FastAPI Backend Builder patterns:
- Routes delegate to services
- Services own business logic
- Dependencies for shared resources
"""

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import asyncio

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models.schemas import (
    VisitorSignal,
    CompanyInput,
    BatchInput,
    AccountIntelligence,
)
from backend.agents.orchestrator import (
    analyze_visitor,
    analyze_company,
    analyze_batch,
)
from backend.services.history_service import (
    save_result,
    get_history,
    clear_history,
)
from backend.services.company_service import (
    CompanyService,
    BatchSizeError,
)


# ── App Setup ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 AI Account Intelligence System starting up...")
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title="AI Account Intelligence & Enrichment System",
    description="Convert raw visitor signals or company names into sales-ready account intelligence.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Service Instances ─────────────────────────────────────────────────────

company_service = CompanyService()


# ── Helpers ───────────────────────────────────────────────────────────────

def _load_visitors() -> list[dict]:
    """Load visitor data from JSON file."""
    data_dir = Path(__file__).parent / "data"
    visitors_path = data_dir / "visitors.json"
    if visitors_path.exists():
        with open(visitors_path, "r") as f:
            return json.load(f)
    return []


# ── API Routes ───────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "system": "AI Account Intelligence"}


@app.get("/api/visitors")
async def get_visitors():
    """Get the simulated visitor dataset."""
    return _load_visitors()


@app.post("/api/analyze/visitor", response_model=AccountIntelligence)
async def analyze_visitor_endpoint(visitor: VisitorSignal):
    """Analyze a single website visitor and generate account intelligence."""
    try:
        result = await analyze_visitor(visitor)
        save_result(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze/company", response_model=AccountIntelligence)
async def analyze_company_endpoint(company: CompanyInput):
    """Analyze a single company and generate account intelligence.
    
    Supports "Company Name,domain.com" format in company_name field.
    """
    try:
        # Delegate parsing to service
        normalized = company_service.parse_company_input(company)
        result = await analyze_company(normalized)
        save_result(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze/batch", response_model=list[AccountIntelligence])
async def analyze_batch_endpoint(batch: BatchInput):
    """Analyze multiple companies in batch (max 10)."""
    try:
        # Delegate validation to service
        company_service.validate_batch(batch.companies)
        normalized = company_service.normalize_batch(batch.companies)
        
        results = await analyze_batch(normalized)
        for r in results:
            save_result(r)
        return results
    except BatchSizeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── History Routes ────────────────────────────────────────────────────────

@app.get("/api/history")
async def get_history_endpoint(limit: int = 10):
    """Get analysis history."""
    return get_history(limit)


@app.post("/api/history/clear")
async def clear_history_endpoint():
    """Clear all analysis history."""
    count = clear_history()
    return {"status": "success", "cleared": count}


# ── Streaming Analysis ───────────────────────────────────────────────────

@app.get("/api/analyze/stream")
async def analyze_stream_endpoint(q: str):
    """Streamed analysis progress for a company name."""
    
    async def event_generator():
        yield f"data: {json.dumps({'status': 'IDENTIFYING', 'message': 'Resolving company identity...'})}\n\n"
        await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'status': 'ENRICHING', 'message': 'Scraping website and enriching profile...'})}\n\n"
        
        from backend.agents.company_identifier import identify_company_from_name
        company_id = await identify_company_from_name(q)
        
        yield f"data: {json.dumps({'status': 'RESEARCHING', 'message': f'Researching {company_id.company_name}...'})}\n\n"
        
        result = await analyze_company(CompanyInput(
            company_name=company_id.company_name,
            domain=company_id.domain
        ))
        save_result(result)
        
        yield f"data: {json.dumps({'status': 'DONE', 'result': result.model_dump()})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Static Files (Frontend) ─────────────────────────────────────────────

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "frontend",
    "dist"
)

if os.path.isdir(FRONTEND_DIR):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")),
        name="assets"
    )

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React frontend for any non-API route."""
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
