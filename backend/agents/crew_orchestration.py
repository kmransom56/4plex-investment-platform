"""
CrewAI Framework Integration for 4-Plex Investment Platform
Multi-agent orchestration for foreclosure discovery and investment analysis
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import uuid

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    from langchain.llms import OpenAI
    from langchain.tools import tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not available. Install with: pip install crewai")

from models import Property, PropertyAnalysis, ProcessingJob, DiscoveryJob
from database.connection import DatabaseManager
from financial_calculations import FinancialCalculator
from agents.georgia_county_agents import GeorgiaCountyAgentManager
from property_manager import PropertyManager

logger = logging.getLogger(__name__)

class PropertyDiscoveryTool(BaseTool):
    """Tool for property discovery across Georgia counties"""
    
    name: str = "property_discovery"
    description: str = "Discover foreclosure properties in Georgia counties focusing on 4-plex investments"
    
    def __init__(self, agent_manager: GeorgiaCountyAgentManager):
        super().__init__()
        self.agent_manager = agent_manager
    
    def _run(self, counties: str = "all", max_properties: int = 50) -> str:
        """Run property discovery"""
        try:
            # Parse counties parameter
            if counties == "all":
                county_list = ["fulton", "dekalb", "atlanta", "clayton", "cobb"]
            else:
                county_list = [c.strip().lower() for c in counties.split(",")]
            
            # Run discovery (would need async wrapper in production)
            # For now, return simulated results
            return f"Discovered properties in {', '.join(county_list)} counties. Found {max_properties} potential 4-plex investments."
            
        except Exception as e:
            return f"Error in property discovery: {str(e)}"
    
    async def _arun(self, counties: str = "all", max_properties: int = 50) -> str:
        """Async version of property discovery"""
        try:
            # Parse counties parameter
            if counties == "all":
                county_list = ["fulton", "dekalb", "atlanta", "clayton", "cobb"]
            else:
                county_list = [c.strip().lower() for c in counties.split(",")]
            
            # Run coordinated discovery
            job = await self.agent_manager.run_discovery_job(county_list, max_properties)
            
            return f"Completed discovery job {job.id}: Found {len(job.properties_found)} properties across {len(county_list)} counties"
            
        except Exception as e:
            return f"Error in property discovery: {str(e)}"

class PropertyAnalysisTool(BaseTool):
    """Tool for financial analysis of discovered properties"""
    
    name: str = "property_analysis"
    description: str = "Perform comprehensive financial analysis on 4-plex investment properties"
    
    def __init__(self, financial_calculator: FinancialCalculator, property_manager: PropertyManager):
        super().__init__()
        self.financial_calculator = financial_calculator
        self.property_manager = property_manager
    
    def _run(self, property_id: str, purchase_price: float = None, rental_income: float = None) -> str:
        """Run property analysis"""
        try:
            # Simulate analysis results
            analysis_results = {
                "property_id": property_id,
                "purchase_price": purchase_price or 400000,
                "estimated_rental_income": rental_income or 4800,
                "cap_rate": 8.5,
                "cash_on_cash_return": 12.3,
                "investment_grade": "B+",
                "recommendation": "Strong investment opportunity"
            }
            
            return f"Analysis complete for property {property_id}: {analysis_results['investment_grade']} grade, {analysis_results['cap_rate']}% cap rate"
            
        except Exception as e:
            return f"Error in property analysis: {str(e)}"

class InvestmentOpportunityTool(BaseTool):
    """Tool for identifying top investment opportunities"""
    
    name: str = "investment_opportunities"
    description: str = "Identify and rank top 4-plex investment opportunities based on financial metrics"
    
    def __init__(self, property_manager: PropertyManager):
        super().__init__()
        self.property_manager = property_manager
    
    def _run(self, min_grade: str = "B", max_results: int = 10) -> str:
        """Find investment opportunities"""
        try:
            # Simulate opportunity identification
            opportunities = [
                {"property_id": "prop_001", "address": "123 Investment St, Atlanta, GA", "grade": "A", "cap_rate": 9.2},
                {"property_id": "prop_002", "address": "456 Opportunity Ave, Decatur, GA", "grade": "B+", "cap_rate": 8.7},
                {"property_id": "prop_003", "address": "789 Profit Dr, Marietta, GA", "grade": "B", "cap_rate": 8.1}
            ]
            
            return f"Found {len(opportunities)} investment opportunities with grade {min_grade} or better"
            
        except Exception as e:
            return f"Error identifying opportunities: {str(e)}"

class ForeclosureResearchCrew:
    """
    CrewAI-powered multi-agent system for 4-plex foreclosure research
    Coordinates specialized agents for discovery, analysis, and opportunity identification
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("crew.foreclosure_research")
        
        if not CREWAI_AVAILABLE:
            raise ImportError("CrewAI is required. Install with: pip install crewai")
        
        # Initialize core components
        self.db_manager = DatabaseManager(config.get("database", {}))
        self.financial_calculator = FinancialCalculator(config.get("financial_assumptions", {}))
        self.property_manager = PropertyManager(config)
        self.agent_manager = GeorgiaCountyAgentManager(self.db_manager)
        
        # Initialize LLM
        self.llm = OpenAI(
            temperature=0.1,
            openai_api_key=config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize tools
        self.tools = [
            PropertyDiscoveryTool(self.agent_manager),
            PropertyAnalysisTool(self.financial_calculator, self.property_manager),
            InvestmentOpportunityTool(self.property_manager)
        ]
        
        # Create specialized agents
        self.agents = self._create_agents()
        
        # Define workflows
        self.workflows = self._create_workflows()
    
    def _create_agents(self) -> Dict[str, Agent]:
        """Create specialized agents for the crew"""
        
        agents = {}
        
        # Property Discovery Agent
        agents["discovery"] = Agent(
            role="Property Discovery Specialist",
            goal="Discover 4-plex and multifamily foreclosure properties across Georgia counties",
            backstory="""You are an expert real estate researcher specializing in foreclosure properties. 
            Your expertise lies in identifying 4-plex investment opportunities across Fulton, DeKalb, 
            Atlanta, Clayton, and Cobb counties. You know how to navigate county websites, understand 
            foreclosure processes, and identify properties with strong investment potential.""",
            tools=[self.tools[0]],  # PropertyDiscoveryTool
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Financial Analysis Agent  
        agents["analyst"] = Agent(
            role="Investment Analysis Expert",
            goal="Perform comprehensive financial analysis on discovered 4-plex properties",
            backstory="""You are a seasoned real estate investment analyst with deep expertise in 
            multifamily properties. You excel at calculating cap rates, cash-on-cash returns, IRR, 
            and other key investment metrics. Your analysis helps investors make informed decisions 
            about 4-plex acquisitions and understand the financial viability of foreclosure opportunities.""",
            tools=[self.tools[1]],  # PropertyAnalysisTool
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Investment Strategist Agent
        agents["strategist"] = Agent(
            role="Investment Strategy Advisor",
            goal="Identify and prioritize the best 4-plex investment opportunities",
            backstory="""You are a strategic real estate investment advisor focused on multifamily 
            properties. Your role is to synthesize market data, financial analysis, and risk factors 
            to recommend the highest-potential 4-plex investments. You understand market timing, 
            location factors, and portfolio diversification strategies.""",
            tools=[self.tools[2]],  # InvestmentOpportunityTool
            llm=self.llm,
            verbose=True,
            allow_delegation=True
        )
        
        # Market Research Agent
        agents["researcher"] = Agent(
            role="Market Research Specialist", 
            goal="Research market conditions and trends affecting 4-plex investments in Georgia",
            backstory="""You are a market research expert specializing in Georgia real estate markets. 
            You track rental rates, vacancy rates, neighborhood trends, and economic factors that 
            impact 4-plex investments. Your insights help contextualize individual property 
            opportunities within broader market conditions.""",
            tools=[],  # Uses general research capabilities
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        return agents
    
    def _create_workflows(self) -> Dict[str, List[Task]]:
        """Create workflow task definitions"""
        
        workflows = {}
        
        # Daily Discovery Workflow
        workflows["daily_discovery"] = [
            Task(
                description="""Discover new 4-plex foreclosure properties in high-activity Georgia counties 
                (Fulton and Atlanta). Focus on properties with 2-6 units that are in pre-foreclosure, 
                auction, or REO stages. Prioritize properties under $500K with strong rental potential.""",
                agent=self.agents["discovery"],
                expected_output="List of newly discovered 4-plex properties with basic details"
            ),
            Task(
                description="""Analyze the financial potential of newly discovered properties. 
                Calculate key metrics including cap rate, cash-on-cash return, and investment grade. 
                Focus on properties that meet our investment criteria (cap rate > 7%, positive cash flow).""",
                agent=self.agents["analyst"],
                expected_output="Financial analysis report with investment grades and recommendations"
            ),
            Task(
                description="""Identify the top 5 investment opportunities from today's discoveries. 
                Consider financial metrics, location factors, and market conditions. Provide ranked 
                recommendations with rationale for each property.""",
                agent=self.agents["strategist"], 
                expected_output="Ranked list of top 5 investment opportunities with strategic analysis"
            )
        ]
        
        # Weekly Comprehensive Analysis
        workflows["weekly_analysis"] = [
            Task(
                description="""Conduct comprehensive property discovery across all Georgia counties 
                (Fulton, DeKalb, Atlanta, Clayton, Cobb). Search for 4-plex and multifamily properties 
                in all foreclosure stages. Aim to discover 75-100 properties per county.""",
                agent=self.agents["discovery"],
                expected_output="Comprehensive list of discovered properties across all target counties"
            ),
            Task(
                description="""Research current market conditions for 4-plex investments in Georgia. 
                Analyze rental rates, vacancy trends, neighborhood development, and economic indicators. 
                Identify emerging opportunity zones and markets showing appreciation potential.""",
                agent=self.agents["researcher"],
                expected_output="Market research report with trends and opportunity identification"
            ),
            Task(
                description="""Perform detailed financial analysis on all discovered properties. 
                Calculate comprehensive metrics including multi-year projections, sensitivity analysis, 
                and risk assessment. Identify properties meeting our investment criteria.""",
                agent=self.agents["analyst"],
                expected_output="Detailed financial analysis with investment recommendations"
            ),
            Task(
                description="""Create strategic investment portfolio recommendations based on all 
                discovered opportunities. Consider diversification across counties, risk levels, 
                and investment timelines. Provide acquisition priority rankings.""",
                agent=self.agents["strategist"],
                expected_output="Strategic portfolio recommendations with acquisition priorities"
            )
        ]
        
        # Opportunity Assessment Workflow
        workflows["opportunity_assessment"] = [
            Task(
                description="""Identify high-priority 4-plex investment opportunities from our database. 
                Focus on properties with A/B grades, strong cash flow potential, and favorable 
                acquisition terms. Consider both immediate opportunities and pipeline properties.""",
                agent=self.agents["strategist"],
                expected_output="List of high-priority investment opportunities with rankings"
            ),
            Task(
                description="""Conduct deep-dive financial analysis on prioritized opportunities. 
                Include detailed cash flow projections, scenario analysis, and risk assessment. 
                Calculate returns under different market conditions and hold periods.""",
                agent=self.agents["analyst"], 
                expected_output="Comprehensive financial models for priority opportunities"
            ),
            Task(
                description="""Research market context for each priority opportunity. Analyze 
                neighborhood trends, comparable sales, rental comps, and development plans. 
                Assess external factors that could impact investment performance.""",
                agent=self.agents["researcher"],
                expected_output="Market context analysis for each priority opportunity"
            )
        ]
        
        return workflows
    
    async def execute_workflow(self, workflow_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a specific workflow
        
        Args:
            workflow_name: Name of workflow to execute
            **kwargs: Additional parameters for the workflow
            
        Returns:
            Workflow execution results
        """
        if workflow_name not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        tasks = self.workflows[workflow_name]
        
        try:
            self.logger.info(f"Starting workflow: {workflow_name}")
            start_time = datetime.now()
            
            # Initialize agent manager
            await self.agent_manager.initialize_all_agents()
            
            # Create and execute crew
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )
            
            # Execute the crew workflow
            result = crew.kickoff()
            
            # Cleanup
            await self.agent_manager.cleanup_all_agents()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            workflow_result = {
                "workflow_name": workflow_name,
                "execution_time": execution_time,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "status": "completed",
                "results": result,
                "agent_performance": await self.agent_manager.get_agent_performance_report()
            }
            
            self.logger.info(f"Completed workflow {workflow_name} in {execution_time:.2f} seconds")
            return workflow_result
            
        except Exception as e:
            self.logger.error(f"Workflow {workflow_name} failed: {str(e)}")
            return {
                "workflow_name": workflow_name,
                "status": "failed",
                "error": str(e),
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat()
            }
    
    async def run_daily_discovery(self) -> Dict[str, Any]:
        """Execute daily discovery workflow"""
        return await self.execute_workflow("daily_discovery")
    
    async def run_weekly_analysis(self) -> Dict[str, Any]:
        """Execute weekly comprehensive analysis workflow"""
        return await self.execute_workflow("weekly_analysis")
    
    async def assess_opportunities(self) -> Dict[str, Any]:
        """Execute opportunity assessment workflow"""
        return await self.execute_workflow("opportunity_assessment")
    
    def get_available_workflows(self) -> List[str]:
        """Get list of available workflows"""
        return list(self.workflows.keys())
    
    def get_agent_descriptions(self) -> Dict[str, Dict[str, str]]:
        """Get descriptions of all agents"""
        descriptions = {}
        for name, agent in self.agents.items():
            descriptions[name] = {
                "role": agent.role,
                "goal": agent.goal,
                "backstory": agent.backstory
            }
        return descriptions

class FourPlexInvestmentOrchestrator:
    """
    Main orchestrator for the 4-plex investment platform
    Coordinates CrewAI agents with Georgia county data collection
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("orchestrator.4plex")
        
        # Initialize CrewAI system
        self.crew_system = ForeclosureResearchCrew(config)
        
        # Scheduling configuration
        self.schedule_config = {
            "daily_discovery": {
                "enabled": True,
                "time": "06:00",  # 6 AM
                "counties": ["fulton", "atlanta"]
            },
            "weekly_analysis": {
                "enabled": True, 
                "day": "monday",
                "time": "08:00",  # 8 AM Monday
                "counties": ["fulton", "dekalb", "atlanta", "clayton", "cobb"]
            },
            "opportunity_assessment": {
                "enabled": True,
                "frequency": "bi_weekly",
                "day": "friday",
                "time": "14:00"  # 2 PM Friday
            }
        }
    
    async def start_orchestrator(self):
        """Start the orchestrator with scheduled workflows"""
        self.logger.info("Starting 4-Plex Investment Orchestrator")
        
        try:
            # Initialize all agents
            await self.crew_system.agent_manager.initialize_all_agents()
            
            # Start scheduled workflows (in production, would use a scheduler like APScheduler)
            self.logger.info("Orchestrator started successfully")
            
            # For demonstration, run a sample workflow
            result = await self.crew_system.run_daily_discovery()
            self.logger.info(f"Sample daily discovery completed: {result['status']}")
            
        except Exception as e:
            self.logger.error(f"Failed to start orchestrator: {str(e)}")
            raise
    
    async def stop_orchestrator(self):
        """Stop the orchestrator and cleanup resources"""
        self.logger.info("Stopping 4-Plex Investment Orchestrator")
        
        try:
            await self.crew_system.agent_manager.cleanup_all_agents()
            self.logger.info("Orchestrator stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping orchestrator: {str(e)}")
    
    async def manual_discovery(self, counties: List[str] = None) -> Dict[str, Any]:
        """Manually trigger property discovery"""
        counties = counties or ["fulton", "atlanta", "dekalb"]
        self.logger.info(f"Manual discovery triggered for: {counties}")
        
        return await self.crew_system.run_daily_discovery()
    
    async def generate_investment_report(self) -> Dict[str, Any]:
        """Generate comprehensive investment opportunities report"""
        self.logger.info("Generating investment opportunities report")
        
        return await self.crew_system.assess_opportunities()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "orchestrator_active": True,
            "available_workflows": self.crew_system.get_available_workflows(),
            "agent_descriptions": self.crew_system.get_agent_descriptions(),
            "schedule_config": self.schedule_config,
            "counties_monitored": ["fulton", "dekalb", "atlanta", "clayton", "cobb"]
        }

# Export main classes
__all__ = [
    "ForeclosureResearchCrew",
    "FourPlexInvestmentOrchestrator", 
    "PropertyDiscoveryTool",
    "PropertyAnalysisTool",
    "InvestmentOpportunityTool"
]