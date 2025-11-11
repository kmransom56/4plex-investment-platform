"""
Georgia County Data Collection Agents for 4-Plex Foreclosure Research
Specialized AI agents for collecting foreclosure and property data across Georgia counties
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
import pandas as pd
from dataclasses import dataclass, asdict
import time
import random

from models import Property, PropertyType, PropertyStatus, ForeclosureStage, ProcessingJob, DiscoveryJob
from database.connection import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class CountyDataSource:
    """Configuration for county-specific data sources"""
    county_name: str
    foreclosure_website: Optional[str] = None
    property_records_url: Optional[str] = None
    auction_calendar_url: Optional[str] = None
    reo_listings_url: Optional[str] = None
    api_endpoint: Optional[str] = None
    search_parameters: Dict[str, Any] = None
    rate_limit_delay: float = 1.0
    requires_authentication: bool = False
    data_format: str = "html"  # html, json, xml, csv

class GeorgiaCountyAgent:
    """
    Base agent for Georgia county foreclosure data collection
    Specialized for 4-plex and multifamily property discovery
    """
    
    def __init__(self, county_config: CountyDataSource, db_manager: DatabaseManager):
        self.county = county_config
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"agent.{self.county.county_name.lower()}")
        self.session = None
        
        # 4-plex specific search criteria
        self.property_types = [
            "4-plex", "4plex", "fourplex", "quadplex",
            "multifamily", "apartment", "duplex", "triplex"
        ]
        
        # Foreclosure stages to track
        self.foreclosure_stages = [
            "notice_of_default", "pre_foreclosure", "auction", 
            "reo", "short_sale", "cash_sale"
        ]
        
        # Performance tracking
        self.stats = {
            "properties_discovered": 0,
            "properties_processed": 0,
            "api_calls_made": 0,
            "errors_encountered": 0,
            "last_run_time": None,
            "average_response_time": 0.0
        }
    
    async def initialize(self):
        """Initialize the agent and set up HTTP session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Georgia-Property-Research-Bot/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
        self.logger.info(f"Initialized {self.county.county_name} County Agent")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def discover_properties(self, job: DiscoveryJob) -> List[Property]:
        """
        Main discovery method - searches for 4-plex foreclosure properties
        
        Args:
            job: Discovery job configuration
            
        Returns:
            List of discovered properties
        """
        start_time = time.time()
        discovered_properties = []
        
        try:
            self.logger.info(f"Starting property discovery for {self.county.county_name} County")
            
            # Update job status
            await self.db_manager.update_job_status(job.id, "running", 10, 
                                                   f"Starting {self.county.county_name} discovery")
            
            # Search each foreclosure data source
            for stage in self.foreclosure_stages:
                stage_properties = await self._search_foreclosure_stage(stage, job)
                discovered_properties.extend(stage_properties)
                
                # Update progress
                progress = min(90, 20 + (len(self.foreclosure_stages) * 15))
                await self.db_manager.update_job_status(
                    job.id, "running", progress,
                    f"Discovered {len(stage_properties)} properties in {stage}"
                )
                
                # Rate limiting
                await asyncio.sleep(self.county.rate_limit_delay)
            
            # Filter for 4-plex properties only
            fourplex_properties = await self._filter_fourplex_properties(discovered_properties)
            
            # Save discovered properties to database
            saved_count = 0
            for prop in fourplex_properties:
                if await self.db_manager.save_property(prop):
                    saved_count += 1
            
            # Update statistics
            self.stats["properties_discovered"] = len(fourplex_properties)
            self.stats["properties_processed"] = saved_count
            self.stats["last_run_time"] = datetime.now()
            self.stats["average_response_time"] = time.time() - start_time
            
            # Complete job
            results = {
                "properties_found": len(fourplex_properties),
                "properties_saved": saved_count,
                "county": self.county.county_name,
                "discovery_time": time.time() - start_time,
                "stats": self.stats
            }
            
            await self.db_manager.update_job_status(
                job.id, "completed", 100,
                f"Discovered {saved_count} 4-plex properties", 
                results
            )
            
            self.logger.info(f"Completed {self.county.county_name} discovery: {saved_count} properties saved")
            return fourplex_properties
            
        except Exception as e:
            self.stats["errors_encountered"] += 1
            self.logger.error(f"Error in {self.county.county_name} discovery: {str(e)}")
            
            await self.db_manager.update_job_status(
                job.id, "failed", 0,
                f"Discovery failed: {str(e)}"
            )
            raise
    
    async def _search_foreclosure_stage(self, stage: str, job: DiscoveryJob) -> List[Property]:
        """Search for properties in a specific foreclosure stage"""
        properties = []
        
        try:
            # County-specific search implementation
            if stage == "auction" and self.county.auction_calendar_url:
                properties.extend(await self._search_auction_calendar())
            elif stage == "reo" and self.county.reo_listings_url:
                properties.extend(await self._search_reo_listings())
            elif stage in ["notice_of_default", "pre_foreclosure"] and self.county.foreclosure_website:
                properties.extend(await self._search_foreclosure_website(stage))
            
            self.stats["api_calls_made"] += 1
            
        except Exception as e:
            self.logger.warning(f"Error searching {stage} in {self.county.county_name}: {str(e)}")
        
        return properties
    
    async def _search_auction_calendar(self) -> List[Property]:
        """Search county auction calendar for properties"""
        properties = []
        
        if not self.county.auction_calendar_url:
            return properties
        
        try:
            async with self.session.get(self.county.auction_calendar_url) as response:
                if response.status == 200:
                    content = await response.text()
                    properties = await self._parse_auction_data(content)
                    
        except Exception as e:
            self.logger.error(f"Error fetching auction calendar: {str(e)}")
        
        return properties
    
    async def _search_reo_listings(self) -> List[Property]:
        """Search REO (Real Estate Owned) listings"""
        properties = []
        
        if not self.county.reo_listings_url:
            return properties
        
        try:
            async with self.session.get(self.county.reo_listings_url) as response:
                if response.status == 200:
                    content = await response.text()
                    properties = await self._parse_reo_data(content)
                    
        except Exception as e:
            self.logger.error(f"Error fetching REO listings: {str(e)}")
        
        return properties
    
    async def _search_foreclosure_website(self, stage: str) -> List[Property]:
        """Search county foreclosure website"""
        properties = []
        
        if not self.county.foreclosure_website:
            return properties
        
        try:
            search_params = self.county.search_parameters or {}
            search_params.update({
                "property_type": "multifamily",
                "foreclosure_stage": stage,
                "min_units": 4
            })
            
            async with self.session.get(self.county.foreclosure_website, params=search_params) as response:
                if response.status == 200:
                    content = await response.text()
                    properties = await self._parse_foreclosure_data(content, stage)
                    
        except Exception as e:
            self.logger.error(f"Error searching foreclosure website: {str(e)}")
        
        return properties
    
    async def _filter_fourplex_properties(self, properties: List[Property]) -> List[Property]:
        """Filter properties to only include 4-plexes and similar multifamily"""
        fourplex_properties = []
        
        for prop in properties:
            # Check if property matches 4-plex criteria
            is_fourplex = (
                prop.units == 4 or
                any(ptype in str(prop.property_type).lower() for ptype in ["4plex", "fourplex", "quadplex"]) or
                (prop.units and 2 <= prop.units <= 6)  # Include 2-6 unit properties
            )
            
            if is_fourplex:
                # Set appropriate property type
                if prop.units == 4 or "4plex" in str(prop.property_type).lower():
                    prop.property_type = PropertyType.FOURPLEX
                elif prop.units == 2:
                    prop.property_type = PropertyType.DUPLEX
                elif prop.units == 3:
                    prop.property_type = PropertyType.TRIPLEX
                else:
                    prop.property_type = PropertyType.MULTIFAMILY
                
                fourplex_properties.append(prop)
        
        self.logger.info(f"Filtered {len(fourplex_properties)} 4-plex properties from {len(properties)} total")
        return fourplex_properties
    
    async def _parse_auction_data(self, content: str) -> List[Property]:
        """Parse auction calendar data"""
        # Implementation would depend on county-specific format
        # This is a placeholder for county-specific parsing
        properties = []
        
        # Example parsing logic (would be customized per county)
        try:
            # Parse HTML/JSON content to extract property data
            # Look for property addresses, auction dates, estimated values
            pass
        except Exception as e:
            self.logger.error(f"Error parsing auction data: {str(e)}")
        
        return properties
    
    async def _parse_reo_data(self, content: str) -> List[Property]:
        """Parse REO listings data"""
        properties = []
        
        try:
            # Parse REO listings content
            # Extract property details, prices, listing agents
            pass
        except Exception as e:
            self.logger.error(f"Error parsing REO data: {str(e)}")
        
        return properties
    
    async def _parse_foreclosure_data(self, content: str, stage: str) -> List[Property]:
        """Parse general foreclosure website data"""
        properties = []
        
        try:
            # Parse foreclosure data based on stage
            # Extract case numbers, property details, foreclosure dates
            pass
        except Exception as e:
            self.logger.error(f"Error parsing foreclosure data: {str(e)}")
        
        return properties
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics"""
        return self.stats.copy()

class FultonCountyAgent(GeorgiaCountyAgent):
    """Specialized agent for Fulton County foreclosure discovery"""
    
    def __init__(self, db_manager: DatabaseManager):
        config = CountyDataSource(
            county_name="Fulton",
            foreclosure_website="https://www.fultoncountyga.gov/services/real-estate/foreclosure-sales",
            property_records_url="https://www.qpublic.net/ga/fulton/",
            auction_calendar_url="https://www.fultoncountyga.gov/services/real-estate/foreclosure-calendar",
            rate_limit_delay=1.5,
            search_parameters={
                "county": "Fulton",
                "state": "GA"
            }
        )
        super().__init__(config, db_manager)
    
    async def _parse_auction_data(self, content: str) -> List[Property]:
        """Fulton County specific auction data parsing"""
        properties = []
        
        try:
            # Fulton County specific parsing logic
            # Extract from their specific HTML/data format
            
            # Example property creation (would be based on actual data)
            sample_property = Property(
                address="123 Sample St",
                city="Atlanta",
                county="Fulton",
                state="GA",
                property_type=PropertyType.FOURPLEX,
                units=4,
                foreclosure_stage=ForeclosureStage.AUCTION,
                status=PropertyStatus.DISCOVERED,
                data_sources=["fulton_county_auction"]
            )
            properties.append(sample_property)
            
        except Exception as e:
            self.logger.error(f"Error parsing Fulton County auction data: {str(e)}")
        
        return properties

class DeKalbCountyAgent(GeorgiaCountyAgent):
    """Specialized agent for DeKalb County foreclosure discovery"""
    
    def __init__(self, db_manager: DatabaseManager):
        config = CountyDataSource(
            county_name="DeKalb",
            foreclosure_website="https://www.dekalbcountyga.gov/real-estate",
            property_records_url="https://www.qpublic.net/ga/dekalb/",
            rate_limit_delay=1.2,
            search_parameters={
                "county": "DeKalb", 
                "state": "GA"
            }
        )
        super().__init__(config, db_manager)

class AtlantaCityAgent(GeorgiaCountyAgent):
    """Specialized agent for City of Atlanta foreclosure discovery"""
    
    def __init__(self, db_manager: DatabaseManager):
        config = CountyDataSource(
            county_name="Atlanta",
            foreclosure_website="https://www.atlantaga.gov/government/departments/finance/real-estate",
            property_records_url="https://www.qpublic.net/ga/fulton/",  # Atlanta uses Fulton County records
            rate_limit_delay=1.0,
            search_parameters={
                "county": "Fulton",
                "city": "Atlanta", 
                "state": "GA"
            }
        )
        super().__init__(config, db_manager)

class ClaytonCountyAgent(GeorgiaCountyAgent):
    """Specialized agent for Clayton County foreclosure discovery"""
    
    def __init__(self, db_manager: DatabaseManager):
        config = CountyDataSource(
            county_name="Clayton",
            foreclosure_website="https://www.claytoncountyga.gov/government/departments-f-p/planning-development/property-records",
            property_records_url="https://www.qpublic.net/ga/clayton/",
            rate_limit_delay=1.3,
            search_parameters={
                "county": "Clayton",
                "state": "GA"
            }
        )
        super().__init__(config, db_manager)

class CobbCountyAgent(GeorgiaCountyAgent):
    """Specialized agent for Cobb County foreclosure discovery"""
    
    def __init__(self, db_manager: DatabaseManager):
        config = CountyDataSource(
            county_name="Cobb",
            foreclosure_website="https://www.cobbcounty.org/public-records/property-records",
            property_records_url="https://www.qpublic.net/ga/cobb/",
            auction_calendar_url="https://www.cobbcounty.org/public-records/foreclosure-sales",
            rate_limit_delay=1.4,
            search_parameters={
                "county": "Cobb",
                "state": "GA"
            }
        )
        super().__init__(config, db_manager)

class GeorgiaCountyAgentManager:
    """
    Manager for coordinating all Georgia county agents
    Handles scheduling, job distribution, and performance monitoring
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger("georgia.agent.manager")
        
        # Initialize all county agents
        self.agents = {
            "fulton": FultonCountyAgent(db_manager),
            "dekalb": DeKalbCountyAgent(db_manager), 
            "atlanta": AtlantaCityAgent(db_manager),
            "clayton": ClaytonCountyAgent(db_manager),
            "cobb": CobbCountyAgent(db_manager)
        }
        
        self.discovery_schedule = {
            "daily": ["fulton", "atlanta"],  # High-activity counties
            "weekly": ["dekalb", "clayton", "cobb"]  # Moderate activity
        }
    
    async def initialize_all_agents(self):
        """Initialize all county agents"""
        for agent_name, agent in self.agents.items():
            try:
                await agent.initialize()
                self.logger.info(f"Initialized {agent_name} agent")
            except Exception as e:
                self.logger.error(f"Failed to initialize {agent_name} agent: {str(e)}")
    
    async def cleanup_all_agents(self):
        """Cleanup all county agents"""
        for agent_name, agent in self.agents.items():
            try:
                await agent.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up {agent_name} agent: {str(e)}")
    
    async def run_discovery_job(self, counties: List[str] = None, max_results: int = 100) -> DiscoveryJob:
        """
        Run coordinated discovery across specified counties
        
        Args:
            counties: List of county names to search (default: all)
            max_results: Maximum properties to discover per county
            
        Returns:
            DiscoveryJob with consolidated results
        """
        counties = counties or list(self.agents.keys())
        
        # Create discovery job
        job = DiscoveryJob(
            counties=counties,
            max_results=max_results,
            search_parameters={
                "property_types": ["4-plex", "fourplex", "quadplex", "multifamily"],
                "min_units": 2,
                "max_units": 6
            }
        )
        
        await self.db_manager.save_job(job)
        
        try:
            self.logger.info(f"Starting coordinated discovery across {len(counties)} counties")
            
            # Run discovery in parallel across counties
            tasks = []
            for county_name in counties:
                if county_name in self.agents:
                    agent = self.agents[county_name]
                    tasks.append(agent.discover_properties(job))
            
            # Wait for all agents to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Consolidate results
            total_properties = []
            successful_counties = []
            
            for i, result in enumerate(results):
                county_name = counties[i]
                if isinstance(result, Exception):
                    self.logger.error(f"Discovery failed for {county_name}: {str(result)}")
                else:
                    total_properties.extend(result)
                    successful_counties.append(county_name)
            
            # Update job with final results
            job.properties_found = total_properties
            job.total_properties = len(total_properties)
            job.status = "completed"
            job.results = {
                "total_properties_found": len(total_properties),
                "successful_counties": successful_counties,
                "failed_counties": [c for c in counties if c not in successful_counties],
                "properties_by_county": {
                    county: len([p for p in total_properties if p.county.lower() == county])
                    for county in successful_counties
                }
            }
            
            await self.db_manager.save_job(job)
            
            self.logger.info(f"Discovery completed: {len(total_properties)} properties across {len(successful_counties)} counties")
            return job
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            await self.db_manager.save_job(job)
            self.logger.error(f"Coordinated discovery failed: {str(e)}")
            raise
    
    async def get_agent_performance_report(self) -> Dict[str, Any]:
        """Generate performance report for all agents"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "agents": {},
            "summary": {
                "total_properties_discovered": 0,
                "total_api_calls": 0,
                "total_errors": 0,
                "active_agents": 0
            }
        }
        
        for agent_name, agent in self.agents.items():
            stats = agent.get_stats()
            report["agents"][agent_name] = stats
            
            # Update summary
            report["summary"]["total_properties_discovered"] += stats.get("properties_discovered", 0)
            report["summary"]["total_api_calls"] += stats.get("api_calls_made", 0)
            report["summary"]["total_errors"] += stats.get("errors_encountered", 0)
            
            if stats.get("last_run_time"):
                report["summary"]["active_agents"] += 1
        
        return report
    
    async def schedule_daily_discovery(self):
        """Run daily discovery for high-activity counties"""
        daily_counties = self.discovery_schedule["daily"]
        self.logger.info(f"Running daily discovery for: {daily_counties}")
        
        try:
            job = await self.run_discovery_job(counties=daily_counties, max_results=50)
            return job
        except Exception as e:
            self.logger.error(f"Daily discovery failed: {str(e)}")
            raise
    
    async def schedule_weekly_discovery(self):
        """Run weekly discovery for moderate-activity counties"""
        weekly_counties = self.discovery_schedule["weekly"] 
        self.logger.info(f"Running weekly discovery for: {weekly_counties}")
        
        try:
            job = await self.run_discovery_job(counties=weekly_counties, max_results=75)
            return job
        except Exception as e:
            self.logger.error(f"Weekly discovery failed: {str(e)}")
            raise

# Export main classes
__all__ = [
    "GeorgiaCountyAgent", 
    "FultonCountyAgent", 
    "DeKalbCountyAgent",
    "AtlantaCityAgent", 
    "ClaytonCountyAgent", 
    "CobbCountyAgent",
    "GeorgiaCountyAgentManager",
    "CountyDataSource"
]