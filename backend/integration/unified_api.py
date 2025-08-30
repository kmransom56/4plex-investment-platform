"""
Unified API for Integrated Property Discovery and Valuation System
Provides single endpoints for the combined foreclosure research and valuation workflow
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from uuid import uuid4

from .unified_models import (
    UnifiedProperty, IntegratedAnalysis, PropertySource, 
    ProcessingStatus, PropertyType, ForeclosureStatus
)
from .workflow_orchestrator import WorkflowOrchestrator
from .data_sync import DataSynchronizer
from config.settings import Settings

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Unified Property Discovery & Valuation API",
    description="Integrated API for 4-plex foreclosure research and AI valuation",
    version="1.0.0",
    docs_url="/api/unified/docs",
    redoc_url="/api/unified/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
settings = Settings()
orchestrator = WorkflowOrchestrator(settings)
data_sync = DataSynchronizer(settings)


# Dependencies
def get_orchestrator() -> WorkflowOrchestrator:
    return orchestrator


def get_data_sync() -> DataSynchronizer:
    return data_sync


# Health Check
@app.get("/api/unified/health")
async def health_check():
    """System health check"""
    try:
        # Check foreclosure system
        foreclosure_health = await orchestrator._check_foreclosure_system_health()
        
        # Check valuation system  
        valuation_health = await orchestrator._check_valuation_system_health()
        
        # Check database connectivity
        db_health = await data_sync.check_database_health()
        
        overall_status = all([foreclosure_health, valuation_health, db_health])
        
        return {
            "status": "healthy" if overall_status else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "systems": {
                "foreclosure_research": "healthy" if foreclosure_health else "unhealthy",
                "valuation_engine": "healthy" if valuation_health else "unhealthy", 
                "database": "healthy" if db_health else "unhealthy"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Property Discovery Endpoints
@app.post("/api/unified/discovery/start")
async def start_property_discovery(
    background_tasks: BackgroundTasks,
    counties: Optional[List[str]] = Query(default=['Fulton', 'DeKalb', 'Clayton', 'Cobb', 'Atlanta']),
    orchestrator: WorkflowOrchestrator = Depends(get_orchestrator)
):
    """Start automated property discovery across Georgia counties"""
    try:
        job_id = str(uuid4())
        
        # Start discovery process in background
        background_tasks.add_task(
            orchestrator.run_discovery_workflow,
            job_id=job_id,
            counties=counties
        )
        
        return {
            "job_id": job_id,
            "status": "started",
            "counties": counties,
            "started_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start discovery: {str(e)}")


@app.get("/api/unified/discovery/{job_id}/status")
async def get_discovery_status(
    job_id: str,
    orchestrator: WorkflowOrchestrator = Depends(get_orchestrator)
):
    """Get discovery job status"""
    try:
        status = await orchestrator.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.get("/api/unified/discovery/results")
async def get_discovery_results(
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    county: Optional[str] = Query(default=None),
    status: Optional[ProcessingStatus] = Query(default=None),
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Get discovered properties with filtering"""
    try:
        filters = {}
        if county:
            filters['county'] = county
        if status:
            filters['discovery_status'] = status
            
        properties = await data_sync.get_properties(
            limit=limit,
            offset=offset,
            filters=filters
        )
        
        return {
            "properties": properties,
            "count": len(properties),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


# Property Management Endpoints
@app.get("/api/unified/properties")
async def list_properties(
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    source: Optional[PropertySource] = Query(default=None),
    property_type: Optional[PropertyType] = Query(default=None),
    county: Optional[str] = Query(default=None),
    min_investment_score: Optional[float] = Query(default=None, ge=0, le=100),
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """List properties with filtering and pagination"""
    try:
        filters = {}
        if source:
            filters['source'] = source
        if property_type:
            filters['property_type'] = property_type
        if county:
            filters['county'] = county
        if min_investment_score is not None:
            filters['min_investment_score'] = min_investment_score
            
        properties = await data_sync.get_properties(
            limit=limit,
            offset=offset,
            filters=filters
        )
        
        return {
            "properties": [prop.dict() for prop in properties],
            "count": len(properties),
            "pagination": {
                "offset": offset,
                "limit": limit,
                "has_more": len(properties) == limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list properties: {str(e)}")


@app.get("/api/unified/properties/{property_id}")
async def get_property(
    property_id: str,
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Get detailed property information"""
    try:
        property_data = await data_sync.get_property_by_id(property_id)
        if not property_data:
            raise HTTPException(status_code=404, detail="Property not found")
            
        return property_data.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get property: {str(e)}")


@app.post("/api/unified/properties/{property_id}/analyze")
async def trigger_property_analysis(
    property_id: str,
    background_tasks: BackgroundTasks,
    priority: str = Query(default="normal", regex="^(low|normal|high|urgent)$"),
    orchestrator: WorkflowOrchestrator = Depends(get_orchestrator)
):
    """Trigger comprehensive property analysis"""
    try:
        # Get property data
        property_data = await data_sync.get_property_by_id(property_id)
        if not property_data:
            raise HTTPException(status_code=404, detail="Property not found")
        
        analysis_job_id = str(uuid4())
        
        # Start analysis in background
        background_tasks.add_task(
            orchestrator.run_property_analysis,
            property_data=property_data.dict(),
            job_id=analysis_job_id,
            priority=priority
        )
        
        return {
            "analysis_job_id": analysis_job_id,
            "property_id": property_id,
            "status": "queued",
            "priority": priority,
            "started_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")


@app.post("/api/unified/properties/{property_id}/enrich")
async def enrich_property_data(
    property_id: str,
    background_tasks: BackgroundTasks,
    sources: List[str] = Query(default=["propertyradar", "realestate_api", "attom"]),
    orchestrator: WorkflowOrchestrator = Depends(get_orchestrator)
):
    """Enrich property data from external sources"""
    try:
        property_data = await data_sync.get_property_by_id(property_id)
        if not property_data:
            raise HTTPException(status_code=404, detail="Property not found")
        
        enrichment_job_id = str(uuid4())
        
        background_tasks.add_task(
            orchestrator.run_property_enrichment,
            property_data=property_data.dict(),
            job_id=enrichment_job_id,
            sources=sources
        )
        
        return {
            "enrichment_job_id": enrichment_job_id,
            "property_id": property_id,
            "sources": sources,
            "status": "queued",
            "started_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start enrichment: {str(e)}")


# Analysis Endpoints
@app.get("/api/unified/analysis/queue")
async def get_analysis_queue(
    status: Optional[str] = Query(default=None),
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Get analysis job queue status"""
    try:
        queue_status = await data_sync.get_analysis_queue(status=status)
        return queue_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue: {str(e)}")


@app.get("/api/unified/analysis/{job_id}/status")
async def get_analysis_status(
    job_id: str,
    orchestrator: WorkflowOrchestrator = Depends(get_orchestrator)
):
    """Get analysis job status"""
    try:
        status = await orchestrator.get_analysis_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.get("/api/unified/analysis/{job_id}/results")
async def get_analysis_results(
    job_id: str,
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Get analysis results"""
    try:
        results = await data_sync.get_analysis_results(job_id)
        if not results:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return results.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


# Investment Opportunities
@app.get("/api/unified/opportunities")
async def get_investment_opportunities(
    min_score: float = Query(default=70.0, ge=0, le=100),
    max_results: int = Query(default=25, le=100),
    county: Optional[str] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Get high-scoring investment opportunities"""
    try:
        filters = {
            'min_investment_score': min_score,
            'discovery_status': ProcessingStatus.ANALYZED
        }
        
        if county:
            filters['county'] = county
        if max_price:
            filters['max_price'] = max_price
            
        opportunities = await data_sync.get_investment_opportunities(
            filters=filters,
            limit=max_results
        )
        
        return {
            "opportunities": [opp.dict() for opp in opportunities],
            "count": len(opportunities),
            "min_score_threshold": min_score,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get opportunities: {str(e)}")


# Batch Operations
@app.post("/api/unified/batch/analyze")
async def batch_analyze_properties(
    property_ids: List[str],
    background_tasks: BackgroundTasks,
    priority: str = Query(default="normal"),
    orchestrator: WorkflowOrchestrator = Depends(get_orchestrator)
):
    """Analyze multiple properties in batch"""
    try:
        if len(property_ids) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 properties per batch")
        
        batch_job_id = str(uuid4())
        
        background_tasks.add_task(
            orchestrator.run_batch_analysis,
            property_ids=property_ids,
            batch_job_id=batch_job_id,
            priority=priority
        )
        
        return {
            "batch_job_id": batch_job_id,
            "property_count": len(property_ids),
            "priority": priority,
            "status": "queued",
            "started_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start batch analysis: {str(e)}")


# System Integration
@app.post("/api/unified/integration/sync")
async def sync_data_sources(
    background_tasks: BackgroundTasks,
    sources: List[str] = Query(default=["foreclosure_system", "valuation_system"]),
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Synchronize data between systems"""
    try:
        sync_job_id = str(uuid4())
        
        background_tasks.add_task(
            data_sync.sync_all_sources,
            job_id=sync_job_id,
            sources=sources
        )
        
        return {
            "sync_job_id": sync_job_id,
            "sources": sources,
            "status": "started",
            "started_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")


@app.get("/api/unified/integration/metrics")
async def get_integration_metrics(
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Get integration system metrics"""
    try:
        metrics = await data_sync.get_system_metrics()
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


# Dashboard Endpoints
@app.get("/api/unified/dashboard/summary")
async def get_dashboard_summary(
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Get dashboard summary statistics"""
    try:
        summary = await data_sync.get_dashboard_summary()
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@app.get("/api/unified/dashboard/activity")
async def get_recent_activity(
    hours: int = Query(default=24, le=168),  # Max 1 week
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Get recent system activity"""
    try:
        activity = await data_sync.get_recent_activity(hours=hours)
        return activity
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activity: {str(e)}")


# Export Endpoints
@app.get("/api/unified/export/properties")
async def export_properties(
    format: str = Query(default="json", regex="^(json|csv|excel)$"),
    filters: Optional[str] = Query(default=None),
    data_sync: DataSynchronizer = Depends(get_data_sync)
):
    """Export properties in various formats"""
    try:
        # Parse filters if provided
        filter_dict = {}
        if filters:
            import json
            filter_dict = json.loads(filters)
            
        export_data = await data_sync.export_properties(format=format, filters=filter_dict)
        
        if format == "json":
            return JSONResponse(content=export_data)
        else:
            # Return file download for CSV/Excel
            from fastapi.responses import StreamingResponse
            import io
            
            if format == "csv":
                output = io.StringIO()
                output.write(export_data)
                output.seek(0)
                return StreamingResponse(
                    io.BytesIO(output.getvalue().encode()), 
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=properties.csv"}
                )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")


# Error Handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "detail": str(exc.detail)}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "Please try again later"}
    )


# Add workflow orchestrator methods to handle the new endpoints
async def WorkflowOrchestrator.run_discovery_workflow(self, job_id: str, counties: List[str]):
    """Run discovery workflow for specified counties"""
    # Implementation would trigger the foreclosure agents
    pass

async def WorkflowOrchestrator.run_property_analysis(self, property_data: dict, job_id: str, priority: str):
    """Run comprehensive property analysis"""
    return await self.process_discovered_property(property_data)

async def WorkflowOrchestrator.run_property_enrichment(self, property_data: dict, job_id: str, sources: List[str]):
    """Run property data enrichment"""
    property = UnifiedProperty(**property_data)
    return await self._enrich_property_data(property)

async def WorkflowOrchestrator.run_batch_analysis(self, property_ids: List[str], batch_job_id: str, priority: str):
    """Run batch analysis on multiple properties"""
    # Implementation would process each property in the batch
    pass

async def WorkflowOrchestrator._check_foreclosure_system_health(self) -> bool:
    """Check foreclosure research system health"""
    try:
        response = await self.client.get(f"{self.foreclosure_api_url}/health")
        return response.status_code == 200
    except:
        return False

async def WorkflowOrchestrator._check_valuation_system_health(self) -> bool:
    """Check valuation system health"""  
    try:
        response = await self.client.get(f"{self.valuation_api_url}/api/health")
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=11060)