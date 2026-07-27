"""
Base Agent Class for 4-Plex Foreclosure Research System
Provides common functionality for all specialized agents
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime
import json

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from services.database.connection import get_db_session
from services.database.models import PropertyRecord, DataSource
from config.settings import Settings


@dataclass
class AgentResult:
    """Standardized result format for agent operations"""
    agent_name: str
    task_id: str
    success: bool
    data: Dict[str, Any]
    message: str
    timestamp: datetime
    processing_time: float
    records_processed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class BaseForeclosureAgent(ABC):
    """Base class for all foreclosure research agents"""
    
    def __init__(self, name: str, settings: Settings):
        self.name = name
        self.settings = settings
        self.logger = self._setup_logging()
        self.llm = self._setup_llm()
        
        # CrewAI Agent configuration
        self.agent = Agent(
            role=self._get_agent_role(),
            goal=self._get_agent_goal(), 
            backstory=self._get_agent_backstory(),
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for the agent"""
        logger = logging.getLogger(f"foreclosure_agent.{self.name}")
        logger.setLevel(getattr(logging, self.settings.LOG_LEVEL))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def _setup_llm(self) -> ChatOpenAI:
        """Setup LLM connection via vLLM AI Gateway"""
        return ChatOpenAI(
            openai_api_base=self.settings.VLLM_GATEWAY_URL + "/v1",
            openai_api_key=self.settings.AI_STACK_API_KEY,
            model_name="general",  # Use general model for most tasks
            temperature=0.1,
            max_tokens=2048
        )
    
    @abstractmethod
    def _get_agent_role(self) -> str:
        """Define the agent's role"""
        pass
        
    @abstractmethod 
    def _get_agent_goal(self) -> str:
        """Define the agent's primary goal"""
        pass
        
    @abstractmethod
    def _get_agent_backstory(self) -> str:
        """Define the agent's backstory and expertise"""
        pass
        
    @abstractmethod
    async def execute_task(self, task_data: Dict[str, Any]) -> AgentResult:
        """Execute the agent's primary task"""
        pass
        
    def create_task(self, description: str, expected_output: str, context: Optional[Dict] = None) -> Task:
        """Create a CrewAI task for this agent"""
        return Task(
            description=description,
            expected_output=expected_output,
            agent=self.agent,
            context=context
        )
        
    async def save_property_record(self, property_data: Dict[str, Any], source: str) -> Optional[int]:
        """Save property data to database"""
        try:
            with get_db_session() as db:
                # Check if property already exists
                existing = db.query(PropertyRecord).filter_by(
                    address=property_data.get('address'),
                    county=property_data.get('county')
                ).first()
                
                if existing:
                    # Update existing record
                    for key, value in property_data.items():
                        if hasattr(existing, key) and value is not None:
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    property_id = existing.id
                else:
                    # Create new record
                    record = PropertyRecord(**property_data)
                    db.add(record)
                    db.flush()
                    property_id = record.id
                
                # Record data source
                data_source = DataSource(
                    property_id=property_id,
                    source_name=source,
                    source_url=property_data.get('source_url'),
                    collected_at=datetime.utcnow(),
                    agent_name=self.name
                )
                db.add(data_source)
                db.commit()
                
                self.logger.info(f"Saved property record: {property_id}")
                return property_id
                
        except Exception as e:
            self.logger.error(f"Error saving property record: {e}")
            return None
            
    def validate_4plex_property(self, property_data: Dict[str, Any]) -> bool:
        """Validate that property is a 4-plex/quadplex"""
        units = property_data.get('units', 0)
        property_type = property_data.get('property_type', '').lower()
        
        # Check unit count
        if units == 4:
            return True
            
        # Check property type keywords
        fourplex_keywords = [
            '4plex', '4-plex', 'fourplex', 'four-plex',
            'quadplex', 'quad-plex', '4 unit', '4-unit',
            'four unit', 'four-unit'
        ]
        
        return any(keyword in property_type for keyword in fourplex_keywords)
        
    async def process_batch(self, items: List[Dict[str, Any]], batch_size: int = 10) -> List[AgentResult]:
        """Process items in batches to avoid overwhelming services"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_tasks = [self.execute_task(item) for item in batch]
            
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Batch processing error: {result}")
                        results.append(AgentResult(
                            agent_name=self.name,
                            task_id=f"batch_{i}",
                            success=False,
                            data={},
                            message=f"Batch processing failed: {result}",
                            timestamp=datetime.utcnow(),
                            processing_time=0.0,
                            errors=[str(result)]
                        ))
                    else:
                        results.append(result)
                        
                # Add delay between batches
                if i + batch_size < len(items):
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Critical batch processing error: {e}")
                
        return results
        
    def log_performance(self, start_time: datetime, records_processed: int, task_name: str):
        """Log performance metrics"""
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        self.logger.info(f"""
        Performance Report - {task_name}:
        - Agent: {self.name}
        - Processing time: {processing_time:.2f} seconds
        - Records processed: {records_processed}
        - Rate: {records_processed / processing_time:.2f} records/second
        """)


class CollaborativeAgentMixin:
    """Mixin for agents that work collaboratively with other agents"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collaboration_history = []
        
    async def request_collaboration(self, target_agent: 'BaseForeclosureAgent', 
                                  task_data: Dict[str, Any]) -> AgentResult:
        """Request collaboration from another agent"""
        self.logger.info(f"Requesting collaboration from {target_agent.name}")
        
        try:
            result = await target_agent.execute_task(task_data)
            
            # Record collaboration
            self.collaboration_history.append({
                'timestamp': datetime.utcnow(),
                'target_agent': target_agent.name,
                'task_data': task_data,
                'success': result.success
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Collaboration failed with {target_agent.name}: {e}")
            return AgentResult(
                agent_name=target_agent.name,
                task_id=task_data.get('task_id', 'collab'),
                success=False,
                data={},
                message=f"Collaboration failed: {e}",
                timestamp=datetime.utcnow(),
                processing_time=0.0,
                errors=[str(e)]
            )