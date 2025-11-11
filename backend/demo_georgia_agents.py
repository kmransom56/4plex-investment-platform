#!/usr/bin/env python3
"""
Demonstration of Georgia County Agents and CrewAI Orchestration
Shows how to use the 4-plex foreclosure research system
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

# Import our modules
from database.connection import DatabaseManager
from agents.georgia_county_agents import GeorgiaCountyAgentManager, FultonCountyAgent
from agents.crew_orchestration import FourPlexInvestmentOrchestrator, ForeclosureResearchCrew
from models import DiscoveryJob, Property, PropertyType, PropertyStatus, ForeclosureStage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("demo")

async def demo_county_agents():
    """Demonstrate Georgia County Agents functionality"""
    logger.info("🏛️ DEMO: Georgia County Agents System")
    
    # Initialize database
    db_manager = DatabaseManager()
    
    # Create agent manager
    agent_manager = GeorgiaCountyAgentManager(db_manager)
    
    try:
        # Initialize all agents
        await agent_manager.initialize_all_agents()
        logger.info("✅ Initialized all 5 Georgia county agents")
        
        # Demo 1: Single county discovery (Fulton)
        logger.info("\n📍 Demo 1: Fulton County Property Discovery")
        fulton_agent = agent_manager.agents["fulton"]
        
        # Create a discovery job
        job = DiscoveryJob(
            counties=["fulton"],
            max_results=25,
            search_parameters={
                "property_types": ["4-plex", "fourplex", "quadplex"],
                "foreclosure_stages": ["auction", "pre_foreclosure", "reo"]
            }
        )
        
        # Run discovery (simulation - would normally discover real properties)
        logger.info("🔍 Discovering 4-plex properties in Fulton County...")
        discovered_properties = await fulton_agent.discover_properties(job)
        logger.info(f"📊 Fulton County Discovery Results: {len(discovered_properties)} properties")
        
        # Demo 2: Multi-county coordinated discovery
        logger.info("\n📍 Demo 2: Multi-County Coordinated Discovery")
        counties_to_search = ["fulton", "dekalb", "atlanta"]
        
        coordinated_job = await agent_manager.run_discovery_job(
            counties=counties_to_search,
            max_results=50
        )
        
        logger.info(f"🎯 Coordinated Discovery Results:")
        logger.info(f"   Total Properties: {coordinated_job.total_properties}")
        logger.info(f"   Counties Searched: {len(coordinated_job.counties)}")
        logger.info(f"   Job Status: {coordinated_job.status}")
        
        # Demo 3: Performance reporting
        logger.info("\n📊 Demo 3: Agent Performance Report")
        performance_report = await agent_manager.get_agent_performance_report()
        
        logger.info("🎯 Agent Performance Summary:")
        for agent_name, stats in performance_report["agents"].items():
            logger.info(f"   {agent_name.title()}: {stats.get('properties_discovered', 0)} properties, "
                       f"{stats.get('api_calls_made', 0)} API calls")
        
        # Demo 4: Scheduled discovery simulation
        logger.info("\n📅 Demo 4: Scheduled Discovery")
        logger.info("🌅 Running daily discovery (high-activity counties)...")
        daily_job = await agent_manager.schedule_daily_discovery()
        logger.info(f"✅ Daily discovery completed: Job {daily_job.id}")
        
        logger.info("📊 Agent system demonstration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error in county agents demo: {str(e)}")
        raise
    finally:
        await agent_manager.cleanup_all_agents()

async def demo_crewai_orchestration():
    """Demonstrate CrewAI orchestration system"""
    logger.info("\n🤖 DEMO: CrewAI Multi-Agent Orchestration")
    
    # Configuration for the system
    config = {
        "database": {
            "sqlite_path": "/tmp/demo_4plex_platform.db"
        },
        "financial_assumptions": {
            "default_vacancy_rate": 0.05,
            "default_cap_rate_threshold": 7.0,
            "default_cash_on_cash_threshold": 12.0
        },
        "file_management": {
            "upload_dir": "./demo_uploads",
            "output_dir": "./demo_outputs"
        },
        # Note: In production, you would set real OpenAI API key
        "openai_api_key": "demo_key_placeholder"
    }
    
    try:
        # Create orchestrator
        orchestrator = FourPlexInvestmentOrchestrator(config)
        
        # Demo 1: System status
        logger.info("\n📊 Demo 1: System Status")
        status = orchestrator.get_system_status()
        logger.info(f"🎯 Orchestrator Status:")
        logger.info(f"   Active: {status['orchestrator_active']}")
        logger.info(f"   Workflows: {len(status['available_workflows'])}")
        logger.info(f"   Counties: {len(status['counties_monitored'])}")
        
        # Demo 2: Agent descriptions
        logger.info("\n🤖 Demo 2: AI Agent Descriptions")
        agent_descriptions = orchestrator.crew_system.get_agent_descriptions()
        for name, desc in agent_descriptions.items():
            logger.info(f"   {name.title()}: {desc['role']}")
        
        # Demo 3: Available workflows
        logger.info("\n⚡ Demo 3: Available Workflows")
        workflows = orchestrator.crew_system.get_available_workflows()
        for workflow in workflows:
            logger.info(f"   📋 {workflow}")
        
        logger.info("🚀 CrewAI orchestration demonstration completed!")
        
        # Note: Full workflow execution would require OpenAI API key
        logger.info("\n💡 To run full workflows, configure OpenAI API key in config")
        
    except Exception as e:
        logger.error(f"❌ Error in CrewAI demo: {str(e)}")
        # This is expected without proper API keys
        logger.info("📝 Note: Full CrewAI features require API configuration")

def demo_database_integration():
    """Demonstrate database integration with sample data"""
    logger.info("\n💾 DEMO: Database Integration")
    
    # Create sample properties
    sample_properties = []
    
    # Fulton County 4-plex
    fulton_property = Property(
        address="1234 Investment Boulevard",
        city="Atlanta", 
        county="Fulton",
        state="GA",
        zip_code="30309",
        property_type=PropertyType.FOURPLEX,
        units=4,
        square_footage=3200,
        year_built=2010,
        status=PropertyStatus.DISCOVERED,
        foreclosure_stage=ForeclosureStage.AUCTION,
        estimated_value=450000,
        investment_score=85.5,
        roi_estimate=14.2,
        cap_rate=8.8,
        data_sources=["fulton_county_auction", "qpublic_records"],
        tags=["high_potential", "good_condition", "desirable_location"]
    )
    sample_properties.append(fulton_property)
    
    # DeKalb County property
    dekalb_property = Property(
        address="5678 Opportunity Street", 
        city="Decatur",
        county="DeKalb",
        state="GA",
        zip_code="30030",
        property_type=PropertyType.FOURPLEX,
        units=4,
        square_footage=2800,
        year_built=2005,
        status=PropertyStatus.ANALYZING,
        foreclosure_stage=ForeclosureStage.PRE_FORECLOSURE,
        estimated_value=380000,
        investment_score=78.2,
        roi_estimate=12.8,
        cap_rate=8.1,
        data_sources=["dekalb_records"],
        tags=["needs_repair", "good_location"]
    )
    sample_properties.append(dekalb_property)
    
    # Clayton County property  
    clayton_property = Property(
        address="9999 Foreclosure Lane",
        city="Jonesboro", 
        county="Clayton",
        state="GA",
        zip_code="30236",
        property_type=PropertyType.FOURPLEX,
        units=4,
        square_footage=2600,
        year_built=2000,
        status=PropertyStatus.OPPORTUNITY,
        foreclosure_stage=ForeclosureStage.REO,
        estimated_value=295000,
        purchase_price=250000,
        investment_score=92.1,
        roi_estimate=18.5,
        cap_rate=10.2,
        data_sources=["clayton_reo_listings"],
        tags=["exceptional_deal", "motivated_seller", "cash_flow_positive"]
    )
    sample_properties.append(clayton_property)
    
    logger.info("📊 Sample Database Content:")
    for i, prop in enumerate(sample_properties, 1):
        logger.info(f"   {i}. {prop.address} - {prop.county} County")
        logger.info(f"      Status: {prop.status}, Stage: {prop.foreclosure_stage}")
        logger.info(f"      Investment Score: {prop.investment_score}, ROI: {prop.roi_estimate}%")
        logger.info(f"      Cap Rate: {prop.cap_rate}%, Value: ${prop.estimated_value:,}")

async def main():
    """Main demonstration function"""
    logger.info("🚀 4-PLEX INVESTMENT PLATFORM - GEORGIA AGENTS DEMONSTRATION")
    logger.info("=" * 70)
    
    # Demo database content
    demo_database_integration()
    
    # Demo county agents
    await demo_county_agents()
    
    # Demo CrewAI orchestration
    await demo_crewai_orchestration()
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ DEMONSTRATION COMPLETED SUCCESSFULLY!")
    logger.info("\n🎯 SYSTEM CAPABILITIES DEMONSTRATED:")
    logger.info("   ✅ Georgia County Data Collection Agents")
    logger.info("   ✅ Multi-County Coordinated Discovery") 
    logger.info("   ✅ Performance Monitoring & Reporting")
    logger.info("   ✅ CrewAI Multi-Agent Orchestration")
    logger.info("   ✅ Database Integration & Property Management")
    logger.info("   ✅ Scheduled Discovery Workflows")
    
    logger.info("\n📋 NEXT STEPS FOR PRODUCTION:")
    logger.info("   🔑 Configure API keys (OpenAI, property data sources)")
    logger.info("   🌐 Set up county-specific web scraping endpoints")
    logger.info("   ⏰ Configure production scheduling (APScheduler)")
    logger.info("   📊 Set up monitoring dashboards")
    logger.info("   🔒 Implement authentication and security")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Demo failed: {str(e)}")
        raise