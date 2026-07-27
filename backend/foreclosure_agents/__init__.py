"""
4-Plex Foreclosure Research AI Agent System
Multi-agent framework using CrewAI for comprehensive property research
"""

from .data_collection.foreclosure_agent import ForeclosureDataAgent
from .data_collection.code_violation_agent import CodeViolationAgent  
from .data_collection.tax_lien_agent import TaxLienAgent
from .property_analysis.characteristics_agent import PropertyCharacteristicsAgent
from .property_analysis.market_analysis_agent import MarketAnalysisAgent
from .property_analysis.legal_compliance_agent import LegalComplianceAgent
from .automation.monitoring_agent import MonitoringAgent
from .automation.alert_agent import AlertAgent

__all__ = [
    'ForeclosureDataAgent',
    'CodeViolationAgent', 
    'TaxLienAgent',
    'PropertyCharacteristicsAgent',
    'MarketAnalysisAgent',
    'LegalComplianceAgent', 
    'MonitoringAgent',
    'AlertAgent'
]