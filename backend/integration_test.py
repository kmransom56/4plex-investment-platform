#!/usr/bin/env python3
"""
Comprehensive Integration Test for 4-plex Investment Platform
Tests complete workflow from property discovery through analysis and reporting
"""

import os
import sys
import json
import logging
import asyncio
import tempfile
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import traceback

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all our modules
from models import Property, PropertyAnalysis, FinancialMetrics, ProcessingJob
from database.connection import DatabaseManager
from financial_calculations import FinancialCalculator
from document_processing import DocumentProcessor
from property_manager import PropertyManager
from status_system import StatusSystem, StatusType, Priority, JobStatusTracker
from export_system import ExportSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationTestSuite:
    """Comprehensive integration test suite"""
    
    def __init__(self):
        self.test_config = {
            'database': {
                'type': 'sqlite',
                'path': ':memory:'  # In-memory database for testing
            },
            'financial_assumptions': {
                'hold_period': 5,
                'exit_cap_rate': 0.065,
                'annual_rent_growth': 0.03,
                'annual_expense_growth': 0.025,
                'vacancy_rate': 0.05,
                'management_fee': 0.05,
                'capital_reserve': 0.02,
                'discount_rate': 0.10
            },
            'processing': {
                'max_file_size_mb': 50,
                'enable_async': True,
                'max_workers': 2,
                'enable_caching': False  # Disable for testing
            },
            'export': {
                'output_dir': tempfile.mkdtemp(),
                'max_export_age_days': 7
            },
            'status_system': {
                'max_history': 100,
                'cleanup_interval_minutes': 1
            },
            'websocket': {
                'enabled': False  # Disable WebSocket for testing
            }
        }
        
        self.test_results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'failures': [],
            'start_time': datetime.now(),
            'end_time': None
        }
        
        # Initialize components
        self.db_manager = None
        self.financial_calculator = None
        self.document_processor = None
        self.property_manager = None
        self.status_system = None
        self.export_system = None
        
        # Test data
        self.test_property_id = None
        self.test_analysis_id = None
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        
        logger.info("=" * 80)
        logger.info("STARTING 4-PLEX INVESTMENT PLATFORM INTEGRATION TESTS")
        logger.info("=" * 80)
        
        try:
            # Initialize all components
            await self.setup_test_environment()
            
            # Run tests in order
            await self.test_database_operations()
            await self.test_financial_calculations()
            await self.test_property_management()
            await self.test_document_processing_simulation()
            await self.test_status_system()
            await self.test_export_system()
            await self.test_complete_workflow()
            
            # Cleanup
            await self.cleanup_test_environment()
            
        except Exception as e:
            logger.error(f"Critical error during testing: {str(e)}")
            self.test_results['failures'].append({
                'test': 'setup_or_critical_error',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        
        # Finalize results
        self.test_results['end_time'] = datetime.now()
        self.test_results['total_duration'] = (
            self.test_results['end_time'] - self.test_results['start_time']
        ).total_seconds()
        
        # Print summary
        self.print_test_summary()
        
        return self.test_results
    
    async def setup_test_environment(self):
        """Initialize all system components for testing"""
        
        logger.info("Setting up test environment...")
        
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(self.test_config['database'])
            logger.info("✅ Database manager initialized")
            
            # Initialize financial calculator
            self.financial_calculator = FinancialCalculator(self.test_config['financial_assumptions'])
            logger.info("✅ Financial calculator initialized")
            
            # Initialize document processor
            self.document_processor = DocumentProcessor(self.test_config)
            logger.info("✅ Document processor initialized")
            
            # Initialize property manager
            self.property_manager = PropertyManager(self.test_config)
            logger.info("✅ Property manager initialized")
            
            # Initialize status system
            self.status_system = StatusSystem(self.test_config)
            await self.status_system.start()
            logger.info("✅ Status system initialized")
            
            # Initialize export system
            self.export_system = ExportSystem(self.test_config)
            logger.info("✅ Export system initialized")
            
            logger.info("Test environment setup complete!")
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {str(e)}")
            raise
    
    async def test_database_operations(self):
        """Test database CRUD operations"""
        
        logger.info("\n" + "-" * 60)
        logger.info("TESTING DATABASE OPERATIONS")
        logger.info("-" * 60)
        
        # Test property creation
        await self.run_test("create_test_property", self._test_create_property)
        
        # Test property retrieval
        await self.run_test("retrieve_property", self._test_retrieve_property)
        
        # Test property update
        await self.run_test("update_property", self._test_update_property)
        
        # Test property listing
        await self.run_test("list_properties", self._test_list_properties)
    
    async def test_financial_calculations(self):
        """Test financial calculation engine"""
        
        logger.info("\n" + "-" * 60)
        logger.info("TESTING FINANCIAL CALCULATIONS")
        logger.info("-" * 60)
        
        await self.run_test("irr_calculation", self._test_irr_calculation)
        await self.run_test("cap_rate_calculation", self._test_cap_rate_calculation)
        await self.run_test("viability_score", self._test_viability_score_calculation)
        await self.run_test("comprehensive_analysis", self._test_comprehensive_analysis)
    
    async def test_property_management(self):
        """Test property management operations"""
        
        logger.info("\n" + "-" * 60)
        logger.info("TESTING PROPERTY MANAGEMENT")
        logger.info("-" * 60)
        
        await self.run_test("property_crud", self._test_property_crud_operations)
        await self.run_test("portfolio_summary", self._test_portfolio_summary)
        await self.run_test("investment_opportunities", self._test_investment_opportunities)
    
    async def test_document_processing_simulation(self):
        """Test document processing (simulated)"""
        
        logger.info("\n" + "-" * 60)
        logger.info("TESTING DOCUMENT PROCESSING (SIMULATED)")
        logger.info("-" * 60)
        
        await self.run_test("document_validation", self._test_document_validation)
        await self.run_test("simulated_processing", self._test_simulated_document_processing)
    
    async def test_status_system(self):
        """Test real-time status system"""
        
        logger.info("\n" + "-" * 60)
        logger.info("TESTING STATUS SYSTEM")
        logger.info("-" * 60)
        
        await self.run_test("status_publishing", self._test_status_publishing)
        await self.run_test("status_subscription", self._test_status_subscription)
        await self.run_test("job_status_tracking", self._test_job_status_tracking)
    
    async def test_export_system(self):
        """Test export and reporting system"""
        
        logger.info("\n" + "-" * 60)
        logger.info("TESTING EXPORT SYSTEM")
        logger.info("-" * 60)
        
        await self.run_test("json_export", self._test_json_export)
        await self.run_test("portfolio_export", self._test_portfolio_export)
        await self.run_test("export_cleanup", self._test_export_cleanup)
    
    async def test_complete_workflow(self):
        """Test complete end-to-end workflow"""
        
        logger.info("\n" + "-" * 60)
        logger.info("TESTING COMPLETE WORKFLOW")
        logger.info("-" * 60)
        
        await self.run_test("end_to_end_workflow", self._test_complete_workflow)
    
    # Individual Test Methods
    
    async def _test_create_property(self):
        """Test creating a property"""
        
        property_data = {
            'address': '123 Test Street',
            'city': 'Test City',
            'state': 'TS',
            'zip_code': '12345',
            'property_type': '4plex',
            'units': 4,
            'total_sqft': 3200,
            'year_built': 1985,
            'foreclosure_stage': 'discovered',
            'outstanding_debt': 280000,
            'estimated_value': 420000,
            'minimum_bid': 250000,
            'discovery_date': datetime.now(),
            'case_number': 'TEST-2024-001'
        }
        
        created_property = await self.property_manager.create_property(property_data)
        
        assert created_property['id'] is not None, "Property ID should be generated"
        assert created_property['address'] == '123 Test Street', "Address should match"
        assert created_property['foreclosure_stage'] == 'discovered', "Stage should be discovered"
        
        # Store for later tests
        self.test_property_id = created_property['id']
        
        logger.info(f"✅ Created test property: {self.test_property_id}")
    
    async def _test_retrieve_property(self):
        """Test retrieving a property"""
        
        assert self.test_property_id is not None, "Test property must exist"
        
        property_data = await self.property_manager.get_property(self.test_property_id)
        
        assert property_data is not None, "Property should be found"
        assert property_data['id'] == self.test_property_id, "Property ID should match"
        assert property_data['address'] == '123 Test Street', "Address should match"
        
        logger.info("✅ Successfully retrieved test property")
    
    async def _test_update_property(self):
        """Test updating a property"""
        
        assert self.test_property_id is not None, "Test property must exist"
        
        updates = {
            'foreclosure_stage': 'analyzing',
            'estimated_value': 450000,
            'notes': 'Updated during integration test'
        }
        
        updated_property = await self.property_manager.update_property(self.test_property_id, updates)
        
        assert updated_property['foreclosure_stage'] == 'analyzing', "Stage should be updated"
        assert updated_property['estimated_value'] == 450000, "Value should be updated"
        assert updated_property['last_modified'] is not None, "Last modified should be set"
        
        logger.info("✅ Successfully updated test property")
    
    async def _test_list_properties(self):
        """Test listing properties"""
        
        # Create a few more test properties
        for i in range(3):
            property_data = {
                'address': f'{100 + i} Test Avenue',
                'city': 'Test City',
                'state': 'TS',
                'property_type': '4plex',
                'foreclosure_stage': 'discovered',
                'outstanding_debt': 200000 + (i * 10000)
            }
            await self.property_manager.create_property(property_data)
        
        # Test listing
        result = await self.property_manager.list_properties(limit=10)
        
        assert 'properties' in result, "Should return properties list"
        assert result['pagination']['total_count'] >= 4, "Should have at least 4 properties"
        assert len(result['properties']) >= 4, "Should return at least 4 properties"
        
        logger.info(f"✅ Listed {len(result['properties'])} properties")
    
    async def _test_irr_calculation(self):
        """Test IRR calculation"""
        
        # Test cash flows: initial investment followed by annual returns
        cash_flows = [-100000, 15000, 18000, 21000, 24000, 150000]
        
        irr = self.financial_calculator.calculate_irr(cash_flows)
        
        assert 0.1 <= irr <= 0.3, f"IRR should be reasonable: {irr:.2%}"
        
        logger.info(f"✅ IRR calculation: {irr:.2%}")
    
    async def _test_cap_rate_calculation(self):
        """Test cap rate calculation"""
        
        noi = 42000
        purchase_price = 350000
        
        cap_rate = self.financial_calculator.calculate_cap_rate(noi, purchase_price)
        
        expected_cap_rate = noi / purchase_price
        assert abs(cap_rate - expected_cap_rate) < 0.001, "Cap rate calculation should be accurate"
        
        logger.info(f"✅ Cap rate calculation: {cap_rate:.2%}")
    
    async def _test_viability_score_calculation(self):
        """Test viability score calculation"""
        
        property_data = {
            'noi': 45000,
            'purchase_price': 400000,
            'cash_flows': [-80000, 12000, 15000, 18000, 21000, 120000],
            'debt_service': 28000,
            'total_units': 4,
            'year_built': 1995
        }
        
        viability_result = self.financial_calculator.calculate_viability_score(property_data)
        
        assert 'score' in viability_result, "Should return viability score"
        assert 'grade' in viability_result, "Should return investment grade"
        assert 0 <= viability_result['score'] <= 1, "Score should be between 0 and 1"
        assert viability_result['grade'] in ['A', 'B', 'C', 'D'], "Grade should be valid"
        
        logger.info(f"✅ Viability score: {viability_result['score']:.3f} (Grade {viability_result['grade']})")
    
    async def _test_comprehensive_analysis(self):
        """Test comprehensive financial analysis"""
        
        financial_inputs = {
            'gross_monthly_income': 4500,
            'annual_operating_expenses': 18000,
            'purchase_price': 380000,
            'down_payment': 76000,
            'loan_amount': 304000,
            'interest_rate': 0.065,
            'loan_term': 30,
            'total_units': 4
        }
        
        analysis = self.financial_calculator.calculate_comprehensive_analysis(financial_inputs)
        
        assert 'noi' in analysis, "Should calculate NOI"
        assert 'cap_rate' in analysis, "Should calculate cap rate"
        assert 'cash_on_cash_return' in analysis, "Should calculate cash-on-cash return"
        assert 'dscr' in analysis, "Should calculate DSCR"
        
        logger.info("✅ Comprehensive financial analysis completed")
    
    async def _test_property_crud_operations(self):
        """Test property CRUD operations through property manager"""
        
        # Create
        property_data = {
            'address': '456 Manager Test St',
            'city': 'Manager City',
            'state': 'MC',
            'property_type': '4plex',
            'foreclosure_stage': 'discovered'
        }
        
        created = await self.property_manager.create_property(property_data)
        property_id = created['id']
        
        # Read
        retrieved = await self.property_manager.get_property(property_id)
        assert retrieved['address'] == '456 Manager Test St'
        
        # Update
        updated = await self.property_manager.update_property(property_id, {
            'foreclosure_stage': 'analyzed',
            'investment_score': 0.75
        })
        assert updated['foreclosure_stage'] == 'analyzed'
        assert updated['investment_score'] == 0.75
        
        # Delete (soft)
        deleted = await self.property_manager.delete_property(property_id, hard_delete=False)
        assert deleted is True
        
        logger.info("✅ Property CRUD operations completed")
    
    async def _test_portfolio_summary(self):
        """Test portfolio summary generation"""
        
        summary = await self.property_manager.get_portfolio_summary()
        
        assert 'property_counts' in summary, "Should include property counts"
        assert 'portfolio_metrics' in summary, "Should include portfolio metrics"
        assert 'summary_generated' in summary, "Should include generation timestamp"
        
        logger.info(f"✅ Portfolio summary generated with {summary['portfolio_metrics'].get('total_properties', 0)} properties")
    
    async def _test_investment_opportunities(self):
        """Test investment opportunity identification"""
        
        opportunities = await self.property_manager.get_investment_opportunities(
            min_grade='C',  # Lower threshold for testing
            max_results=10
        )
        
        assert isinstance(opportunities, list), "Should return list of opportunities"
        
        logger.info(f"✅ Found {len(opportunities)} investment opportunities")
    
    async def _test_document_validation(self):
        """Test document validation"""
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b"Test document content")
            temp_path = temp_file.name
        
        try:
            validation = self.document_processor.validate_file(temp_path)
            
            assert validation['valid'] is True, "File should be valid"
            assert validation['size_mb'] > 0, "Should calculate file size"
            
            logger.info("✅ Document validation working")
            
        finally:
            os.unlink(temp_path)
    
    async def _test_simulated_document_processing(self):
        """Test document processing with simulated data"""
        
        # Create simulated analysis data
        simulated_analysis = {
            'id': f"analysis_{self.test_property_id}",
            'property_id': self.test_property_id,
            'analysis_date': datetime.now(),
            'investment_grade': 'B',
            'viability_score': 0.72,
            'confidence_score': 0.85,
            'financial_metrics': {
                'noi': 42000,
                'cap_rate': 0.105,
                'irr': 0.145,
                'cash_on_cash_return': 0.125,
                'dscr': 1.45,
                'ltv_ratio': 0.80,
                'gross_income': 54000,
                'debt_service': 28800,
                'cash_flow': 13200,
                'equity_multiple': 2.15,
                'total_return': 0.156
            },
            'risk_factors': [
                'Property age may require capital improvements',
                'Local market conditions require monitoring'
            ],
            'ai_insights': {
                'recommendations': [
                    'Strong investment opportunity with solid fundamentals',
                    'Consider negotiating purchase price for improved returns'
                ],
                'key_strengths': [
                    'Good cash flow potential',
                    'Strong rental market area'
                ],
                'key_concerns': [
                    'Property age',
                    'Market competition'
                ]
            },
            'processing_metadata': {
                'files_processed': ['simulated_rent_roll', 'simulated_t12'],
                'processing_time_seconds': 45.2,
                'ai_enabled': False
            },
            'document_sources': ['simulated_data']
        }
        
        # Save the simulated analysis
        saved_analysis = self.db_manager.save_analysis(simulated_analysis)
        self.test_analysis_id = saved_analysis['id']
        
        # Update property with analysis
        await self.property_manager.update_property(self.test_property_id, {
            'foreclosure_stage': 'analyzed',
            'investment_score': 0.72,
            'last_analysis_date': datetime.now()
        })
        
        logger.info("✅ Simulated document processing and analysis completed")
    
    async def _test_status_publishing(self):
        """Test status system publishing"""
        
        # Publish various status updates
        status_id = self.status_system.publish_status(
            StatusType.JOB_STARTED,
            "Integration test job started",
            Priority.NORMAL,
            property_id=self.test_property_id,
            job_id="test_job_123"
        )
        
        assert status_id is not None, "Should return status ID"
        
        # Publish progress update
        self.status_system.publish_status(
            StatusType.JOB_PROGRESS,
            "Processing documents",
            Priority.NORMAL,
            property_id=self.test_property_id,
            job_id="test_job_123",
            progress=50
        )
        
        # Publish completion
        self.status_system.publish_status(
            StatusType.JOB_COMPLETED,
            "Analysis completed successfully",
            Priority.HIGH,
            property_id=self.test_property_id,
            job_id="test_job_123",
            progress=100
        )
        
        logger.info("✅ Status publishing working")
    
    async def _test_status_subscription(self):
        """Test status system subscription"""
        
        received_updates = []
        
        def callback(status_update):
            received_updates.append(status_update)
        
        # Subscribe to updates
        subscription_id = self.status_system.subscribe(
            callback=callback,
            filters={'property_ids': [self.test_property_id]}
        )
        
        # Publish a test update
        self.status_system.publish_status(
            StatusType.SYSTEM_STATUS,
            "Test subscription message",
            Priority.NORMAL,
            property_id=self.test_property_id
        )
        
        # Give some time for processing
        await asyncio.sleep(0.1)
        
        # Check if update was received
        assert len(received_updates) > 0, "Should receive status updates"
        
        # Unsubscribe
        success = self.status_system.unsubscribe(subscription_id)
        assert success is True, "Should successfully unsubscribe"
        
        logger.info("✅ Status subscription working")
    
    async def _test_job_status_tracking(self):
        """Test job status tracking helper"""
        
        job_tracker = JobStatusTracker(
            self.status_system,
            "tracker_test_job",
            self.test_property_id
        )
        
        # Test progress updates
        job_tracker.update_progress(25, "Starting analysis")
        job_tracker.update_progress(50, "Processing documents")
        job_tracker.update_progress(75, "Generating insights")
        
        # Test milestone logging
        job_tracker.log_milestone("Document processing completed")
        
        # Test completion
        job_tracker.mark_completed("Analysis completed successfully")
        
        # Get job status stream
        job_updates = self.status_system.get_job_status_stream("tracker_test_job")
        
        assert len(job_updates) >= 4, "Should have multiple job updates"
        
        logger.info("✅ Job status tracking working")
    
    async def _test_json_export(self):
        """Test JSON export functionality"""
        
        assert self.test_property_id is not None, "Test property must exist"
        assert self.test_analysis_id is not None, "Test analysis must exist"
        
        # Export property analysis
        export_result = await self.export_system.export_property_analysis(
            self.test_property_id,
            self.test_analysis_id,
            export_formats=['json'],
            include_charts=False,
            include_raw_data=True
        )
        
        assert export_result['status'] == 'completed', "Export should be completed"
        assert export_result['total_files'] >= 1, "Should generate at least 1 file"
        assert len(export_result['files']) >= 1, "Should have file information"
        
        # Verify JSON file exists
        json_file = next((f for f in export_result['files'] if f['type'] == 'json'), None)
        assert json_file is not None, "Should have JSON export file"
        assert os.path.exists(json_file['path']), "JSON file should exist"
        
        # Verify JSON content
        with open(json_file['path'], 'r') as f:
            json_data = json.load(f)
        
        assert 'property' in json_data, "Should include property data"
        assert 'analysis' in json_data, "Should include analysis data"
        
        logger.info("✅ JSON export working")
    
    async def _test_portfolio_export(self):
        """Test portfolio export"""
        
        export_result = await self.export_system.export_portfolio_summary(
            export_formats=['json'],
            include_property_details=True
        )
        
        assert export_result['status'] == 'completed', "Portfolio export should be completed"
        assert export_result['property_count'] > 0, "Should include properties"
        
        logger.info(f"✅ Portfolio export completed with {export_result['property_count']} properties")
    
    async def _test_export_cleanup(self):
        """Test export cleanup functionality"""
        
        # Create some old test files
        old_export_dir = os.path.join(self.export_system.export_dir, 'old_test_export')
        os.makedirs(old_export_dir, exist_ok=True)
        
        old_file = os.path.join(old_export_dir, 'old_test_file.txt')
        with open(old_file, 'w') as f:
            f.write("Old test file")
        
        # Set file modification time to old date
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(old_export_dir, (old_time, old_time))
        
        # Run cleanup
        cleanup_result = await self.export_system.cleanup_old_exports(days_threshold=7)
        
        assert cleanup_result['exports_cleaned'] >= 1, "Should clean up old exports"
        assert not os.path.exists(old_export_dir), "Old export directory should be removed"
        
        logger.info("✅ Export cleanup working")
    
    async def _test_complete_workflow(self):
        """Test complete end-to-end workflow"""
        
        logger.info("Testing complete workflow: Discovery → Analysis → Export")
        
        # Step 1: Create a new property (Discovery)
        property_data = {
            'address': '789 Complete Workflow Ave',
            'city': 'Workflow City', 
            'state': 'WF',
            'property_type': '4plex',
            'units': 4,
            'foreclosure_stage': 'discovered',
            'outstanding_debt': 320000,
            'estimated_value': 480000
        }
        
        workflow_property = await self.property_manager.create_property(property_data)
        workflow_property_id = workflow_property['id']
        
        logger.info(f"Step 1: Property discovered - {workflow_property_id}")
        
        # Step 2: Create simulated analysis
        analysis_data = {
            'id': f"workflow_analysis_{workflow_property_id}",
            'property_id': workflow_property_id,
            'analysis_date': datetime.now(),
            'investment_grade': 'A',
            'viability_score': 0.85,
            'confidence_score': 0.90,
            'financial_metrics': {
                'noi': 48000,
                'cap_rate': 0.12,
                'irr': 0.18,
                'cash_on_cash_return': 0.15,
                'dscr': 1.6,
                'gross_income': 60000,
                'debt_service': 32000,
                'cash_flow': 16000
            },
            'risk_factors': ['Minimal risk factors identified'],
            'ai_insights': {
                'recommendations': ['Excellent investment opportunity'],
                'key_strengths': ['High cash flow', 'Strong fundamentals']
            },
            'document_sources': ['workflow_test']
        }
        
        saved_analysis = self.db_manager.save_analysis(analysis_data)
        workflow_analysis_id = saved_analysis['id']
        
        # Update property stage
        await self.property_manager.update_property(workflow_property_id, {
            'foreclosure_stage': 'opportunity',
            'investment_score': 0.85
        })
        
        logger.info(f"Step 2: Analysis completed - Grade A, Score 85%")
        
        # Step 3: Generate reports
        export_result = await self.export_system.export_property_analysis(
            workflow_property_id,
            workflow_analysis_id,
            export_formats=['json', 'csv'],
            include_charts=False
        )
        
        assert export_result['status'] == 'completed', "Export should succeed"
        assert export_result['total_files'] >= 2, "Should generate multiple files"
        
        logger.info(f"Step 3: Reports generated - {export_result['total_files']} files")
        
        # Step 4: Verify opportunity appears in investment opportunities
        opportunities = await self.property_manager.get_investment_opportunities(min_grade='A')
        
        workflow_opportunity = next(
            (opp for opp in opportunities if opp['id'] == workflow_property_id),
            None
        )
        
        assert workflow_opportunity is not None, "Property should appear in opportunities"
        assert workflow_opportunity.get('financial_summary', {}).get('investment_grade') == 'A'
        
        logger.info("Step 4: Property confirmed as investment opportunity")
        
        logger.info("✅ Complete workflow test passed!")
    
    async def cleanup_test_environment(self):
        """Clean up test environment"""
        
        logger.info("Cleaning up test environment...")
        
        try:
            # Stop status system
            if self.status_system:
                await self.status_system.stop()
            
            # Clean up export directory
            if hasattr(self.export_system, 'export_dir'):
                import shutil
                if os.path.exists(self.export_system.export_dir):
                    shutil.rmtree(self.export_system.export_dir)
            
            logger.info("✅ Test environment cleaned up")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
    
    # Test Utility Methods
    
    async def run_test(self, test_name: str, test_func):
        """Run a single test with error handling"""
        
        self.test_results['tests_run'] += 1
        
        try:
            await test_func()
            self.test_results['tests_passed'] += 1
            logger.info(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            self.test_results['tests_failed'] += 1
            self.test_results['failures'].append({
                'test': test_name,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            logger.error(f"❌ {test_name}: FAILED - {str(e)}")
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        
        logger.info("\n" + "=" * 80)
        logger.info("INTEGRATION TEST SUMMARY")
        logger.info("=" * 80)
        
        logger.info(f"Total Tests Run: {self.test_results['tests_run']}")
        logger.info(f"Tests Passed: {self.test_results['tests_passed']}")
        logger.info(f"Tests Failed: {self.test_results['tests_failed']}")
        logger.info(f"Success Rate: {(self.test_results['tests_passed'] / self.test_results['tests_run'] * 100):.1f}%")
        logger.info(f"Total Duration: {self.test_results['total_duration']:.2f} seconds")
        
        if self.test_results['failures']:
            logger.info("\n" + "-" * 60)
            logger.info("FAILED TESTS:")
            logger.info("-" * 60)
            
            for failure in self.test_results['failures']:
                logger.error(f"❌ {failure['test']}: {failure['error']}")
        
        overall_status = "PASSED" if self.test_results['tests_failed'] == 0 else "FAILED"
        status_symbol = "✅" if overall_status == "PASSED" else "❌"
        
        logger.info(f"\n{status_symbol} OVERALL STATUS: {overall_status}")
        logger.info("=" * 80)

async def main():
    """Main test runner"""
    
    test_suite = IntegrationTestSuite()
    results = await test_suite.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results['tests_failed'] == 0 else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())