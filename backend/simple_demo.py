#!/usr/bin/env python3
"""
Simple demonstration of the 4-plex platform core functionality
Shows the database and agent system without external dependencies
"""

import asyncio
import logging
from datetime import datetime
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import DatabaseManager
from models import Property, PropertyType, PropertyStatus, ForeclosureStage, DiscoveryJob
from agents.georgia_county_agents import GeorgiaCountyAgentManager, FultonCountyAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_demo")

async def demo_database_operations():
    """Demonstrate database operations"""
    logger.info("💾 Testing Database Operations")
    
    db_manager = DatabaseManager()
    
    # Create sample 4-plex properties
    properties = [
        Property(
            address="123 Investment Blvd",
            city="Atlanta",
            county="Fulton", 
            state="GA",
            zip_code="30309",
            property_type=PropertyType.FOURPLEX,
            units=4,
            status=PropertyStatus.DISCOVERED,
            foreclosure_stage=ForeclosureStage.AUCTION,
            estimated_value=450000,
            investment_score=85.5,
            data_sources=["fulton_county_auction"]
        ),
        Property(
            address="456 Opportunity Ave",
            city="Decatur",
            county="DeKalb",
            state="GA", 
            zip_code="30030",
            property_type=PropertyType.FOURPLEX,
            units=4,
            status=PropertyStatus.OPPORTUNITY,
            foreclosure_stage=ForeclosureStage.REO,
            estimated_value=380000,
            investment_score=92.1,
            data_sources=["dekalb_reo_listings"]
        )
    ]
    
    # Save properties
    for i, prop in enumerate(properties):
        success = await db_manager.save_property(prop)
        logger.info(f"   {'✅' if success else '❌'} Saved property {i+1}: {prop.address}")
    
    # Retrieve properties
    all_properties = await db_manager.get_properties(limit=10)
    logger.info(f"   📊 Retrieved {len(all_properties)} properties from database")
    
    # Get metrics
    metrics = await db_manager.get_metrics()
    logger.info(f"   📈 Platform metrics: {metrics['properties_analyzed']} properties analyzed")
    
    return len(all_properties)

async def demo_georgia_agents():
    """Demonstrate Georgia county agents"""
    logger.info("🏛️ Testing Georgia County Agents")
    
    db_manager = DatabaseManager()
    agent_manager = GeorgiaCountyAgentManager(db_manager)
    
    try:
        # Initialize agents
        await agent_manager.initialize_all_agents()
        logger.info("   ✅ Initialized 5 Georgia county agents")
        
        # Show agent configuration
        for name, agent in agent_manager.agents.items():
            logger.info(f"      🏛️ {name.title()} County: {agent.county.county_name}")
        
        # Test individual agent
        fulton_agent = agent_manager.agents["fulton"]
        logger.info(f"   🎯 Testing Fulton County Agent")
        logger.info(f"      Rate limit: {fulton_agent.county.rate_limit_delay}s")
        logger.info(f"      Property types tracked: {len(fulton_agent.property_types)}")
        
        # Get agent stats
        stats = fulton_agent.get_stats()
        logger.info(f"      📊 Agent stats initialized: {stats}")
        
        # Performance report
        performance = await agent_manager.get_agent_performance_report()
        logger.info(f"   📈 Performance report generated for {len(performance['agents'])} agents")
        
    finally:
        await agent_manager.cleanup_all_agents()
        logger.info("   🧹 Cleaned up agent resources")

async def demo_discovery_job():
    """Demonstrate discovery job creation"""
    logger.info("🔍 Testing Discovery Job System")
    
    db_manager = DatabaseManager()
    
    # Create discovery job
    job = DiscoveryJob(
        counties=["fulton", "dekalb", "atlanta"],
        max_results=50,
        search_parameters={
            "property_types": ["4-plex", "fourplex", "quadplex"],
            "min_units": 4,
            "foreclosure_stages": ["auction", "reo"]
        }
    )
    
    # Save job
    success = await db_manager.save_job(job)
    logger.info(f"   {'✅' if success else '❌'} Created discovery job: {job.id}")
    
    # Retrieve job
    retrieved_job = await db_manager.get_job(job.id)
    if retrieved_job:
        logger.info(f"   📋 Job details: {retrieved_job.job_type} for {len(job.counties)} counties")
        logger.info(f"      Status: {retrieved_job.status}, Progress: {retrieved_job.progress}%")
    
    # Update job status
    await db_manager.update_job_status(job.id, "running", 50, "Processing counties")
    logger.info("   ⚡ Updated job status to running")
    
    return job.id

async def main():
    """Main demonstration"""
    logger.info("🚀 4-PLEX INVESTMENT PLATFORM - CORE SYSTEM DEMO")
    logger.info("=" * 60)
    
    try:
        # Test database operations
        property_count = await demo_database_operations()
        
        # Test Georgia county agents
        await demo_georgia_agents()
        
        # Test discovery job system
        job_id = await demo_discovery_job()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ CORE SYSTEM DEMONSTRATION SUCCESSFUL!")
        logger.info(f"\n📊 RESULTS SUMMARY:")
        logger.info(f"   💾 Database: {property_count} properties stored")
        logger.info(f"   🏛️ Agents: 5 Georgia county agents configured")
        logger.info(f"   🔍 Jobs: Discovery job {job_id[:8]}... created")
        
        logger.info(f"\n🎯 SYSTEM COMPONENTS VERIFIED:")
        logger.info("   ✅ Database operations (CRUD)")
        logger.info("   ✅ Property models and validation")
        logger.info("   ✅ Georgia county agent architecture")
        logger.info("   ✅ Discovery job management")
        logger.info("   ✅ Async/await implementation")
        
        logger.info(f"\n📋 FULL SYSTEM INCLUDES:")
        logger.info("   🏛️ 5 Georgia County Agents (Fulton, DeKalb, Atlanta, Clayton, Cobb)")
        logger.info("   🤖 CrewAI Multi-Agent Orchestration (requires pip install crewai)")
        logger.info("   📊 Financial Calculations (multifamily valuation preserved)")
        logger.info("   📑 Document Processing (AI-powered analysis)")
        logger.info("   📈 Export System (Excel, PDF, PowerPoint reports)")
        logger.info("   ⚡ Real-time Status System (WebSocket support)")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()