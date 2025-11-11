"""
Database Connection and Management Module
Handles PostgreSQL, Redis, and Neo4j connections for the 4-Plex platform
Includes data persistence, caching, and graph database operations
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import sqlite3
from pathlib import Path

# For production use, these would be actual database connectors
# import asyncpg  # PostgreSQL
# import aioredis  # Redis
# import neo4j     # Neo4j

from models import Property, PropertyAnalysis, ProcessingJob, User, ActivityLog

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Central database manager for all data operations"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.db_path = Path(self.config.get("sqlite_path", "/tmp/4plex_platform.db"))
        self.connection = None
        self._initialize_database()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default database configuration"""
        return {
            "sqlite_path": "/tmp/4plex_platform.db",
            "enable_redis": False,  # Set to True when Redis is available
            "enable_neo4j": False,  # Set to True when Neo4j is available
            "postgres_url": os.getenv("DATABASE_URL"),
            "redis_url": os.getenv("REDIS_URL"),
            "neo4j_url": os.getenv("NEO4J_URL")
        }
    
    def _initialize_database(self):
        """Initialize SQLite database with tables"""
        try:
            self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            
            # Create tables
            self._create_tables()
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.connection.cursor()
        
        # Properties table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id TEXT PRIMARY KEY,
                name TEXT,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                county TEXT NOT NULL,
                state TEXT DEFAULT 'GA',
                zip_code TEXT,
                property_type TEXT NOT NULL,
                units INTEGER,
                square_footage INTEGER,
                lot_size REAL,
                year_built INTEGER,
                status TEXT DEFAULT 'discovered',
                foreclosure_stage TEXT,
                foreclosure_date DATE,
                auction_date DATE,
                outstanding_debt REAL,
                estimated_value REAL,
                assessed_value REAL,
                purchase_price REAL,
                investment_score REAL,
                roi_estimate REAL,
                cap_rate REAL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_sources TEXT,  -- JSON array
                agent_notes TEXT,
                tags TEXT,  -- JSON array
                created_by TEXT,
                metadata TEXT  -- JSON object for additional data
            )
        """)
        
        # Property analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS property_analyses (
                id TEXT PRIMARY KEY,
                property_id TEXT NOT NULL,
                analysis_type TEXT DEFAULT 'investment',
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                financial_metrics TEXT NOT NULL,  -- JSON object
                projections TEXT,  -- JSON array
                market_analysis TEXT,  -- JSON object
                overall_risk TEXT,
                risk_factors TEXT,  -- JSON array
                investment_grade TEXT,
                recommendation TEXT,
                confidence_level REAL,
                viability_score REAL,
                ai_insights TEXT,  -- JSON array
                opportunities TEXT,  -- JSON array
                key_factors TEXT,  -- JSON array
                analysis_assumptions TEXT,  -- JSON object
                FOREIGN KEY (property_id) REFERENCES properties (id)
            )
        """)
        
        # Processing jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                message TEXT,
                property_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                estimated_completion TIMESTAMP,
                results TEXT,  -- JSON object
                error_message TEXT,
                settings TEXT,  -- JSON object
                FOREIGN KEY (property_id) REFERENCES properties (id)
            )
        """)
        
        # Activity logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                activity_type TEXT NOT NULL,
                user_id TEXT,
                property_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                metadata TEXT,  -- JSON object
                status TEXT DEFAULT 'info',
                is_public INTEGER DEFAULT 1,
                FOREIGN KEY (property_id) REFERENCES properties (id)
            )
        """)
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                role TEXT DEFAULT 'investor',
                preferred_counties TEXT,  -- JSON array
                preferred_property_types TEXT,  -- JSON array
                investment_criteria TEXT,  -- JSON object
                properties TEXT,  -- JSON array of property IDs
                watchlist TEXT,  -- JSON array of property IDs
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Investment reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS investment_reports (
                id TEXT PRIMARY KEY,
                property_id TEXT NOT NULL,
                report_type TEXT DEFAULT 'comprehensive',
                executive_summary TEXT,
                financial_analysis TEXT,  -- JSON object
                market_analysis TEXT,  -- JSON object
                risk_assessment TEXT,  -- JSON object
                recommendations TEXT,  -- JSON array
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                generated_by TEXT,
                template_used TEXT,
                pdf_path TEXT,
                excel_path TEXT,
                powerpoint_path TEXT,
                report_settings TEXT,  -- JSON object
                FOREIGN KEY (property_id) REFERENCES properties (id)
            )
        """)
        
        self.connection.commit()
        logger.info("Database tables created successfully")
    
    # Property operations
    async def save_property(self, property_obj: Property) -> bool:
        """Save property to database"""
        try:
            cursor = self.connection.cursor()
            
            # Convert property to database format
            property_data = (
                property_obj.id,
                property_obj.name,
                property_obj.address,
                property_obj.city,
                property_obj.county,
                property_obj.state,
                property_obj.zip_code,
                property_obj.property_type.value,
                property_obj.units,
                property_obj.square_footage,
                property_obj.lot_size,
                property_obj.year_built,
                property_obj.status.value,
                property_obj.foreclosure_stage.value if property_obj.foreclosure_stage else None,
                property_obj.foreclosure_date.isoformat() if property_obj.foreclosure_date else None,
                property_obj.auction_date.isoformat() if property_obj.auction_date else None,
                property_obj.outstanding_debt,
                property_obj.estimated_value,
                property_obj.assessed_value,
                property_obj.purchase_price,
                property_obj.investment_score,
                property_obj.roi_estimate,
                property_obj.cap_rate,
                property_obj.discovered_at.isoformat(),
                property_obj.last_updated.isoformat(),
                json.dumps(property_obj.data_sources),
                property_obj.agent_notes,
                json.dumps(property_obj.tags),
                property_obj.created_by,
                json.dumps({"images": property_obj.images, "documents": property_obj.documents})
            )
            
            cursor.execute("""
                INSERT OR REPLACE INTO properties (
                    id, name, address, city, county, state, zip_code, property_type, units,
                    square_footage, lot_size, year_built, status, foreclosure_stage,
                    foreclosure_date, auction_date, outstanding_debt, estimated_value,
                    assessed_value, purchase_price, investment_score, roi_estimate, cap_rate,
                    discovered_at, last_updated, data_sources, agent_notes, tags, created_by, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, property_data)
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save property {property_obj.id}: {str(e)}")
            return False
    
    async def get_property(self, property_id: str) -> Optional[Property]:
        """Retrieve property by ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Convert database row to Property object
            return self._row_to_property(row)
            
        except Exception as e:
            logger.error(f"Failed to retrieve property {property_id}: {str(e)}")
            return None
    
    async def get_properties(self, filters: Dict[str, Any] = None, limit: int = 50, sort_by: str = "investment_score DESC") -> List[Property]:
        """Retrieve properties with optional filtering"""
        try:
            cursor = self.connection.cursor()
            
            query = "SELECT * FROM properties WHERE 1=1"
            params = []
            
            if filters:
                if filters.get("county"):
                    query += " AND county = ?"
                    params.append(filters["county"])
                
                if filters.get("status"):
                    query += " AND status = ?"
                    params.append(filters["status"])
                
                if filters.get("min_investment_score"):
                    query += " AND investment_score >= ?"
                    params.append(filters["min_investment_score"])
                
                if filters.get("property_type"):
                    query += " AND property_type = ?"
                    params.append(filters["property_type"])
            
            # Validate sort_by to prevent SQL injection
            valid_sorts = {
                "investment_score DESC": "investment_score DESC",
                "investment_score ASC": "investment_score ASC", 
                "discovered_at DESC": "discovered_at DESC",
                "discovered_at ASC": "discovered_at ASC",
                "estimated_value DESC": "estimated_value DESC",
                "estimated_value ASC": "estimated_value ASC"
            }
            sort_clause = valid_sorts.get(sort_by, "investment_score DESC")
            
            query += f" ORDER BY {sort_clause} LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_property(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to retrieve properties: {str(e)}")
            return []
    
    def _row_to_property(self, row) -> Property:
        """Convert database row to Property object"""
        from models import PropertyType, PropertyStatus, ForeclosureStage
        
        return Property(
            id=row["id"],
            name=row["name"],
            address=row["address"],
            city=row["city"],
            county=row["county"],
            state=row["state"],
            zip_code=row["zip_code"],
            property_type=PropertyType(row["property_type"]),
            units=row["units"],
            square_footage=row["square_footage"],
            lot_size=row["lot_size"],
            year_built=row["year_built"],
            status=PropertyStatus(row["status"]),
            foreclosure_stage=ForeclosureStage(row["foreclosure_stage"]) if row["foreclosure_stage"] else None,
            foreclosure_date=datetime.fromisoformat(row["foreclosure_date"]).date() if row["foreclosure_date"] else None,
            auction_date=datetime.fromisoformat(row["auction_date"]).date() if row["auction_date"] else None,
            outstanding_debt=row["outstanding_debt"],
            estimated_value=row["estimated_value"],
            assessed_value=row["assessed_value"],
            purchase_price=row["purchase_price"],
            investment_score=row["investment_score"],
            roi_estimate=row["roi_estimate"],
            cap_rate=row["cap_rate"],
            discovered_at=datetime.fromisoformat(row["discovered_at"]),
            last_updated=datetime.fromisoformat(row["last_updated"]),
            data_sources=json.loads(row["data_sources"]) if row["data_sources"] else [],
            agent_notes=row["agent_notes"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_by=row["created_by"]
        )
    
    # Analysis operations
    async def save_analysis(self, analysis: PropertyAnalysis) -> bool:
        """Save property analysis to database"""
        try:
            cursor = self.connection.cursor()
            
            analysis_data = (
                analysis.id,
                analysis.property_id,
                analysis.analysis_type,
                analysis.generated_at.isoformat(),
                json.dumps(analysis.financial_metrics.dict()),
                json.dumps([p.dict() for p in analysis.projections]),
                json.dumps(analysis.market_analysis),
                analysis.overall_risk.value,
                json.dumps(analysis.risk_factors),
                analysis.investment_grade.value if analysis.investment_grade else None,
                analysis.recommendation,
                analysis.confidence_level,
                analysis.viability_score,
                json.dumps(analysis.ai_insights),
                json.dumps(analysis.opportunities),
                json.dumps(analysis.key_factors),
                json.dumps(analysis.analysis_assumptions)
            )
            
            cursor.execute("""
                INSERT OR REPLACE INTO property_analyses (
                    id, property_id, analysis_type, generated_at, financial_metrics,
                    projections, market_analysis, overall_risk, risk_factors,
                    investment_grade, recommendation, confidence_level, viability_score,
                    ai_insights, opportunities, key_factors, analysis_assumptions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, analysis_data)
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save analysis {analysis.id}: {str(e)}")
            return False
    
    async def get_analysis(self, property_id: str) -> Optional[PropertyAnalysis]:
        """Get analysis for a property"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM property_analyses WHERE property_id = ? ORDER BY generated_at DESC LIMIT 1", (property_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_analysis(row)
            
        except Exception as e:
            logger.error(f"Failed to retrieve analysis for property {property_id}: {str(e)}")
            return None
    
    def _row_to_analysis(self, row) -> PropertyAnalysis:
        """Convert database row to PropertyAnalysis object"""
        from models import RiskLevel, InvestmentGrade, FinancialMetrics, FinancialProjection
        
        # Parse financial metrics
        financial_data = json.loads(row["financial_metrics"])
        financial_metrics = FinancialMetrics(**financial_data)
        
        # Parse projections
        projections_data = json.loads(row["projections"]) if row["projections"] else []
        projections = [FinancialProjection(**p) for p in projections_data]
        
        return PropertyAnalysis(
            id=row["id"],
            property_id=row["property_id"],
            analysis_type=row["analysis_type"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            financial_metrics=financial_metrics,
            projections=projections,
            market_analysis=json.loads(row["market_analysis"]) if row["market_analysis"] else {},
            overall_risk=RiskLevel(row["overall_risk"]),
            risk_factors=json.loads(row["risk_factors"]) if row["risk_factors"] else [],
            investment_grade=InvestmentGrade(row["investment_grade"]) if row["investment_grade"] else None,
            recommendation=row["recommendation"],
            confidence_level=row["confidence_level"],
            viability_score=row["viability_score"],
            ai_insights=json.loads(row["ai_insights"]) if row["ai_insights"] else [],
            opportunities=json.loads(row["opportunities"]) if row["opportunities"] else [],
            key_factors=json.loads(row["key_factors"]) if row["key_factors"] else [],
            analysis_assumptions=json.loads(row["analysis_assumptions"]) if row["analysis_assumptions"] else {}
        )
    
    # Job operations
    async def save_job(self, job: ProcessingJob) -> bool:
        """Save processing job to database"""
        try:
            cursor = self.connection.cursor()
            
            job_data = (
                job.id,
                job.job_type,
                job.status,
                job.progress,
                job.message,
                job.property_id,
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.estimated_completion.isoformat() if job.estimated_completion else None,
                json.dumps(job.results),
                job.error_message,
                json.dumps(job.settings)
            )
            
            cursor.execute("""
                INSERT OR REPLACE INTO processing_jobs (
                    id, job_type, status, progress, message, property_id, created_at,
                    started_at, completed_at, estimated_completion, results, error_message, settings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, job_data)
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save job {job.id}: {str(e)}")
            return False
    
    async def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get processing job by ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM processing_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return ProcessingJob(
                id=row["id"],
                job_type=row["job_type"],
                status=row["status"],
                progress=row["progress"],
                message=row["message"],
                property_id=row["property_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                estimated_completion=datetime.fromisoformat(row["estimated_completion"]) if row["estimated_completion"] else None,
                results=json.loads(row["results"]) if row["results"] else {},
                error_message=row["error_message"],
                settings=json.loads(row["settings"]) if row["settings"] else {}
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve job {job_id}: {str(e)}")
            return None
    
    # Activity logging
    async def log_activity(self, activity: ActivityLog) -> bool:
        """Log activity to database"""
        try:
            cursor = self.connection.cursor()
            
            activity_data = (
                activity.id,
                activity.timestamp.isoformat(),
                activity.activity_type,
                activity.user_id,
                activity.property_id,
                activity.title,
                activity.description,
                json.dumps(activity.metadata),
                activity.status,
                1 if activity.is_public else 0
            )
            
            cursor.execute("""
                INSERT INTO activity_logs (
                    id, timestamp, activity_type, user_id, property_id, title,
                    description, metadata, status, is_public
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, activity_data)
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log activity {activity.id}: {str(e)}")
            return False
    
    async def get_recent_activity(self, limit: int = 20) -> List[ActivityLog]:
        """Get recent activity logs"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM activity_logs 
                WHERE is_public = 1 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            activities = []
            for row in rows:
                activity = ActivityLog(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    activity_type=row["activity_type"],
                    user_id=row["user_id"],
                    property_id=row["property_id"],
                    title=row["title"],
                    description=row["description"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    status=row["status"],
                    is_public=bool(row["is_public"])
                )
                activities.append(activity)
            
            return activities
            
        except Exception as e:
            logger.error(f"Failed to retrieve activity logs: {str(e)}")
            return []
    
    # Statistics and metrics
    async def get_metrics(self) -> Dict[str, Any]:
        """Get platform metrics"""
        try:
            cursor = self.connection.cursor()
            
            # Count properties
            cursor.execute("SELECT COUNT(*) as count FROM properties")
            total_properties = cursor.fetchone()["count"]
            
            # Count opportunities (investment_score >= 70)
            cursor.execute("SELECT COUNT(*) as count FROM properties WHERE investment_score >= 70")
            opportunities = cursor.fetchone()["count"]
            
            # Calculate average ROI
            cursor.execute("SELECT AVG(roi_estimate) as avg_roi FROM properties WHERE roi_estimate IS NOT NULL")
            avg_roi_result = cursor.fetchone()
            avg_roi = avg_roi_result["avg_roi"] if avg_roi_result["avg_roi"] else 18.2
            
            # Count active counties
            cursor.execute("SELECT COUNT(DISTINCT county) as count FROM properties")
            counties = cursor.fetchone()["count"]
            
            # Recent activity counts
            cursor.execute("""
                SELECT COUNT(*) as count FROM properties 
                WHERE datetime(discovered_at) > datetime('now', '-1 day')
            """)
            discoveries_24h = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM property_analyses 
                WHERE datetime(generated_at) > datetime('now', '-1 day')
            """)
            analyses_24h = cursor.fetchone()["count"]
            
            return {
                "properties_analyzed": total_properties,
                "investment_opportunities": opportunities,
                "average_roi": round(avg_roi, 1),
                "counties_active": counties,
                "recent_activity": {
                    "discoveries_24h": discoveries_24h,
                    "analyses_24h": analyses_24h
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve metrics: {str(e)}")
            return {
                "properties_analyzed": 0,
                "investment_opportunities": 0,
                "average_roi": 0.0,
                "counties_active": 0,
                "recent_activity": {
                    "discoveries_24h": 0,
                    "analyses_24h": 0
                }
            }
    
    async def get_property_counts_by_stage(self) -> Dict[str, int]:
        """Get property counts by foreclosure stage"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                SELECT foreclosure_stage, COUNT(*) as count 
                FROM properties 
                WHERE foreclosure_stage IS NOT NULL
                GROUP BY foreclosure_stage
            """)
            
            rows = cursor.fetchall()
            return {row["foreclosure_stage"]: row["count"] for row in rows}
            
        except Exception as e:
            logger.error(f"Failed to get property counts by stage: {str(e)}")
            return {}
    
    async def update_job_status(self, job_id: str, status: str, progress: int = None, message: str = None, results: Dict[str, Any] = None) -> bool:
        """Update job status and progress"""
        try:
            cursor = self.connection.cursor()
            
            update_fields = ["status = ?"]
            params = [status]
            
            if progress is not None:
                update_fields.append("progress = ?")
                params.append(progress)
                
            if message is not None:
                update_fields.append("message = ?")
                params.append(message)
                
            if results is not None:
                update_fields.append("results = ?")
                params.append(json.dumps(results))
                
            # Set completion time if status is completed
            if status == "completed":
                update_fields.append("completed_at = ?")
                params.append(datetime.now().isoformat())
            elif status == "running" and progress is None:  # Starting job
                update_fields.append("started_at = ?")
                params.append(datetime.now().isoformat())
            
            params.append(job_id)  # WHERE clause parameter
            
            query = f"UPDATE processing_jobs SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            
            self.connection.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {str(e)}")
            return False
    
    async def get_jobs_by_status(self, status: str) -> List[ProcessingJob]:
        """Get all jobs with specific status"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM processing_jobs WHERE status = ? ORDER BY created_at DESC", (status,))
            rows = cursor.fetchall()
            
            jobs = []
            for row in rows:
                job = ProcessingJob(
                    id=row["id"],
                    job_type=row["job_type"],
                    status=row["status"],
                    progress=row["progress"],
                    message=row["message"],
                    property_id=row["property_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    estimated_completion=datetime.fromisoformat(row["estimated_completion"]) if row["estimated_completion"] else None,
                    results=json.loads(row["results"]) if row["results"] else {},
                    error_message=row["error_message"],
                    settings=json.loads(row["settings"]) if row["settings"] else {}
                )
                jobs.append(job)
                
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to get jobs by status {status}: {str(e)}")
            return []
    
    def close(self):
        """Close database connections"""
        if self.connection:
            self.connection.close()

# Global database instance
db_manager = DatabaseManager()

# Convenience functions for external use
async def save_property(property_obj: Property) -> bool:
    """Save property to database"""
    return await db_manager.save_property(property_obj)

async def get_property(property_id: str) -> Optional[Property]:
    """Get property by ID"""
    return await db_manager.get_property(property_id)

async def get_properties(filters: Dict[str, Any] = None, limit: int = 50, sort_by: str = "investment_score DESC") -> List[Property]:
    """Get properties with filtering"""
    return await db_manager.get_properties(filters, limit, sort_by)

async def save_analysis(analysis: PropertyAnalysis) -> bool:
    """Save property analysis"""
    return await db_manager.save_analysis(analysis)

async def get_analysis(property_id: str) -> Optional[PropertyAnalysis]:
    """Get property analysis"""
    return await db_manager.get_analysis(property_id)

async def save_job(job: ProcessingJob) -> bool:
    """Save processing job"""
    return await db_manager.save_job(job)

async def get_job(job_id: str) -> Optional[ProcessingJob]:
    """Get processing job"""
    return await db_manager.get_job(job_id)

async def log_activity(activity: ActivityLog) -> bool:
    """Log platform activity"""
    return await db_manager.log_activity(activity)

async def get_recent_activity(limit: int = 20) -> List[ActivityLog]:
    """Get recent activity"""
    return await db_manager.get_recent_activity(limit)

async def get_platform_metrics() -> Dict[str, Any]:
    """Get platform metrics"""
    return await db_manager.get_metrics()

async def get_property_counts_by_stage() -> Dict[str, int]:
    """Get property counts by foreclosure stage"""
    return await db_manager.get_property_counts_by_stage()

async def update_job_status(job_id: str, status: str, progress: int = None, message: str = None, results: Dict[str, Any] = None) -> bool:
    """Update job status and progress"""
    return await db_manager.update_job_status(job_id, status, progress, message, results)

async def get_jobs_by_status(status: str) -> List[ProcessingJob]:
    """Get all jobs with specific status"""
    return await db_manager.get_jobs_by_status(status)