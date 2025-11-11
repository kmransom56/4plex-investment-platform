"""
Property Management CRUD Operations for 4-plex Investment Platform
Comprehensive property lifecycle management with foreclosure discovery and multifamily analysis
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
import shutil

from models import Property, PropertyAnalysis, FinancialMetrics, ProcessingJob
from database.connection import DatabaseManager
from document_processing import DocumentProcessor
from financial_calculations import FinancialCalculator

class PropertyManager:
    """
    Comprehensive property management system
    Handles property lifecycle from discovery through investment analysis
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager(config.get('database', {}))
        self.document_processor = DocumentProcessor(config)
        self.financial_calculator = FinancialCalculator(config.get('financial_assumptions', {}))
        
        # File management configuration
        self.upload_dir = config.get('file_management', {}).get('upload_dir', './uploads')
        self.output_dir = config.get('file_management', {}).get('output_dir', './outputs')
        self.max_file_age_days = config.get('file_management', {}).get('max_file_age_days', 30)
        
        # Ensure directories exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    # Property CRUD Operations
    
    async def create_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new property record
        
        Args:
            property_data: Property information dictionary
            
        Returns:
            Created property with generated ID
        """
        try:
            # Generate unique ID if not provided
            if 'id' not in property_data:
                property_data['id'] = f"prop_{uuid.uuid4().hex[:12]}"
            
            # Set discovery date if not provided
            if 'discovery_date' not in property_data:
                property_data['discovery_date'] = datetime.now()
            
            # Set initial status
            if 'foreclosure_stage' not in property_data:
                property_data['foreclosure_stage'] = 'discovered'
            
            # Validate and create Property model
            property_obj = Property(**property_data)
            
            # Save to database
            saved_property = self.db_manager.save_property(property_obj.dict())
            
            # Log activity
            await self._log_property_activity(
                property_data['id'], 
                'created', 
                f"Property created: {property_data.get('address', 'Unknown address')}"
            )
            
            self.logger.info(f"Property created: {property_data['id']}")
            return saved_property
            
        except Exception as e:
            self.logger.error(f"Error creating property: {str(e)}")
            raise ValueError(f"Failed to create property: {str(e)}")
    
    async def get_property(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a property by ID
        
        Args:
            property_id: Unique property identifier
            
        Returns:
            Property data or None if not found
        """
        try:
            property_data = self.db_manager.get_property(property_id)
            
            if property_data:
                # Enrich with recent activity
                property_data['recent_activity'] = await self._get_recent_activity(property_id)
                
                # Add analysis summary if available
                latest_analysis = self.db_manager.get_latest_analysis(property_id)
                if latest_analysis:
                    property_data['latest_analysis'] = {
                        'id': latest_analysis['id'],
                        'analysis_date': latest_analysis['analysis_date'],
                        'investment_grade': latest_analysis['investment_grade'],
                        'viability_score': latest_analysis['viability_score'],
                        'confidence_score': latest_analysis['confidence_score']
                    }
                
                self.logger.info(f"Property retrieved: {property_id}")
            else:
                self.logger.warning(f"Property not found: {property_id}")
            
            return property_data
            
        except Exception as e:
            self.logger.error(f"Error retrieving property {property_id}: {str(e)}")
            raise
    
    async def update_property(self, property_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update property information
        
        Args:
            property_id: Property to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated property data
        """
        try:
            # Get existing property
            existing_property = self.db_manager.get_property(property_id)
            if not existing_property:
                raise ValueError(f"Property not found: {property_id}")
            
            # Track what fields are being updated for activity logging
            updated_fields = []
            for field, new_value in updates.items():
                if field in existing_property and existing_property[field] != new_value:
                    updated_fields.append(field)
            
            # Update last_modified
            updates['last_modified'] = datetime.now()
            
            # Update in database
            updated_property = self.db_manager.update_property(property_id, updates)
            
            # Log activity
            if updated_fields:
                await self._log_property_activity(
                    property_id, 
                    'updated', 
                    f"Updated fields: {', '.join(updated_fields)}"
                )
            
            self.logger.info(f"Property updated: {property_id}, fields: {updated_fields}")
            return updated_property
            
        except Exception as e:
            self.logger.error(f"Error updating property {property_id}: {str(e)}")
            raise
    
    async def delete_property(self, property_id: str, hard_delete: bool = False) -> bool:
        """
        Delete or soft delete a property
        
        Args:
            property_id: Property to delete
            hard_delete: If True, permanently delete; otherwise soft delete
            
        Returns:
            True if successful
        """
        try:
            if hard_delete:
                # Permanently delete property and all associated data
                success = self.db_manager.delete_property(property_id)
                
                # Clean up associated files
                await self._cleanup_property_files(property_id)
                
                await self._log_property_activity(
                    property_id, 
                    'deleted', 
                    "Property permanently deleted"
                )
                
                self.logger.info(f"Property hard deleted: {property_id}")
            else:
                # Soft delete - mark as deleted
                updates = {
                    'is_deleted': True,
                    'deleted_date': datetime.now()
                }
                success = bool(self.db_manager.update_property(property_id, updates))
                
                await self._log_property_activity(
                    property_id, 
                    'soft_deleted', 
                    "Property marked as deleted"
                )
                
                self.logger.info(f"Property soft deleted: {property_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting property {property_id}: {str(e)}")
            raise
    
    async def list_properties(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'discovery_date',
        sort_order: str = 'desc',
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List properties with filtering and pagination
        
        Args:
            filters: Optional filters to apply
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Dictionary with properties list and metadata
        """
        try:
            # Construct sort_by parameter from sort_by and sort_order
            sort_clause = f"{sort_by} {sort_order.upper()}"
            
            properties = await self.db_manager.get_properties(
                filters=filters,
                sort_by=sort_clause,
                limit=limit
            )
            
            # Enrich each property with summary data
            enriched_properties = []
            for prop in properties:
                # Add latest analysis summary
                latest_analysis = self.db_manager.get_latest_analysis(prop['id'])
                if latest_analysis:
                    prop['investment_summary'] = {
                        'grade': latest_analysis.get('investment_grade', 'Ungraded'),
                        'viability_score': latest_analysis.get('viability_score', 0),
                        'analysis_date': latest_analysis.get('analysis_date')
                    }
                
                # Add active job status
                active_job = self.db_manager.get_active_job(prop['id'])
                if active_job:
                    prop['processing_status'] = {
                        'job_id': active_job['id'],
                        'status': active_job['status'],
                        'progress': active_job['progress']
                    }
                
                enriched_properties.append(prop)
            
            # Get total count for pagination
            total_count = self.db_manager.count_properties(filters)
            
            result = {
                'properties': enriched_properties,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                },
                'filters_applied': filters or {},
                'sort': {'by': sort_by, 'order': sort_order}
            }
            
            self.logger.info(f"Listed {len(enriched_properties)} properties (total: {total_count})")
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing properties: {str(e)}")
            raise
    
    # Property Analysis Management
    
    async def create_analysis(self, property_id: str, document_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Create a new property analysis with document processing
        
        Args:
            property_id: Property to analyze
            document_files: Dictionary mapping document types to file paths
            
        Returns:
            Analysis results with job tracking information
        """
        try:
            # Verify property exists
            property_data = self.db_manager.get_property(property_id)
            if not property_data:
                raise ValueError(f"Property not found: {property_id}")
            
            # Update property stage to analyzing
            await self.update_property(property_id, {
                'foreclosure_stage': 'analyzing',
                'last_analysis_date': datetime.now()
            })
            
            # Process documents and create analysis
            analysis_results = await self.document_processor.process_property_documents(
                property_id=property_id,
                document_paths=document_files
            )
            
            # Update property stage based on results
            investment_grade = analysis_results.get('investment_metrics', {}).get('viability_score', {}).get('grade', 'B')
            new_stage = 'opportunity' if investment_grade in ['A', 'B'] else 'analyzed'
            
            await self.update_property(property_id, {
                'foreclosure_stage': new_stage,
                'investment_score': analysis_results.get('investment_metrics', {}).get('viability_score', {}).get('score', 0.5)
            })
            
            # Log activity
            await self._log_property_activity(
                property_id, 
                'analyzed', 
                f"Analysis completed with grade {investment_grade}"
            )
            
            self.logger.info(f"Analysis created for property: {property_id}")
            return analysis_results
            
        except Exception as e:
            # Update property back to discovered on error
            await self.update_property(property_id, {'foreclosure_stage': 'discovered'})
            
            await self._log_property_activity(
                property_id, 
                'analysis_failed', 
                f"Analysis failed: {str(e)}"
            )
            
            self.logger.error(f"Error creating analysis for property {property_id}: {str(e)}")
            raise
    
    async def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific analysis
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            Analysis data or None if not found
        """
        try:
            analysis = self.db_manager.get_analysis(analysis_id)
            
            if analysis:
                # Enrich with property information
                property_data = self.db_manager.get_property(analysis['property_id'])
                if property_data:
                    analysis['property_info'] = {
                        'address': property_data.get('address', ''),
                        'city': property_data.get('city', ''),
                        'state': property_data.get('state', ''),
                        'property_type': property_data.get('property_type', '')
                    }
                
                self.logger.info(f"Analysis retrieved: {analysis_id}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error retrieving analysis {analysis_id}: {str(e)}")
            raise
    
    async def list_property_analyses(self, property_id: str) -> List[Dict[str, Any]]:
        """
        List all analyses for a property
        
        Args:
            property_id: Property identifier
            
        Returns:
            List of analyses for the property
        """
        try:
            analyses = self.db_manager.get_property_analyses(property_id)
            
            self.logger.info(f"Retrieved {len(analyses)} analyses for property: {property_id}")
            return analyses
            
        except Exception as e:
            self.logger.error(f"Error listing analyses for property {property_id}: {str(e)}")
            raise
    
    # Processing Job Management
    
    async def get_processing_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get processing job status
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job data or None if not found
        """
        try:
            job = self.db_manager.get_job(job_id)
            
            if job:
                # Add estimated completion time for running jobs
                if job['status'] == 'processing':
                    job['estimated_completion'] = self._estimate_job_completion(job)
                
                self.logger.info(f"Job retrieved: {job_id}")
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error retrieving job {job_id}: {str(e)}")
            raise
    
    async def cancel_processing_job(self, job_id: str) -> bool:
        """
        Cancel a processing job
        
        Args:
            job_id: Job to cancel
            
        Returns:
            True if successfully cancelled
        """
        try:
            job = self.db_manager.get_job(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            
            if job['status'] not in ['processing', 'pending']:
                raise ValueError(f"Cannot cancel job with status: {job['status']}")
            
            # Update job status
            success = self.db_manager.update_job_status(
                job_id, 
                'cancelled', 
                job.get('progress', 0),
                error="Job cancelled by user"
            )
            
            # Reset property status if needed
            if job.get('property_id'):
                await self.update_property(job['property_id'], {
                    'foreclosure_stage': 'discovered'
                })
                
                await self._log_property_activity(
                    job['property_id'], 
                    'job_cancelled', 
                    f"Processing job {job_id} cancelled"
                )
            
            self.logger.info(f"Job cancelled: {job_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error cancelling job {job_id}: {str(e)}")
            raise
    
    async def list_processing_jobs(
        self, 
        property_id: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List processing jobs with optional filtering
        
        Args:
            property_id: Filter by property ID
            status_filter: Filter by job status
            
        Returns:
            List of processing jobs
        """
        try:
            jobs = self.db_manager.get_jobs(
                property_id=property_id,
                status_filter=status_filter
            )
            
            # Enrich with property information
            enriched_jobs = []
            for job in jobs:
                if job.get('property_id'):
                    property_data = self.db_manager.get_property(job['property_id'])
                    if property_data:
                        job['property_address'] = property_data.get('address', '')
                
                # Add estimated completion for processing jobs
                if job['status'] == 'processing':
                    job['estimated_completion'] = self._estimate_job_completion(job)
                
                enriched_jobs.append(job)
            
            self.logger.info(f"Listed {len(enriched_jobs)} processing jobs")
            return enriched_jobs
            
        except Exception as e:
            self.logger.error(f"Error listing processing jobs: {str(e)}")
            raise
    
    # Portfolio and Reporting Operations
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary
        
        Returns:
            Portfolio statistics and metrics
        """
        try:
            # Get property counts by stage
            stage_counts = await self.db_manager.get_property_counts_by_stage()
            
            # Get recent activities
            recent_activities = await self.db_manager.get_recent_activity(limit=10)
            
            # Get investment opportunities (Grade A/B properties)
            opportunities = await self.db_manager.get_properties(
                filters={'investment_grade': ['A', 'B']},
                limit=5
            )
            
            # Calculate portfolio value metrics
            portfolio_metrics = await self._calculate_portfolio_metrics()
            
            # Get processing job statistics
            job_stats = self.db_manager.get_job_statistics()
            
            summary = {
                'property_counts': stage_counts,
                'portfolio_metrics': portfolio_metrics,
                'top_opportunities': opportunities,
                'recent_activity': recent_activities,
                'processing_stats': job_stats,
                'summary_generated': datetime.now().isoformat()
            }
            
            self.logger.info("Portfolio summary generated")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating portfolio summary: {str(e)}")
            raise
    
    async def get_investment_opportunities(
        self, 
        min_grade: str = 'B',
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get current investment opportunities
        
        Args:
            min_grade: Minimum investment grade (A, B, C, D)
            max_results: Maximum number of results
            
        Returns:
            List of investment opportunities
        """
        try:
            # Grade hierarchy for filtering
            grade_hierarchy = {'A': 4, 'B': 3, 'C': 2, 'D': 1}
            min_grade_value = grade_hierarchy.get(min_grade, 3)
            
            # Get properties that meet grade criteria
            grade_filters = [grade for grade, value in grade_hierarchy.items() if value >= min_grade_value]
            
            opportunities = await self.db_manager.get_properties(
                filters={
                    'investment_grade': grade_filters,
                    'foreclosure_stage': ['opportunity', 'analyzed']
                },
                sort_by='investment_score DESC',
                limit=max_results
            )
            
            # Enrich with analysis data
            enriched_opportunities = []
            for opportunity in opportunities:
                latest_analysis = self.db_manager.get_latest_analysis(opportunity['id'])
                if latest_analysis:
                    opportunity['financial_summary'] = {
                        'cap_rate': latest_analysis.get('financial_metrics', {}).get('cap_rate', 0),
                        'irr': latest_analysis.get('financial_metrics', {}).get('irr', 0),
                        'cash_on_cash_return': latest_analysis.get('financial_metrics', {}).get('cash_on_cash_return', 0),
                        'investment_grade': latest_analysis.get('investment_grade', 'Ungraded')
                    }
                
                enriched_opportunities.append(opportunity)
            
            self.logger.info(f"Retrieved {len(enriched_opportunities)} investment opportunities")
            return enriched_opportunities
            
        except Exception as e:
            self.logger.error(f"Error retrieving investment opportunities: {str(e)}")
            raise
    
    async def generate_property_report(self, property_id: str, report_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Generate comprehensive property report
        
        Args:
            property_id: Property to report on
            report_type: Type of report (summary, comprehensive, financial)
            
        Returns:
            Generated report data
        """
        try:
            # Get property data
            property_data = await self.get_property(property_id)
            if not property_data:
                raise ValueError(f"Property not found: {property_id}")
            
            # Get all analyses for this property
            analyses = await self.list_property_analyses(property_id)
            
            # Get activity history
            activity_history = await self._get_property_activity_history(property_id)
            
            # Build report based on type
            if report_type == 'summary':
                report = {
                    'property_overview': self._extract_property_overview(property_data),
                    'current_status': property_data.get('foreclosure_stage', 'discovered'),
                    'latest_analysis': analyses[0] if analyses else None,
                    'key_metrics': self._extract_key_metrics(analyses[0] if analyses else None)
                }
            
            elif report_type == 'financial':
                latest_analysis = analyses[0] if analyses else None
                report = {
                    'property_overview': self._extract_property_overview(property_data),
                    'financial_analysis': latest_analysis.get('financial_metrics', {}) if latest_analysis else {},
                    'investment_metrics': latest_analysis.get('investment_metrics', {}) if latest_analysis else {},
                    'cash_flow_projections': self._generate_cash_flow_projections(latest_analysis),
                    'sensitivity_analysis': self._generate_sensitivity_analysis(latest_analysis)
                }
            
            else:  # comprehensive
                report = {
                    'property_overview': self._extract_property_overview(property_data),
                    'foreclosure_details': self._extract_foreclosure_details(property_data),
                    'financial_analysis': analyses,
                    'activity_history': activity_history,
                    'investment_recommendations': self._generate_investment_recommendations(property_data, analyses),
                    'risk_assessment': self._generate_risk_assessment(property_data, analyses),
                    'market_analysis': self._generate_market_analysis(property_data)
                }
            
            # Add report metadata
            report.update({
                'report_type': report_type,
                'property_id': property_id,
                'generated_date': datetime.now().isoformat(),
                'generated_by': 'PropertyManager'
            })
            
            self.logger.info(f"Generated {report_type} report for property: {property_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating report for property {property_id}: {str(e)}")
            raise
    
    # File Management Operations
    
    async def upload_property_document(
        self, 
        property_id: str, 
        file_path: str, 
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload and organize property document
        
        Args:
            property_id: Property the document belongs to
            file_path: Source file path
            document_type: Type of document (foreclosure, rent_roll, t12, etc.)
            metadata: Optional document metadata
            
        Returns:
            Document information with storage location
        """
        try:
            # Create property-specific directory
            property_dir = os.path.join(self.upload_dir, property_id)
            os.makedirs(property_dir, exist_ok=True)
            
            # Generate unique filename
            file_ext = Path(file_path).suffix
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_filename = f"{document_type}_{timestamp}{file_ext}"
            destination = os.path.join(property_dir, new_filename)
            
            # Copy file to managed location
            shutil.copy2(file_path, destination)
            
            # Create document record
            document_info = {
                'id': f"doc_{uuid.uuid4().hex[:12]}",
                'property_id': property_id,
                'document_type': document_type,
                'filename': new_filename,
                'file_path': destination,
                'file_size': os.path.getsize(destination),
                'uploaded_date': datetime.now(),
                'metadata': metadata or {}
            }
            
            # Save document record to database
            self.db_manager.save_document(document_info)
            
            # Log activity
            await self._log_property_activity(
                property_id, 
                'document_uploaded', 
                f"Uploaded {document_type}: {new_filename}"
            )
            
            self.logger.info(f"Document uploaded for property {property_id}: {new_filename}")
            return document_info
            
        except Exception as e:
            self.logger.error(f"Error uploading document for property {property_id}: {str(e)}")
            raise
    
    async def get_property_documents(self, property_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a property
        
        Args:
            property_id: Property identifier
            
        Returns:
            List of property documents
        """
        try:
            documents = self.db_manager.get_property_documents(property_id)
            
            # Add file existence check
            for doc in documents:
                doc['file_exists'] = os.path.exists(doc.get('file_path', ''))
                if not doc['file_exists']:
                    self.logger.warning(f"Missing file for document {doc['id']}: {doc.get('file_path', '')}")
            
            self.logger.info(f"Retrieved {len(documents)} documents for property: {property_id}")
            return documents
            
        except Exception as e:
            self.logger.error(f"Error retrieving documents for property {property_id}: {str(e)}")
            raise
    
    async def delete_property_document(self, property_id: str, document_id: str) -> bool:
        """
        Delete a property document
        
        Args:
            property_id: Property identifier
            document_id: Document to delete
            
        Returns:
            True if successful
        """
        try:
            # Get document info
            document = self.db_manager.get_document(document_id)
            if not document or document.get('property_id') != property_id:
                raise ValueError(f"Document not found or doesn't belong to property: {document_id}")
            
            # Delete physical file
            file_path = document.get('file_path', '')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete database record
            success = self.db_manager.delete_document(document_id)
            
            # Log activity
            await self._log_property_activity(
                property_id, 
                'document_deleted', 
                f"Deleted document: {document.get('filename', '')}"
            )
            
            self.logger.info(f"Document deleted: {document_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting document {document_id}: {str(e)}")
            raise
    
    # Maintenance and Utility Operations
    
    async def cleanup_old_files(self, days_threshold: int = None) -> Dict[str, Any]:
        """
        Clean up old files and data
        
        Args:
            days_threshold: Files older than this many days will be deleted
            
        Returns:
            Cleanup summary
        """
        try:
            if days_threshold is None:
                days_threshold = self.max_file_age_days
            
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            
            cleanup_stats = {
                'files_deleted': 0,
                'space_freed_mb': 0,
                'jobs_cleaned': 0,
                'errors': []
            }
            
            # Clean up old upload files
            if os.path.exists(self.upload_dir):
                for root, dirs, files in os.walk(self.upload_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            if datetime.fromtimestamp(os.path.getmtime(file_path)) < cutoff_date:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                cleanup_stats['files_deleted'] += 1
                                cleanup_stats['space_freed_mb'] += file_size / (1024 * 1024)
                        except Exception as e:
                            cleanup_stats['errors'].append(f"Error deleting {file_path}: {str(e)}")
            
            # Clean up old processing jobs
            old_jobs = self.db_manager.get_old_jobs(cutoff_date)
            for job in old_jobs:
                try:
                    self.db_manager.delete_job(job['id'])
                    cleanup_stats['jobs_cleaned'] += 1
                except Exception as e:
                    cleanup_stats['errors'].append(f"Error deleting job {job['id']}: {str(e)}")
            
            self.logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise
    
    async def backup_property_data(self, property_id: str, backup_location: str) -> str:
        """
        Create comprehensive backup of property data
        
        Args:
            property_id: Property to backup
            backup_location: Directory for backup files
            
        Returns:
            Path to backup archive
        """
        try:
            # Create backup directory structure
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(backup_location, f"property_{property_id}_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Export property data
            property_data = await self.get_property(property_id)
            with open(os.path.join(backup_dir, 'property_data.json'), 'w') as f:
                json.dump(property_data, f, indent=2, default=str)
            
            # Export all analyses
            analyses = await self.list_property_analyses(property_id)
            with open(os.path.join(backup_dir, 'analyses.json'), 'w') as f:
                json.dump(analyses, f, indent=2, default=str)
            
            # Copy all documents
            documents = await self.get_property_documents(property_id)
            docs_dir = os.path.join(backup_dir, 'documents')
            os.makedirs(docs_dir, exist_ok=True)
            
            for doc in documents:
                if doc.get('file_exists', False):
                    source_path = doc['file_path']
                    dest_path = os.path.join(docs_dir, doc['filename'])
                    shutil.copy2(source_path, dest_path)
            
            # Create backup manifest
            manifest = {
                'property_id': property_id,
                'backup_date': datetime.now().isoformat(),
                'property_data': bool(property_data),
                'analyses_count': len(analyses),
                'documents_count': len([d for d in documents if d.get('file_exists', False)]),
                'backup_location': backup_dir
            }
            
            with open(os.path.join(backup_dir, 'manifest.json'), 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.logger.info(f"Property backup created: {backup_dir}")
            return backup_dir
            
        except Exception as e:
            self.logger.error(f"Error creating backup for property {property_id}: {str(e)}")
            raise
    
    # Private Helper Methods
    
    async def _log_property_activity(self, property_id: str, activity_type: str, description: str):
        """Log property activity"""
        try:
            activity = {
                'property_id': property_id,
                'activity_type': activity_type,
                'description': description,
                'timestamp': datetime.now(),
                'user_id': 'system'  # Would be actual user in production
            }
            
            await self.db_manager.log_activity(activity)
        except Exception as e:
            self.logger.warning(f"Failed to log activity: {str(e)}")
    
    async def _get_recent_activity(self, property_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent activity for a property"""
        try:
            return self.db_manager.get_property_activities(property_id, limit=limit)
        except Exception as e:
            self.logger.warning(f"Failed to get recent activity for {property_id}: {str(e)}")
            return []
    
    async def _get_property_activity_history(self, property_id: str) -> List[Dict[str, Any]]:
        """Get complete activity history for a property"""
        try:
            return self.db_manager.get_property_activities(property_id, limit=100)
        except Exception as e:
            self.logger.warning(f"Failed to get activity history for {property_id}: {str(e)}")
            return []
    
    def _estimate_job_completion(self, job: Dict[str, Any]) -> Optional[str]:
        """Estimate job completion time"""
        try:
            if job.get('status') != 'processing':
                return None
            
            created_at = job.get('created_at')
            progress = job.get('progress', 0)
            
            if not created_at or progress <= 0:
                return None
            
            # Simple estimation based on current progress
            elapsed = datetime.now() - created_at
            estimated_total = elapsed / (progress / 100) if progress > 0 else None
            
            if estimated_total:
                completion_time = created_at + estimated_total
                return completion_time.isoformat()
            
            return None
        except Exception:
            return None
    
    async def _calculate_portfolio_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio-level metrics"""
        try:
            # Get all properties with analyses
            properties_with_analyses = self.db_manager.get_properties_with_analyses()
            
            if not properties_with_analyses:
                return {
                    'total_properties': 0,
                    'average_investment_score': 0,
                    'grade_distribution': {},
                    'total_potential_value': 0
                }
            
            # Calculate metrics
            total_properties = len(properties_with_analyses)
            investment_scores = [p.get('investment_score', 0) for p in properties_with_analyses if p.get('investment_score')]
            average_score = sum(investment_scores) / len(investment_scores) if investment_scores else 0
            
            # Grade distribution
            grades = [p.get('investment_grade', 'Ungraded') for p in properties_with_analyses]
            grade_distribution = {}
            for grade in set(grades):
                grade_distribution[grade] = grades.count(grade)
            
            # Estimate total potential value
            total_potential_value = 0
            for prop in properties_with_analyses:
                outstanding_debt = prop.get('outstanding_debt', 0)
                if outstanding_debt > 0:
                    # Estimate market value as 1.5x outstanding debt (conservative)
                    total_potential_value += outstanding_debt * 1.5
            
            return {
                'total_properties': total_properties,
                'average_investment_score': round(average_score, 3),
                'grade_distribution': grade_distribution,
                'total_potential_value': total_potential_value
            }
            
        except Exception as e:
            self.logger.warning(f"Error calculating portfolio metrics: {str(e)}")
            return {}
    
    def _extract_property_overview(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract property overview for reports"""
        return {
            'property_id': property_data.get('id'),
            'address': property_data.get('address', ''),
            'city': property_data.get('city', ''),
            'state': property_data.get('state', ''),
            'property_type': property_data.get('property_type', ''),
            'discovery_date': property_data.get('discovery_date'),
            'current_stage': property_data.get('foreclosure_stage', ''),
            'investment_score': property_data.get('investment_score', 0)
        }
    
    def _extract_foreclosure_details(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract foreclosure-specific details"""
        return {
            'foreclosure_stage': property_data.get('foreclosure_stage'),
            'outstanding_debt': property_data.get('outstanding_debt', 0),
            'estimated_value': property_data.get('estimated_value', 0),
            'auction_date': property_data.get('auction_date'),
            'minimum_bid': property_data.get('minimum_bid', 0),
            'case_number': property_data.get('case_number', '')
        }
    
    def _extract_key_metrics(self, analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract key metrics from analysis"""
        if not analysis:
            return {}
        
        financial_metrics = analysis.get('financial_metrics', {})
        return {
            'cap_rate': financial_metrics.get('cap_rate', 0),
            'irr': financial_metrics.get('irr', 0),
            'cash_on_cash_return': financial_metrics.get('cash_on_cash_return', 0),
            'noi': financial_metrics.get('noi', 0),
            'investment_grade': analysis.get('investment_grade', 'Ungraded')
        }
    
    def _generate_cash_flow_projections(self, analysis: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate cash flow projections"""
        if not analysis:
            return []
        
        # Would generate detailed 5-year cash flow projections
        # This is a simplified version
        base_noi = analysis.get('financial_metrics', {}).get('noi', 0)
        projections = []
        
        for year in range(1, 6):
            projected_noi = base_noi * (1.03 ** year)  # 3% annual growth
            projections.append({
                'year': year,
                'projected_noi': projected_noi,
                'projected_cash_flow': projected_noi * 0.8  # Simplified
            })
        
        return projections
    
    def _generate_sensitivity_analysis(self, analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate sensitivity analysis"""
        if not analysis:
            return {}
        
        # Simplified sensitivity analysis
        base_irr = analysis.get('investment_metrics', {}).get('irr', 0)
        
        return {
            'rent_growth_sensitivity': {
                'pessimistic': base_irr - 0.02,
                'base_case': base_irr,
                'optimistic': base_irr + 0.02
            },
            'exit_cap_sensitivity': {
                'pessimistic': base_irr - 0.015,
                'base_case': base_irr,
                'optimistic': base_irr + 0.015
            }
        }
    
    def _generate_investment_recommendations(
        self, 
        property_data: Dict[str, Any], 
        analyses: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate investment recommendations"""
        recommendations = []
        
        latest_analysis = analyses[0] if analyses else None
        if not latest_analysis:
            recommendations.append("Complete financial analysis required before investment decision")
            return recommendations
        
        investment_grade = latest_analysis.get('investment_grade', 'C')
        viability_score = latest_analysis.get('viability_score', 0.5)
        
        if investment_grade == 'A' and viability_score > 0.8:
            recommendations.extend([
                "Strong buy recommendation - excellent investment fundamentals",
                "Consider aggressive bidding strategy up to 85% of estimated market value",
                "Fast-track due diligence and financing approvals"
            ])
        elif investment_grade == 'B' and viability_score > 0.6:
            recommendations.extend([
                "Good investment opportunity with solid returns",
                "Recommend detailed property inspection before bidding",
                "Negotiate purchase price to improve returns"
            ])
        else:
            recommendations.extend([
                "High-risk investment - proceed with caution",
                "Consider alternative opportunities with better fundamentals",
                "If proceeding, limit exposure and have exit strategy"
            ])
        
        return recommendations
    
    def _generate_risk_assessment(
        self, 
        property_data: Dict[str, Any], 
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate risk assessment"""
        risk_factors = []
        risk_score = 0  # 0-100, higher is riskier
        
        # Market risk factors
        if not property_data.get('estimated_value'):
            risk_factors.append("Property valuation uncertain")
            risk_score += 15
        
        # Financial risk factors
        latest_analysis = analyses[0] if analyses else None
        if latest_analysis:
            cap_rate = latest_analysis.get('financial_metrics', {}).get('cap_rate', 0)
            if cap_rate < 0.05:
                risk_factors.append("Low cap rate indicates potential overvaluation")
                risk_score += 20
        
        # Foreclosure-specific risks
        if property_data.get('foreclosure_stage') == 'discovered':
            risk_factors.append("Early-stage foreclosure - timeline uncertain")
            risk_score += 10
        
        risk_level = "High" if risk_score > 60 else "Medium" if risk_score > 30 else "Low"
        
        return {
            'risk_score': min(risk_score, 100),
            'risk_level': risk_level,
            'risk_factors': risk_factors
        }
    
    def _generate_market_analysis(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate market analysis"""
        # Simplified market analysis - in production would use real market data
        return {
            'market_area': f"{property_data.get('city', 'Unknown')}, {property_data.get('state', '')}",
            'property_type_demand': 'moderate',  # Would be calculated from market data
            'comparable_sales': [],  # Would fetch from MLS or similar
            'market_trends': {
                'price_trend': 'stable',
                'inventory_levels': 'moderate',
                'days_on_market': 45  # Example
            }
        }
    
    async def _cleanup_property_files(self, property_id: str):
        """Clean up all files associated with a property"""
        try:
            # Clean up upload directory
            property_upload_dir = os.path.join(self.upload_dir, property_id)
            if os.path.exists(property_upload_dir):
                shutil.rmtree(property_upload_dir)
            
            # Clean up output directory
            property_output_dir = os.path.join(self.output_dir, property_id)
            if os.path.exists(property_output_dir):
                shutil.rmtree(property_output_dir)
            
            self.logger.info(f"Files cleaned up for property: {property_id}")
        except Exception as e:
            self.logger.warning(f"Error cleaning up files for property {property_id}: {str(e)}")