"""
Data Synchronizer for Integrated Property System
Handles data synchronization between foreclosure research and valuation systems
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from services.database.connection import get_db_session
from .unified_models import (
    UnifiedPropertyDB, IntegratedAnalysisDB, WorkflowJob,
    UnifiedProperty, IntegratedAnalysis, ProcessingStatus
)
from config.settings import Settings

logger = logging.getLogger(__name__)


class DataSynchronizer:
    """Manages data synchronization between foreclosure and valuation systems"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.foreclosure_api_url = getattr(settings, 'FORECLOSURE_API_URL', 'http://localhost:11050')
        self.valuation_api_url = getattr(settings, 'VALUATION_API_URL', 'http://localhost:3000')
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def check_database_health(self) -> bool:
        """Check database connectivity and health"""
        try:
            with get_db_session() as db:
                db.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def get_properties(self, limit: int = 50, offset: int = 0, 
                           filters: Optional[Dict[str, Any]] = None) -> List[UnifiedProperty]:
        """Get properties with filtering and pagination"""
        try:
            with get_db_session() as db:
                query = db.query(UnifiedPropertyDB)
                
                # Apply filters
                if filters:
                    if 'county' in filters:
                        query = query.filter(UnifiedPropertyDB.county == filters['county'])
                    if 'source' in filters:
                        query = query.filter(UnifiedPropertyDB.source == filters['source'])
                    if 'property_type' in filters:
                        query = query.filter(UnifiedPropertyDB.property_type == filters['property_type'])
                    if 'discovery_status' in filters:
                        query = query.filter(UnifiedPropertyDB.discovery_status == filters['discovery_status'])
                    if 'min_investment_score' in filters:
                        query = query.filter(UnifiedPropertyDB.investment_score >= filters['min_investment_score'])
                    if 'max_price' in filters:
                        query = query.filter(
                            or_(
                                UnifiedPropertyDB.asking_price <= filters['max_price'],
                                and_(
                                    UnifiedPropertyDB.asking_price.is_(None),
                                    UnifiedPropertyDB.assessed_value <= filters['max_price']
                                )
                            )
                        )
                
                # Apply pagination and ordering
                properties_db = query.order_by(desc(UnifiedPropertyDB.discovered_at))\
                                   .offset(offset)\
                                   .limit(limit)\
                                   .all()
                
                # Convert to Pydantic models
                properties = []
                for prop_db in properties_db:
                    prop_dict = self._db_to_dict(prop_db)
                    properties.append(UnifiedProperty(**prop_dict))
                
                return properties
                
        except Exception as e:
            logger.error(f"Failed to get properties: {e}")
            return []
    
    async def get_property_by_id(self, property_id: str) -> Optional[UnifiedProperty]:
        """Get property by ID"""
        try:
            with get_db_session() as db:
                prop_db = db.query(UnifiedPropertyDB).filter(
                    UnifiedPropertyDB.id == property_id
                ).first()
                
                if prop_db:
                    prop_dict = self._db_to_dict(prop_db)
                    return UnifiedProperty(**prop_dict)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get property {property_id}: {e}")
            return None
    
    async def save_property(self, property: UnifiedProperty) -> bool:
        """Save or update property in database"""
        try:
            with get_db_session() as db:
                # Check if property exists
                existing = db.query(UnifiedPropertyDB).filter(
                    UnifiedPropertyDB.id == property.id
                ).first()
                
                if existing:
                    # Update existing
                    self._update_db_property(existing, property)
                else:
                    # Create new
                    prop_db = UnifiedPropertyDB(**property.dict(exclude={'id'}))
                    prop_db.id = property.id
                    db.add(prop_db)
                
                db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to save property {property.id}: {e}")
            return False
    
    async def get_analysis_queue(self, status: Optional[str] = None) -> Dict[str, Any]:
        """Get analysis job queue status"""
        try:
            with get_db_session() as db:
                query = db.query(WorkflowJob)
                
                if status:
                    query = query.filter(WorkflowJob.status == status)
                
                jobs = query.order_by(desc(WorkflowJob.started_at)).limit(100).all()
                
                # Group by status
                status_counts = {}
                for job in jobs:
                    status_counts[job.status] = status_counts.get(job.status, 0) + 1
                
                return {
                    "queue_status": status_counts,
                    "total_jobs": len(jobs),
                    "recent_jobs": [self._workflow_job_to_dict(job) for job in jobs[:10]],
                    "updated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get analysis queue: {e}")
            return {"error": str(e)}
    
    async def get_analysis_results(self, job_id: str) -> Optional[IntegratedAnalysis]:
        """Get analysis results by job ID"""
        try:
            with get_db_session() as db:
                analysis_db = db.query(IntegratedAnalysisDB).filter(
                    IntegratedAnalysisDB.id == job_id
                ).first()
                
                if analysis_db:
                    analysis_dict = self._db_to_dict(analysis_db)
                    return IntegratedAnalysis(**analysis_dict)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get analysis results {job_id}: {e}")
            return None
    
    async def get_investment_opportunities(self, filters: Dict[str, Any], 
                                         limit: int = 25) -> List[UnifiedProperty]:
        """Get high-scoring investment opportunities"""
        try:
            with get_db_session() as db:
                query = db.query(UnifiedPropertyDB)
                
                # Apply opportunity-specific filters
                if 'min_investment_score' in filters:
                    query = query.filter(
                        UnifiedPropertyDB.investment_score >= filters['min_investment_score']
                    )
                
                if 'discovery_status' in filters:
                    query = query.filter(
                        UnifiedPropertyDB.discovery_status == filters['discovery_status']
                    )
                
                if 'county' in filters:
                    query = query.filter(UnifiedPropertyDB.county == filters['county'])
                
                if 'max_price' in filters:
                    query = query.filter(
                        or_(
                            UnifiedPropertyDB.asking_price <= filters['max_price'],
                            and_(
                                UnifiedPropertyDB.asking_price.is_(None),
                                UnifiedPropertyDB.assessed_value <= filters['max_price']
                            )
                        )
                    )
                
                # Order by investment score descending
                opportunities_db = query.order_by(desc(UnifiedPropertyDB.investment_score))\
                                      .limit(limit)\
                                      .all()
                
                opportunities = []
                for opp_db in opportunities_db:
                    opp_dict = self._db_to_dict(opp_db)
                    opportunities.append(UnifiedProperty(**opp_dict))
                
                return opportunities
                
        except Exception as e:
            logger.error(f"Failed to get investment opportunities: {e}")
            return []
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary statistics"""
        try:
            with get_db_session() as db:
                # Total properties
                total_properties = db.query(UnifiedPropertyDB).count()
                
                # Properties by status
                status_counts = {}
                for status in ProcessingStatus:
                    count = db.query(UnifiedPropertyDB).filter(
                        UnifiedPropertyDB.discovery_status == status
                    ).count()
                    status_counts[status.value] = count
                
                # Properties by county
                county_counts = {}
                counties = ['Fulton', 'DeKalb', 'Clayton', 'Cobb', 'Atlanta']
                for county in counties:
                    count = db.query(UnifiedPropertyDB).filter(
                        UnifiedPropertyDB.county == county
                    ).count()
                    county_counts[county] = count
                
                # High-value opportunities (score >= 70)
                high_value_count = db.query(UnifiedPropertyDB).filter(
                    UnifiedPropertyDB.investment_score >= 70
                ).count()
                
                # Recent activity (last 24 hours)
                yesterday = datetime.utcnow() - timedelta(hours=24)
                recent_discoveries = db.query(UnifiedPropertyDB).filter(
                    UnifiedPropertyDB.discovered_at >= yesterday
                ).count()
                
                recent_analyses = db.query(IntegratedAnalysisDB).filter(
                    IntegratedAnalysisDB.analysis_date >= yesterday
                ).count()
                
                # Average investment score
                from sqlalchemy import func
                avg_score = db.query(func.avg(UnifiedPropertyDB.investment_score)).scalar() or 0
                
                return {
                    "total_properties": total_properties,
                    "status_distribution": status_counts,
                    "county_distribution": county_counts,
                    "high_value_opportunities": high_value_count,
                    "recent_activity": {
                        "discoveries_24h": recent_discoveries,
                        "analyses_24h": recent_analyses
                    },
                    "average_investment_score": round(avg_score, 2),
                    "last_updated": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get dashboard summary: {e}")
            return {"error": str(e)}
    
    async def get_recent_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Get recent system activity"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            with get_db_session() as db:
                # Recent discoveries
                recent_properties = db.query(UnifiedPropertyDB).filter(
                    UnifiedPropertyDB.discovered_at >= cutoff_time
                ).order_by(desc(UnifiedPropertyDB.discovered_at)).limit(10).all()
                
                # Recent analyses
                recent_analyses = db.query(IntegratedAnalysisDB).filter(
                    IntegratedAnalysisDB.analysis_date >= cutoff_time
                ).order_by(desc(IntegratedAnalysisDB.analysis_date)).limit(10).all()
                
                # Recent workflow jobs
                recent_jobs = db.query(WorkflowJob).filter(
                    WorkflowJob.started_at >= cutoff_time
                ).order_by(desc(WorkflowJob.started_at)).limit(20).all()
                
                return {
                    "time_window_hours": hours,
                    "recent_discoveries": [
                        {
                            "id": prop.id,
                            "address": prop.address,
                            "county": prop.county,
                            "discovered_at": prop.discovered_at.isoformat(),
                            "investment_score": prop.investment_score
                        }
                        for prop in recent_properties
                    ],
                    "recent_analyses": [
                        {
                            "id": analysis.id,
                            "property_id": analysis.property_id,
                            "analysis_date": analysis.analysis_date.isoformat(),
                            "investment_recommendation": analysis.investment_recommendation
                        }
                        for analysis in recent_analyses
                    ],
                    "recent_jobs": [
                        self._workflow_job_to_dict(job) for job in recent_jobs
                    ],
                    "generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}")
            return {"error": str(e)}
    
    async def sync_all_sources(self, job_id: str, sources: List[str]):
        """Synchronize data from all specified sources"""
        logger.info(f"Starting data sync job {job_id} for sources: {sources}")
        
        try:
            sync_results = {}
            
            if "foreclosure_system" in sources:
                sync_results["foreclosure_system"] = await self._sync_foreclosure_data()
            
            if "valuation_system" in sources:
                sync_results["valuation_system"] = await self._sync_valuation_data()
            
            # Record sync job completion
            await self._record_sync_job(job_id, sync_results)
            
            logger.info(f"Data sync job {job_id} completed")
            return sync_results
            
        except Exception as e:
            logger.error(f"Data sync job {job_id} failed: {e}")
            await self._record_sync_job(job_id, {"error": str(e)})
            return {"error": str(e)}
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get integration system metrics"""
        try:
            with get_db_session() as db:
                # Database metrics
                total_properties = db.query(UnifiedPropertyDB).count()
                total_analyses = db.query(IntegratedAnalysisDB).count()
                total_jobs = db.query(WorkflowJob).count()
                
                # Processing metrics (last 7 days)
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                properties_week = db.query(UnifiedPropertyDB).filter(
                    UnifiedPropertyDB.discovered_at >= week_ago
                ).count()
                
                analyses_week = db.query(IntegratedAnalysisDB).filter(
                    IntegratedAnalysisDB.analysis_date >= week_ago
                ).count()
                
                # Success rates
                from sqlalchemy import func
                successful_jobs = db.query(WorkflowJob).filter(
                    and_(
                        WorkflowJob.started_at >= week_ago,
                        WorkflowJob.status == 'completed'
                    )
                ).count()
                
                total_jobs_week = db.query(WorkflowJob).filter(
                    WorkflowJob.started_at >= week_ago
                ).count()
                
                success_rate = (successful_jobs / total_jobs_week * 100) if total_jobs_week > 0 else 0
                
                # Average processing time
                avg_processing_time = db.query(func.avg(WorkflowJob.processing_time_seconds)).filter(
                    and_(
                        WorkflowJob.started_at >= week_ago,
                        WorkflowJob.processing_time_seconds.isnot(None)
                    )
                ).scalar() or 0
                
                return {
                    "database_metrics": {
                        "total_properties": total_properties,
                        "total_analyses": total_analyses,
                        "total_workflow_jobs": total_jobs
                    },
                    "processing_metrics": {
                        "properties_discovered_week": properties_week,
                        "analyses_completed_week": analyses_week,
                        "success_rate_percentage": round(success_rate, 2),
                        "average_processing_time_seconds": round(avg_processing_time, 2)
                    },
                    "generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}
    
    async def export_properties(self, format: str, filters: Dict[str, Any]) -> Any:
        """Export properties in specified format"""
        try:
            properties = await self.get_properties(limit=1000, filters=filters)
            
            if format == "json":
                return [prop.dict() for prop in properties]
            
            elif format == "csv":
                import csv
                import io
                
                output = io.StringIO()
                if properties:
                    writer = csv.DictWriter(output, fieldnames=properties[0].dict().keys())
                    writer.writeheader()
                    for prop in properties:
                        writer.writerow(prop.dict())
                
                return output.getvalue()
            
            elif format == "excel":
                import pandas as pd
                import io
                
                df = pd.DataFrame([prop.dict() for prop in properties])
                output = io.BytesIO()
                df.to_excel(output, index=False)
                output.seek(0)
                return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to export properties: {e}")
            return {"error": str(e)}
    
    # Helper methods
    def _db_to_dict(self, db_obj) -> Dict[str, Any]:
        """Convert SQLAlchemy object to dictionary"""
        result = {}
        for column in db_obj.__table__.columns:
            value = getattr(db_obj, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result
    
    def _update_db_property(self, db_prop: UnifiedPropertyDB, property: UnifiedProperty):
        """Update database property from Pydantic model"""
        for field, value in property.dict().items():
            if hasattr(db_prop, field):
                setattr(db_prop, field, value)
    
    def _workflow_job_to_dict(self, job: WorkflowJob) -> Dict[str, Any]:
        """Convert workflow job to dictionary"""
        return {
            "id": job.id,
            "property_id": job.property_id,
            "job_type": job.job_type,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "processing_time_seconds": job.processing_time_seconds,
            "records_processed": job.records_processed
        }
    
    async def _sync_foreclosure_data(self) -> Dict[str, Any]:
        """Sync data from foreclosure research system"""
        try:
            response = await self.client.get(f"{self.foreclosure_api_url}/api/properties")
            if response.status_code == 200:
                foreclosure_properties = response.json()
                synced_count = 0
                
                for prop_data in foreclosure_properties:
                    # Convert to unified format and save
                    unified_prop = self._convert_foreclosure_to_unified(prop_data)
                    if await self.save_property(unified_prop):
                        synced_count += 1
                
                return {
                    "status": "success",
                    "properties_synced": synced_count,
                    "total_properties": len(foreclosure_properties)
                }
            else:
                return {"status": "error", "message": f"API returned {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Foreclosure data sync failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _sync_valuation_data(self) -> Dict[str, Any]:
        """Sync data from valuation system"""
        try:
            response = await self.client.get(f"{self.valuation_api_url}/api/properties")
            if response.status_code == 200:
                valuation_properties = response.json()
                synced_count = 0
                
                for prop_data in valuation_properties:
                    # Convert to unified format and save
                    unified_prop = self._convert_valuation_to_unified(prop_data)
                    if await self.save_property(unified_prop):
                        synced_count += 1
                
                return {
                    "status": "success",
                    "properties_synced": synced_count,
                    "total_properties": len(valuation_properties)
                }
            else:
                return {"status": "error", "message": f"API returned {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Valuation data sync failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _record_sync_job(self, job_id: str, results: Dict[str, Any]):
        """Record sync job completion in database"""
        try:
            with get_db_session() as db:
                job = WorkflowJob(
                    id=job_id,
                    job_type="data_sync",
                    status="completed" if "error" not in results else "failed",
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    result_data=results
                )
                db.add(job)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to record sync job {job_id}: {e}")
    
    def _convert_foreclosure_to_unified(self, foreclosure_data: Dict[str, Any]) -> UnifiedProperty:
        """Convert foreclosure system data to unified format"""
        # Implementation would map foreclosure-specific fields
        return UnifiedProperty(**foreclosure_data)  # Simplified
    
    def _convert_valuation_to_unified(self, valuation_data: Dict[str, Any]) -> UnifiedProperty:
        """Convert valuation system data to unified format"""
        # Implementation would map valuation-specific fields
        return UnifiedProperty(**valuation_data)  # Simplified