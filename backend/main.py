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
    print("AI Account Intelligence System starting up...")
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
        # Step 1: Company Identification
        yield "data: {\"step\": \"IDENTIFY\", \"status\": \"in_progress\", \"message\": \"Identifying company...\"}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.company_identifier import identify_company_from_name
        company_id = await identify_company_from_name(q)
        
        yield f"data: {json.dumps({'step': 'IDENTIFY', 'status': 'complete', 'message': f'Identified: {company_id.company_name}'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 2: Company Enrichment (Parallel agents)
        yield f"data: {json.dumps({'step': 'ENRICH', 'status': 'in_progress', 'message': 'Scraping website and enriching profile...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.company_enricher import enrich_company
        profile = await enrich_company(company_id.company_name, company_id.domain)
        
        industry_msg = profile.industry if profile.industry else "Unknown"
        yield f"data: {json.dumps({'step': 'ENRICH', 'status': 'complete', 'message': f'Profile enriched: {industry_msg}'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 3: Tech Stack Detection
        yield f"data: {json.dumps({'step': 'TECH', 'status': 'in_progress', 'message': 'Detecting technology stack...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.tech_detector import detect_tech_stack
        tech_stack = await detect_tech_stack(company_id.company_name, company_id.domain)
        
        tech_count = len(tech_stack.items) if tech_stack.items else 0
        yield f"data: {json.dumps({'step': 'TECH', 'status': 'complete', 'message': f'Found {tech_count} technologies'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 4: Business Signals
        yield f"data: {json.dumps({'step': 'SIGNALS', 'status': 'in_progress', 'message': 'Detecting business signals...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.business_signals import detect_business_signals
        signals = await detect_business_signals(company_id.company_name, company_id.domain)
        
        signal_count = len(signals.signals) if signals.signals else 0
        yield f"data: {json.dumps({'step': 'SIGNALS', 'status': 'complete', 'message': f'Found {signal_count} business signals'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 5: Leadership Discovery
        yield f"data: {json.dumps({'step': 'LEADERSHIP', 'status': 'in_progress', 'message': 'Discovering key decision makers...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.leadership import discover_leadership
        leadership = await discover_leadership(company_id.company_name, company_id.domain)
        
        leader_count = len(leadership.leaders) if leadership.leaders else 0
        yield f"data: {json.dumps({'step': 'LEADERSHIP', 'status': 'complete', 'message': f'Found {leader_count} leaders'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 6: ICP & Competitors
        yield f"data: {json.dumps({'step': 'ICP', 'status': 'in_progress', 'message': 'Analyzing ICP fit and competitors...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.competitor_detector import detect_competitors_and_icp
        icp_score = await detect_competitors_and_icp(profile)
        
        yield f"data: {json.dumps({'step': 'ICP', 'status': 'complete', 'message': f'ICP Score: {icp_score.score}/10 ({icp_score.fit_level})'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 7: Summary & Outreach
        yield f"data: {json.dumps({'step': 'FINALIZE', 'status': 'in_progress', 'message': 'Generating summary and outreach...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.summary_generator import generate_summary
        from backend.agents.outreach_composer import compose_outreach
        from backend.agents.persona_inferrer import infer_persona
        from backend.agents.intent_scorer import score_intent
        
        # Create dummy persona/intent for company analysis
        persona = await infer_persona([])
        intent = await score_intent(pages_visited=[], time_on_site_seconds=0, visits_this_week=1)
        
        summary_result = await generate_summary(profile, persona, intent, tech_stack, signals, leadership)
        outreach = await compose_outreach(profile, persona, intent, leadership)
        
        yield f"data: {json.dumps({'step': 'FINALIZE', 'status': 'complete', 'message': 'Analysis complete!'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Now get full result
        result = await analyze_company(CompanyInput(
            company_name=company_id.company_name,
            domain=company_id.domain
        ))
        save_result(result)
        
        yield f"data: {json.dumps({'step': 'DONE', 'status': 'complete', 'result': result.model_dump()})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Streaming Visitor Analysis ───────────────────────────────────────────────

@app.post("/api/analyze/visitor/stream")
async def analyze_visitor_stream_endpoint(visitor: VisitorSignal):
    """Streamed analysis progress for a visitor signal."""
    
    async def event_generator():
        # Step 1: Identify company from IP
        yield f"data: {json.dumps({'step': 'IDENTIFY', 'status': 'in_progress', 'message': 'Identifying company from IP...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.company_identifier import identify_company_from_ip
        company_id = await identify_company_from_ip(visitor.ip_address)
        
        yield f"data: {json.dumps({'step': 'IDENTIFY', 'status': 'complete', 'message': f'Identified: {company_id.company_name}'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 2: Analyze visitor behavior
        yield f"data: {json.dumps({'step': 'BEHAVIOR', 'status': 'in_progress', 'message': 'Analyzing visitor behavior...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.persona_inferrer import infer_persona
        from backend.agents.intent_scorer import score_intent
        
        persona = await infer_persona(visitor.pages_visited)
        intent = await score_intent(
            pages_visited=visitor.pages_visited,
            time_on_site_seconds=visitor.time_on_site_seconds,
            visits_this_week=visitor.visits_this_week,
            referral_source=visitor.referral_source or "",
            timestamps=visitor.timestamps,
        )
        
        yield f"data: {json.dumps({'step': 'BEHAVIOR', 'status': 'complete', 'message': f'Intent: {intent.score}/10 ({intent.stage})'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 3: Company Enrichment
        yield f"data: {json.dumps({'step': 'ENRICH', 'status': 'in_progress', 'message': 'Scraping website and enriching profile...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.company_enricher import enrich_company
        profile = await enrich_company(company_id.company_name, company_id.domain)
        
        industry_msg = profile.industry if profile.industry else "Unknown"
        yield f"data: {json.dumps({'step': 'ENRICH', 'status': 'complete', 'message': f'Profile enriched: {industry_msg}'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 4: Tech Stack
        yield f"data: {json.dumps({'step': 'TECH', 'status': 'in_progress', 'message': 'Detecting technology stack...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.tech_detector import detect_tech_stack
        tech_stack = await detect_tech_stack(company_id.company_name, company_id.domain)
        
        tech_count = len(tech_stack.items) if tech_stack.items else 0
        yield f"data: {json.dumps({'step': 'TECH', 'status': 'complete', 'message': f'Found {tech_count} technologies'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 5: Business Signals
        yield f"data: {json.dumps({'step': 'SIGNALS', 'status': 'in_progress', 'message': 'Detecting business signals...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.business_signals import detect_business_signals
        signals = await detect_business_signals(company_id.company_name, company_id.domain)
        
        signal_count = len(signals.signals) if signals.signals else 0
        yield f"data: {json.dumps({'step': 'SIGNALS', 'status': 'complete', 'message': f'Found {signal_count} signals'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 6: Leadership
        yield f"data: {json.dumps({'step': 'LEADERSHIP', 'status': 'in_progress', 'message': 'Discovering decision makers...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.leadership import discover_leadership
        leadership = await discover_leadership(company_id.company_name, company_id.domain)
        
        leader_count = len(leadership.leaders) if leadership.leaders else 0
        yield f"data: {json.dumps({'step': 'LEADERSHIP', 'status': 'complete', 'message': f'Found {leader_count} leaders'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Step 7: ICP & Summary
        yield f"data: {json.dumps({'step': 'FINALIZE', 'status': 'in_progress', 'message': 'ICP & Summary generation...'})}\n\n"
        await asyncio.sleep(0.3)
        
        from backend.agents.competitor_detector import detect_competitors_and_icp
        from backend.agents.summary_generator import generate_summary
        from backend.agents.outreach_composer import compose_outreach
        
        icp_score = await detect_competitors_and_icp(profile)
        summary_result = await generate_summary(profile, persona, intent, tech_stack, signals, leadership)
        outreach = await compose_outreach(profile, persona, intent, leadership)
        
        yield f"data: {json.dumps({'step': 'FINALIZE', 'status': 'complete', 'message': 'Analysis complete!'})}\n\n"
        await asyncio.sleep(0.2)
        
        # Get full result
        result = await analyze_visitor(visitor)
        save_result(result)
        
        yield f"data: {json.dumps({'step': 'DONE', 'status': 'complete', 'result': result.model_dump()})}\n\n"

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
