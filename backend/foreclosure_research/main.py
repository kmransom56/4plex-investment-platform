"""
4-Plex Foreclosure Research AI System - Main Application
Multi-agent orchestration system for Georgia county property research
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List
import signal

from crewai import Crew
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import Settings
from services.database.connection import initialize_databases, get_database_health
from agents.data_collection.foreclosure_agent import ForeclosureDataAgent
from agents.data_collection.code_violation_agent import CodeViolationAgent
from agents.data_collection.tax_lien_agent import TaxLienAgent
from agents.property_analysis.characteristics_agent import PropertyCharacteristicsAgent
from agents.property_analysis.market_analysis_agent import MarketAnalysisAgent
from agents.property_analysis.legal_compliance_agent import LegalComplianceAgent
from agents.automation.monitoring_agent import MonitoringAgent
from agents.automation.alert_agent import AlertAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('4plex_research.log')
    ]
)

logger = logging.getLogger(__name__)


class ForeclosureResearchSystem:
    """Main orchestration system for 4-plex foreclosure research"""
    
    def __init__(self):
        self.settings = Settings()
        self.scheduler = AsyncIOScheduler()
        self.agents = {}
        self.crews = {}
        self.is_running = False
        
        # System status
        self.start_time = None
        self.total_properties_processed = 0
        self.last_collection_time = None
        
    async def initialize(self):
        """Initialize the system and all components"""
        logger.info("🚀 Initializing 4-Plex Foreclosure Research System")
        
        try:
            # Initialize databases
            logger.info("📊 Initializing database connections...")
            initialize_databases(self.settings)
            
            # Verify database health
            health = get_database_health()
            if not all(health.values()):
                logger.error(f"Database health check failed: {health}")
                raise RuntimeError("Database initialization failed")
                
            logger.info("✅ Database connections established")
            
            # Initialize agents
            await self._initialize_agents()
            
            # Setup crews for collaborative tasks
            await self._setup_crews()
            
            # Setup scheduled tasks
            self._setup_scheduler()
            
            logger.info("🎯 System initialization complete")
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            raise
            
    async def _initialize_agents(self):
        """Initialize all AI agents"""
        logger.info("🤖 Initializing AI agents...")
        
        try:
            # Data Collection Agents
            self.agents['foreclosure'] = ForeclosureDataAgent(self.settings)
            self.agents['code_violation'] = CodeViolationAgent(self.settings) 
            self.agents['tax_lien'] = TaxLienAgent(self.settings)
            
            # Property Analysis Agents
            self.agents['characteristics'] = PropertyCharacteristicsAgent(self.settings)
            self.agents['market_analysis'] = MarketAnalysisAgent(self.settings)
            self.agents['legal_compliance'] = LegalComplianceAgent(self.settings)
            
            # Automation Agents
            self.agents['monitoring'] = MonitoringAgent(self.settings)
            self.agents['alert'] = AlertAgent(self.settings)
            
            logger.info(f"✅ Initialized {len(self.agents)} AI agents")
            
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            raise
            
    async def _setup_crews(self):
        """Setup CrewAI crews for collaborative tasks"""
        logger.info("👥 Setting up agent crews...")
        
        # Data Collection Crew
        self.crews['data_collection'] = Crew(
            agents=[
                self.agents['foreclosure'].agent,
                self.agents['code_violation'].agent,
                self.agents['tax_lien'].agent
            ],
            verbose=True,
            memory=True
        )
        
        # Property Analysis Crew
        self.crews['property_analysis'] = Crew(
            agents=[
                self.agents['characteristics'].agent,
                self.agents['market_analysis'].agent,
                self.agents['legal_compliance'].agent
            ],
            verbose=True,
            memory=True
        )
        
        # Monitoring Crew
        self.crews['monitoring'] = Crew(
            agents=[
                self.agents['monitoring'].agent,
                self.agents['alert'].agent
            ],
            verbose=True,
            memory=True
        )
        
        logger.info(f"✅ Setup {len(self.crews)} agent crews")
        
    def _setup_scheduler(self):
        """Setup scheduled tasks"""
        logger.info("⏰ Setting up scheduled tasks...")
        
        # Data collection schedules
        self.scheduler.add_job(
            self.run_foreclosure_collection,
            CronTrigger.from_crontab(self.settings.FORECLOSURE_DATA_SCHEDULE),
            id='foreclosure_collection',
            name='Daily Foreclosure Data Collection'
        )
        
        self.scheduler.add_job(
            self.run_code_violation_collection,
            CronTrigger.from_crontab(self.settings.CODE_VIOLATION_SCHEDULE),
            id='code_violation_collection',
            name='Daily Code Violation Collection'
        )
        
        self.scheduler.add_job(
            self.run_tax_lien_collection,
            CronTrigger.from_crontab(self.settings.TAX_LIEN_SCHEDULE),
            id='tax_lien_collection',
            name='Daily Tax Lien Collection'
        )
        
        # Analysis schedule
        self.scheduler.add_job(
            self.run_market_analysis,
            CronTrigger.from_crontab(self.settings.MARKET_ANALYSIS_SCHEDULE),
            id='market_analysis',
            name='Weekly Market Analysis'
        )
        
        # System monitoring
        self.scheduler.add_job(
            self.run_system_monitoring,
            CronTrigger(minute='*/15'),  # Every 15 minutes
            id='system_monitoring',
            name='System Health Monitoring'
        )
        
        logger.info("✅ Scheduled tasks configured")
        
    async def start(self):
        """Start the research system"""
        logger.info("🎬 Starting 4-Plex Foreclosure Research System")
        
        try:
            if not self.agents:
                await self.initialize()
                
            self.is_running = True
            self.start_time = datetime.utcnow()
            
            # Start scheduler
            self.scheduler.start()
            logger.info("⏰ Scheduler started")
            
            # Run initial data collection
            logger.info("🔄 Running initial data collection...")
            await self.run_initial_collection()
            
            logger.info("✅ System is running - Press Ctrl+C to stop")
            
            # Keep system running
            while self.is_running:
                await asyncio.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested by user")
            await self.shutdown()
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            await self.shutdown()
            
    async def shutdown(self):
        """Gracefully shutdown the system"""
        logger.info("🔄 Shutting down system...")
        
        self.is_running = False
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("⏰ Scheduler stopped")
            
        # Generate shutdown report
        uptime = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
        logger.info(f"""
        📊 System Statistics:
        - Uptime: {uptime:.0f} seconds
        - Properties processed: {self.total_properties_processed}
        - Last collection: {self.last_collection_time}
        """)
        
        logger.info("✅ System shutdown complete")
        
    async def run_initial_collection(self):
        """Run initial data collection for all counties"""
        logger.info("🔍 Starting initial data collection...")
        
        try:
            # Collect data from all counties
            counties = ['fulton', 'dekalb', 'clayton', 'atlanta', 'cobb']
            
            for county in counties:
                logger.info(f"📍 Collecting data for {county.title()} County")
                
                # Run data collection crew
                tasks = [
                    self.agents['foreclosure'].create_task(
                        description=f"Collect foreclosure data for {county} county",
                        expected_output="List of 4-plex properties in foreclosure"
                    ),
                    self.agents['code_violation'].create_task(
                        description=f"Collect code violation data for {county} county", 
                        expected_output="List of 4-plex properties with code violations"
                    ),
                    self.agents['tax_lien'].create_task(
                        description=f"Collect tax lien data for {county} county",
                        expected_output="List of 4-plex properties with tax liens"
                    )
                ]
                
                # Execute data collection
                crew_result = await self._execute_crew_tasks(self.crews['data_collection'], tasks)
                
                if crew_result:
                    logger.info(f"✅ {county.title()} County collection completed")
                else:
                    logger.warning(f"⚠️ {county.title()} County collection had issues")
                    
            self.last_collection_time = datetime.utcnow()
            logger.info("✅ Initial data collection complete")
            
        except Exception as e:
            logger.error(f"Initial collection failed: {e}")
            
    async def run_foreclosure_collection(self):
        """Scheduled foreclosure data collection"""
        logger.info("🏠 Running scheduled foreclosure data collection")
        
        try:
            task_data = {'task_id': f"foreclosure_{int(datetime.utcnow().timestamp())}", 'county': 'all'}
            result = await self.agents['foreclosure'].execute_task(task_data)
            
            if result.success:
                self.total_properties_processed += result.records_processed
                logger.info(f"✅ Foreclosure collection: {result.records_processed} properties processed")
                
                # Trigger analysis for new properties
                if result.records_processed > 0:
                    await self.run_property_analysis(result.data.get('properties', []))
            else:
                logger.error(f"❌ Foreclosure collection failed: {result.message}")
                
        except Exception as e:
            logger.error(f"Scheduled foreclosure collection error: {e}")
            
    async def run_code_violation_collection(self):
        """Scheduled code violation data collection"""
        logger.info("🚨 Running scheduled code violation data collection")
        
        try:
            task_data = {'task_id': f"code_violation_{int(datetime.utcnow().timestamp())}", 'county': 'all'}
            result = await self.agents['code_violation'].execute_task(task_data)
            
            if result.success:
                self.total_properties_processed += result.records_processed
                logger.info(f"✅ Code violation collection: {result.records_processed} properties processed")
            else:
                logger.error(f"❌ Code violation collection failed: {result.message}")
                
        except Exception as e:
            logger.error(f"Scheduled code violation collection error: {e}")
            
    async def run_tax_lien_collection(self):
        """Scheduled tax lien data collection"""
        logger.info("💰 Running scheduled tax lien data collection")
        
        try:
            task_data = {'task_id': f"tax_lien_{int(datetime.utcnow().timestamp())}", 'county': 'all'}
            result = await self.agents['tax_lien'].execute_task(task_data)
            
            if result.success:
                self.total_properties_processed += result.records_processed
                logger.info(f"✅ Tax lien collection: {result.records_processed} properties processed")
            else:
                logger.error(f"❌ Tax lien collection failed: {result.message}")
                
        except Exception as e:
            logger.error(f"Scheduled tax lien collection error: {e}")
            
    async def run_market_analysis(self):
        """Scheduled market analysis"""
        logger.info("📈 Running scheduled market analysis")
        
        try:
            task_data = {'task_id': f"market_analysis_{int(datetime.utcnow().timestamp())}"}
            result = await self.agents['market_analysis'].execute_task(task_data)
            
            if result.success:
                logger.info(f"✅ Market analysis completed: {result.records_processed} properties analyzed")
            else:
                logger.error(f"❌ Market analysis failed: {result.message}")
                
        except Exception as e:
            logger.error(f"Scheduled market analysis error: {e}")
            
    async def run_property_analysis(self, properties: List[Dict[str, Any]]):
        """Run comprehensive property analysis"""
        logger.info(f"🔬 Running analysis for {len(properties)} properties")
        
        try:
            for property_data in properties:
                # Run characteristics analysis
                char_result = await self.agents['characteristics'].execute_task({
                    'task_id': f"char_{property_data.get('property_id')}",
                    'property_data': property_data
                })
                
                # Run market analysis
                market_result = await self.agents['market_analysis'].execute_task({
                    'task_id': f"market_{property_data.get('property_id')}",
                    'property_data': property_data
                })
                
                # Run legal compliance check
                legal_result = await self.agents['legal_compliance'].execute_task({
                    'task_id': f"legal_{property_data.get('property_id')}",
                    'property_data': property_data
                })
                
                # Generate alerts for high-value opportunities
                if all([char_result.success, market_result.success, legal_result.success]):
                    await self._check_investment_opportunity(property_data, {
                        'characteristics': char_result,
                        'market': market_result,
                        'legal': legal_result
                    })
                    
        except Exception as e:
            logger.error(f"Property analysis error: {e}")
            
    async def run_system_monitoring(self):
        """System health monitoring"""
        try:
            task_data = {'task_id': f"monitoring_{int(datetime.utcnow().timestamp())}"}
            result = await self.agents['monitoring'].execute_task(task_data)
            
            if not result.success:
                logger.warning(f"System monitoring detected issues: {result.message}")
                
        except Exception as e:
            logger.error(f"System monitoring error: {e}")
            
    async def _execute_crew_tasks(self, crew: Crew, tasks: List) -> bool:
        """Execute tasks using CrewAI crew"""
        try:
            # This would be implemented based on CrewAI's task execution API
            # For now, we'll simulate crew execution
            for task in tasks:
                # Execute individual agent tasks
                pass
            return True
        except Exception as e:
            logger.error(f"Crew task execution failed: {e}")
            return False
            
    async def _check_investment_opportunity(self, property_data: Dict[str, Any], analyses: Dict[str, Any]):
        """Check if property represents a high-value investment opportunity"""
        try:
            # Calculate investment score based on analyses
            market_data = analyses['market'].data
            legal_data = analyses['legal'].data
            
            score = 0
            reasons = []
            
            # Market factors
            if market_data.get('cap_rate', 0) >= self.settings.MIN_CAP_RATE:
                score += 30
                reasons.append(f"High cap rate: {market_data.get('cap_rate', 0):.2%}")
                
            if market_data.get('cash_flow', 0) >= self.settings.MIN_CASH_FLOW:
                score += 25
                reasons.append(f"Positive cash flow: ${market_data.get('cash_flow', 0):,.0f}")
                
            # Legal factors
            if legal_data.get('clear_title', False):
                score += 20
                reasons.append("Clear title")
                
            if legal_data.get('zoning_compliant', False):
                score += 15
                reasons.append("Zoning compliant")
                
            # Price factors
            if property_data.get('amount_owed', 0) < self.settings.MAX_PRICE:
                score += 10
                reasons.append("Below price threshold")
                
            # Generate high-priority alert if score is high
            if score >= 70:
                await self.agents['alert'].execute_task({
                    'task_id': f"alert_{property_data.get('property_id')}",
                    'alert_type': 'high_value_opportunity',
                    'property_data': property_data,
                    'investment_score': score,
                    'reasons': reasons
                })
                
        except Exception as e:
            logger.error(f"Investment opportunity check failed: {e}")


# Signal handlers for graceful shutdown
def signal_handler(system: ForeclosureResearchSystem):
    def handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(system.shutdown())
    return handler


async def main():
    """Main application entry point"""
    system = ForeclosureResearchSystem()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler(system))
    signal.signal(signal.SIGTERM, signal_handler(system))
    
    try:
        await system.start()
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the system
    asyncio.run(main())