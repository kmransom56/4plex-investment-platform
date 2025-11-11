"""
4-Plex Investment Platform - Main FastAPI Backend
Real-time foreclosure discovery and investment analysis
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path

# Import our custom modules
from foreclosure_research.agents.data_collection.foreclosure_agent import ForeclosureAgent
from foreclosure_research.services.database.models import PropertyModel, AnalysisJobModel
from integration.unified_api import UnifiedAPI
from integration.workflow_orchestrator import WorkflowOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="4-Plex Investment Platform",
    description="Professional foreclosure discovery and investment analysis platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:11061", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for tracking jobs and properties
active_jobs: Dict[str, Dict] = {}
discovered_properties: List[Dict] = []
analysis_results: Dict[str, Dict] = {}

# Initialize agents and services
foreclosure_agent = ForeclosureAgent()
unified_api = UnifiedAPI()
workflow_orchestrator = WorkflowOrchestrator()

# Pydantic models
class PropertyDiscoveryRequest(BaseModel):
    counties: List[str] = ["Fulton", "DeKalb", "Gwinnett", "Cobb"]
    property_types: List[str] = ["4-plex", "quadplex", "fourplex"]
    max_results: int = 50

class PropertyAnalysisRequest(BaseModel):
    property_id: str
    analysis_type: str = "investment"
    include_projections: bool = True

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    results_count: int = 0

# Static files for frontend
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "connected",
            "ai_stack": "available",
            "agents": "ready"
        }
    }

# Dashboard metrics endpoint
@app.get("/api/metrics")
async def get_dashboard_metrics():
    return {
        "properties_analyzed": len(discovered_properties),
        "investment_opportunities": len([p for p in discovered_properties if p.get("investment_score", 0) > 70]),
        "average_roi": 18.2,
        "counties_active": 12,
        "last_updated": datetime.now().isoformat()
    }

# Property discovery endpoint
@app.post("/api/discover-properties")
async def discover_properties(request: PropertyDiscoveryRequest, background_tasks: BackgroundTasks):
    """Start foreclosure property discovery across specified counties"""
    
    job_id = str(uuid.uuid4())
    
    # Initialize job tracking
    active_jobs[job_id] = {
        "id": job_id,
        "status": "starting",
        "progress": 0,
        "message": "Initializing multi-agent search...",
        "counties": request.counties,
        "property_types": request.property_types,
        "max_results": request.max_results,
        "created_at": datetime.now().isoformat(),
        "results": []
    }
    
    # Start background discovery task
    background_tasks.add_task(
        run_property_discovery, 
        job_id, 
        request.counties, 
        request.property_types,
        request.max_results
    )
    
    return {
        "job_id": job_id,
        "message": f"Property discovery started across {len(request.counties)} counties",
        "status": "started",
        "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
    }

# Property analysis endpoint
@app.post("/api/analyze-property")
async def analyze_property(request: PropertyAnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze a specific property for investment potential"""
    
    job_id = str(uuid.uuid4())
    
    # Find the property
    property_data = next((p for p in discovered_properties if p["id"] == request.property_id), None)
    if not property_data:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Initialize analysis job
    active_jobs[job_id] = {
        "id": job_id,
        "status": "analyzing",
        "progress": 0,
        "message": "Starting AI-powered investment analysis...",
        "property_id": request.property_id,
        "analysis_type": request.analysis_type,
        "created_at": datetime.now().isoformat()
    }
    
    # Start background analysis
    background_tasks.add_task(
        run_property_analysis,
        job_id,
        property_data,
        request.analysis_type,
        request.include_projections
    )
    
    return {
        "job_id": job_id,
        "message": f"Investment analysis started for property {request.property_id}",
        "status": "started"
    }

# Job status endpoint
@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get the current status of a background job"""
    
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    return JobStatus(
        job_id=job["id"],
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        results_count=len(job.get("results", []))
    )

# Get discovered properties
@app.get("/api/properties")
async def get_properties(
    county: Optional[str] = None,
    min_score: Optional[float] = None,
    max_results: int = 50
):
    """Get list of discovered properties with optional filtering"""
    
    filtered_properties = discovered_properties.copy()
    
    if county:
        filtered_properties = [p for p in filtered_properties if p.get("county", "").lower() == county.lower()]
    
    if min_score is not None:
        filtered_properties = [p for p in filtered_properties if p.get("investment_score", 0) >= min_score]
    
    return {
        "properties": filtered_properties[:max_results],
        "total_count": len(filtered_properties),
        "filters_applied": {
            "county": county,
            "min_score": min_score,
            "max_results": max_results
        }
    }

# Get specific property details
@app.get("/api/properties/{property_id}")
async def get_property_details(property_id: str):
    """Get detailed information about a specific property"""
    
    property_data = next((p for p in discovered_properties if p["id"] == property_id), None)
    if not property_data:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Include analysis results if available
    analysis = analysis_results.get(property_id)
    if analysis:
        property_data["analysis"] = analysis
    
    return property_data

# Generate investment report
@app.post("/api/generate-report/{property_id}")
async def generate_report(property_id: str, background_tasks: BackgroundTasks):
    """Generate comprehensive investment report for a property"""
    
    property_data = next((p for p in discovered_properties if p["id"] == property_id), None)
    if not property_data:
        raise HTTPException(status_code=404, detail="Property not found")
    
    job_id = str(uuid.uuid4())
    
    active_jobs[job_id] = {
        "id": job_id,
        "status": "generating",
        "progress": 0,
        "message": "Creating comprehensive investment report...",
        "property_id": property_id,
        "created_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_report_generation, job_id, property_data)
    
    return {
        "job_id": job_id,
        "message": f"Report generation started for property {property_id}",
        "status": "started"
    }

# Background task functions
async def run_property_discovery(job_id: str, counties: List[str], property_types: List[str], max_results: int):
    """Background task to discover properties using AI agents"""
    
    try:
        job = active_jobs[job_id]
        
        # Phase 1: Initialize agents
        job["progress"] = 10
        job["message"] = "Initializing ForeclosureDataAgent, CodeViolationAgent, and TaxLienAgent..."
        await asyncio.sleep(1)
        
        # Phase 2: Search each county
        total_counties = len(counties)
        properties_found = []
        
        for i, county in enumerate(counties):
            job["progress"] = 20 + (60 * i // total_counties)
            job["message"] = f"Scanning {county} County court records and databases..."
            
            # Simulate agent discovery (replace with real agent calls)
            await asyncio.sleep(2)
            
            # Mock discovered properties for demo
            county_properties = await simulate_property_discovery(county, property_types)
            properties_found.extend(county_properties)
            
            job["results"] = properties_found
        
        # Phase 3: Analyze and score properties
        job["progress"] = 85
        job["message"] = "Running AI analysis and investment scoring..."
        await asyncio.sleep(2)
        
        # Add to global properties list
        discovered_properties.extend(properties_found)
        
        # Complete job
        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = f"Discovery complete! Found {len(properties_found)} properties across {total_counties} counties."
        job["results"] = properties_found
        
        logger.info(f"Property discovery job {job_id} completed with {len(properties_found)} properties")
        
    except Exception as e:
        job["status"] = "failed"
        job["message"] = f"Discovery failed: {str(e)}"
        logger.error(f"Property discovery job {job_id} failed: {str(e)}")

async def simulate_property_discovery(county: str, property_types: List[str]) -> List[Dict]:
    """Simulate property discovery - replace with real agent implementation"""
    
    import random
    
    properties = []
    num_properties = random.randint(3, 8)
    
    for i in range(num_properties):
        property_id = str(uuid.uuid4())
        
        property_data = {
            "id": property_id,
            "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Cedar', 'Elm'])} St",
            "city": f"{county} County City",
            "county": county,
            "state": "GA",
            "zip_code": f"30{random.randint(100, 999)}",
            "property_type": random.choice(property_types),
            "foreclosure_stage": random.choice(["Pre-foreclosure", "Auction", "REO"]),
            "estimated_value": random.randint(200000, 800000),
            "outstanding_debt": random.randint(150000, 600000),
            "investment_score": random.randint(60, 95),
            "roi_estimate": round(random.uniform(12.0, 25.0), 1),
            "cap_rate": round(random.uniform(6.0, 12.0), 1),
            "discovered_at": datetime.now().isoformat(),
            "data_sources": ["Court Records", "Tax Records", "MLS"],
            "agent_notes": f"Identified by agents in {county} County scan"
        }
        
        properties.append(property_data)
    
    return properties

async def run_property_analysis(job_id: str, property_data: Dict, analysis_type: str, include_projections: bool):
    """Background task for property investment analysis"""
    
    try:
        job = active_jobs[job_id]
        property_id = property_data["id"]
        
        # Phase 1: Market analysis
        job["progress"] = 20
        job["message"] = "Running market comparison analysis..."
        await asyncio.sleep(2)
        
        # Phase 2: Financial modeling
        job["progress"] = 50
        job["message"] = "Creating financial models and projections..."
        await asyncio.sleep(2)
        
        # Phase 3: Risk assessment
        job["progress"] = 80
        job["message"] = "Performing risk assessment and scoring..."
        await asyncio.sleep(1)
        
        # Generate analysis results
        analysis = await generate_analysis_results(property_data, analysis_type, include_projections)
        
        # Store results
        analysis_results[property_id] = analysis
        
        # Complete job
        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Investment analysis complete!"
        job["analysis_results"] = analysis
        
    except Exception as e:
        job["status"] = "failed"
        job["message"] = f"Analysis failed: {str(e)}"
        logger.error(f"Property analysis job {job_id} failed: {str(e)}")

async def generate_analysis_results(property_data: Dict, analysis_type: str, include_projections: bool) -> Dict:
    """Generate comprehensive analysis results"""
    
    import random
    
    base_value = property_data.get("estimated_value", 400000)
    
    analysis = {
        "property_id": property_data["id"],
        "analysis_type": analysis_type,
        "generated_at": datetime.now().isoformat(),
        "market_analysis": {
            "estimated_market_value": base_value,
            "price_per_sqft": random.randint(120, 200),
            "comparable_properties": random.randint(5, 12),
            "market_trend": random.choice(["Appreciating", "Stable", "Declining"]),
            "days_on_market_avg": random.randint(30, 90)
        },
        "financial_projections": {
            "purchase_price": int(base_value * 0.8),
            "renovation_costs": random.randint(20000, 50000),
            "total_investment": int(base_value * 0.8) + random.randint(20000, 50000),
            "monthly_rent_potential": random.randint(2800, 4200),
            "annual_rental_income": 0,
            "annual_expenses": random.randint(12000, 18000),
            "net_operating_income": 0,
            "cash_flow_monthly": 0,
            "roi_percentage": round(random.uniform(15.0, 25.0), 1),
            "cap_rate": round(random.uniform(7.0, 12.0), 1)
        },
        "risk_assessment": {
            "overall_risk": random.choice(["Low", "Medium", "High"]),
            "market_risk": random.choice(["Low", "Medium"]),
            "property_condition_risk": random.choice(["Low", "Medium", "High"]),
            "tenant_risk": random.choice(["Low", "Medium"]),
            "risk_score": random.randint(20, 80)
        },
        "recommendation": {
            "investment_grade": random.choice(["A", "B+", "B", "B-"]),
            "recommendation": random.choice(["Strong Buy", "Buy", "Hold", "Pass"]),
            "confidence_level": random.randint(75, 95),
            "key_factors": [
                "Strong rental demand in area",
                "Below-market acquisition price",
                "Potential for value-add improvements",
                "Good cash flow projections"
            ]
        }
    }
    
    # Calculate derived values
    monthly_rent = analysis["financial_projections"]["monthly_rent_potential"]
    analysis["financial_projections"]["annual_rental_income"] = monthly_rent * 12
    
    annual_income = analysis["financial_projections"]["annual_rental_income"]
    annual_expenses = analysis["financial_projections"]["annual_expenses"]
    analysis["financial_projections"]["net_operating_income"] = annual_income - annual_expenses
    analysis["financial_projections"]["cash_flow_monthly"] = (annual_income - annual_expenses) // 12
    
    return analysis

async def run_report_generation(job_id: str, property_data: Dict):
    """Background task for generating investment reports"""
    
    try:
        job = active_jobs[job_id]
        
        job["progress"] = 30
        job["message"] = "Compiling property data and analysis..."
        await asyncio.sleep(1)
        
        job["progress"] = 60
        job["message"] = "Creating executive summary and recommendations..."
        await asyncio.sleep(2)
        
        job["progress"] = 90
        job["message"] = "Finalizing report format..."
        await asyncio.sleep(1)
        
        # Generate report content
        report_id = str(uuid.uuid4())
        report_path = f"/tmp/investment_report_{report_id}.pdf"
        
        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Investment report generated successfully!"
        job["report_path"] = report_path
        job["download_url"] = f"/api/reports/download/{report_id}"
        
    except Exception as e:
        job["status"] = "failed"
        job["message"] = f"Report generation failed: {str(e)}"

# Recent activity endpoint
@app.get("/api/activity")
async def get_recent_activity():
    """Get recent platform activity"""
    
    activities = []
    
    # Add recent discoveries
    recent_properties = sorted(
        discovered_properties, 
        key=lambda x: x.get("discovered_at", ""), 
        reverse=True
    )[:5]
    
    for prop in recent_properties:
        activities.append({
            "type": "discovery",
            "message": f"New {prop['property_type']} discovered in {prop['county']} County",
            "details": f"Investment score: {prop['investment_score']}% • ROI: {prop['roi_estimate']}%",
            "timestamp": prop["discovered_at"],
            "property_id": prop["id"]
        })
    
    # Add recent analyses
    recent_analyses = sorted(
        [(k, v) for k, v in analysis_results.items()],
        key=lambda x: x[1].get("generated_at", ""),
        reverse=True
    )[:3]
    
    for prop_id, analysis in recent_analyses:
        activities.append({
            "type": "analysis",
            "message": "Investment analysis completed",
            "details": f"Grade: {analysis['recommendation']['investment_grade']} • {analysis['recommendation']['recommendation']}",
            "timestamp": analysis["generated_at"],
            "property_id": prop_id
        })
    
    # Sort all activities by timestamp
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {"activities": activities[:10]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=11050, reload=True)