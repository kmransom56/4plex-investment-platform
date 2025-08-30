"""
Unified Data Models for Integrated Property System
Harmonizes data structures between foreclosure research and valuation systems
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PropertySource(str, Enum):
    """Property discovery source"""
    FORECLOSURE_DISCOVERY = "foreclosure_discovery"
    MANUAL_ENTRY = "manual_entry"
    API_IMPORT = "api_import"
    MARKET_SCAN = "market_scan"


class PropertyType(str, Enum):
    """Property type classification"""
    FOURPLEX = "4plex"
    MULTIFAMILY = "multifamily"
    COMMERCIAL = "commercial"
    MIXED_USE = "mixed_use"
    OTHER = "other"


class ForeclosureStatus(str, Enum):
    """Foreclosure process status"""
    PRE_FORECLOSURE = "pre_foreclosure"
    NOTICE_OF_DEFAULT = "notice_of_default"
    LIS_PENDENS = "lis_pendens"
    AUCTION_SCHEDULED = "auction_scheduled"
    AUCTION_COMPLETED = "auction_completed"
    REO = "reo"
    TAX_SALE = "tax_sale"
    NONE = "none"


class ProcessingStatus(str, Enum):
    """Property processing pipeline status"""
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    ENRICHED = "enriched"
    ANALYZED = "analyzed"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    """Investment risk assessment"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UnifiedProperty(BaseModel):
    """Unified property model combining foreclosure and valuation data"""
    
    # Core Identification
    id: str = Field(..., description="Unique property identifier")
    source: PropertySource = Field(..., description="How property was discovered")
    
    # Basic Information
    name: str = Field(..., description="Property name or identifier")
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    county: str = Field(..., description="County (Georgia)")
    state: str = Field(default="GA", description="State")
    zip_code: Optional[str] = Field(None, description="ZIP code")
    parcel_number: Optional[str] = Field(None, description="Assessor parcel number")
    
    # Property Characteristics
    property_type: PropertyType = Field(default=PropertyType.FOURPLEX, description="Property type")
    units: int = Field(..., description="Number of units")
    bedrooms: Optional[int] = Field(None, description="Total bedrooms")
    bathrooms: Optional[float] = Field(None, description="Total bathrooms")
    square_footage: Optional[int] = Field(None, description="Total square footage")
    lot_size: Optional[float] = Field(None, description="Lot size in acres")
    year_built: Optional[int] = Field(None, description="Year built")
    
    # Financial Data
    asking_price: Optional[float] = Field(None, description="Listed asking price")
    assessed_value: Optional[float] = Field(None, description="Tax assessed value")
    market_value: Optional[float] = Field(None, description="Estimated market value")
    amount_owed: Optional[float] = Field(None, description="Amount owed (foreclosure/liens)")
    
    # Foreclosure Information
    foreclosure_status: Optional[ForeclosureStatus] = Field(None, description="Foreclosure status")
    foreclosure_stage: Optional[str] = Field(None, description="Current foreclosure stage")
    sale_date: Optional[datetime] = Field(None, description="Scheduled sale date")
    redemption_period: Optional[str] = Field(None, description="Redemption period info")
    auction_minimum_bid: Optional[float] = Field(None, description="Minimum auction bid")
    
    # Code Violations
    has_code_violations: bool = Field(default=False, description="Has active code violations")
    violation_count: int = Field(default=0, description="Number of violations")
    violation_types: List[str] = Field(default=[], description="Types of violations")
    violation_severity: Optional[str] = Field(None, description="Severity level")
    
    # Investment Analysis
    cap_rate: Optional[float] = Field(None, description="Capitalization rate")
    noi: Optional[float] = Field(None, description="Net Operating Income")
    gross_income: Optional[float] = Field(None, description="Gross rental income")
    operating_expenses: Optional[float] = Field(None, description="Operating expenses")
    cash_flow: Optional[float] = Field(None, description="Monthly cash flow")
    cash_on_cash_return: Optional[float] = Field(None, description="Cash-on-cash return")
    irr: Optional[float] = Field(None, description="Internal rate of return")
    
    # Scoring and Risk
    investment_score: Optional[float] = Field(None, ge=0, le=100, description="Investment score (0-100)")
    viability_score: Optional[float] = Field(None, ge=0, le=100, description="Viability score from valuation")
    risk_level: Optional[RiskLevel] = Field(None, description="Overall risk assessment")
    confidence_level: Optional[float] = Field(None, ge=0, le=1, description="Confidence in analysis")
    
    # Processing Status
    discovery_status: ProcessingStatus = Field(..., description="Discovery pipeline status")
    valuation_status: Optional[str] = Field(None, description="Valuation processing status")
    
    # Market Context
    neighborhood_score: Optional[float] = Field(None, description="Neighborhood quality score")
    crime_rate: Optional[float] = Field(None, description="Local crime rate")
    school_rating: Optional[float] = Field(None, description="School district rating")
    walkability_score: Optional[float] = Field(None, description="Walkability score")
    
    # Owner Information
    owner_name: Optional[str] = Field(None, description="Property owner name")
    owner_address: Optional[str] = Field(None, description="Owner mailing address")
    owner_phone: Optional[str] = Field(None, description="Owner phone number")
    
    # Timestamps
    discovered_at: datetime = Field(..., description="When property was discovered")
    analyzed_at: Optional[datetime] = Field(None, description="When valuation analysis completed")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Metadata
    data_sources: List[str] = Field(default=[], description="List of data sources")
    processing_notes: Optional[str] = Field(None, description="Processing notes and flags")
    
    @validator('units')
    def validate_4plex(cls, v):
        """Ensure we're focusing on 4-plex properties"""
        if v != 4:
            raise ValueError("This system is designed for 4-plex properties only")
        return v
        
    @validator('county')
    def validate_georgia_county(cls, v):
        """Validate Georgia county"""
        valid_counties = ['Fulton', 'DeKalb', 'Clayton', 'Cobb', 'Atlanta']
        if v not in valid_counties:
            raise ValueError(f"County must be one of: {valid_counties}")
        return v


class IntegratedAnalysis(BaseModel):
    """Comprehensive analysis combining foreclosure research and valuation"""
    
    id: str = Field(..., description="Analysis ID")
    property_id: str = Field(..., description="Associated property ID")
    
    # Analysis Metadata
    analysis_date: datetime = Field(default_factory=datetime.utcnow)
    analyst: str = Field(default="AI_SYSTEM", description="Who performed analysis")
    confidence_score: float = Field(..., ge=0, le=1, description="Analysis confidence")
    
    # Foreclosure Analysis
    foreclosure_opportunity_score: float = Field(..., ge=0, le=100)
    foreclosure_risk_factors: List[str] = Field(default=[])
    legal_complexity_score: float = Field(..., ge=0, le=100)
    timeline_to_acquisition: Optional[str] = Field(None)
    
    # Financial Analysis  
    acquisition_cost_estimate: float = Field(..., description="Estimated total acquisition cost")
    renovation_cost_estimate: float = Field(..., description="Estimated renovation costs")
    total_investment_required: float = Field(..., description="Total capital required")
    
    # Return Projections
    projected_annual_income: float = Field(..., description="Projected gross annual income")
    projected_monthly_cashflow: float = Field(..., description="Projected monthly cash flow")
    projected_cap_rate: float = Field(..., description="Projected cap rate")
    projected_irr: float = Field(..., description="Projected IRR")
    payback_period_years: float = Field(..., description="Investment payback period")
    
    # Risk Assessment
    overall_risk_score: float = Field(..., ge=0, le=100, description="Overall risk score")
    risk_categories: Dict[str, float] = Field(default={}, description="Risk breakdown by category")
    mitigation_strategies: List[str] = Field(default=[], description="Recommended risk mitigation")
    
    # Market Analysis
    comparable_properties: List[Dict[str, Any]] = Field(default=[], description="Comparable property analysis")
    market_trends: Dict[str, Any] = Field(default={}, description="Market trend analysis")
    competitive_advantages: List[str] = Field(default=[], description="Competitive advantages")
    
    # Recommendations
    investment_recommendation: str = Field(..., description="Buy/Hold/Pass recommendation")
    reasoning: List[str] = Field(default=[], description="Reasoning for recommendation")
    next_steps: List[str] = Field(default=[], description="Recommended next steps")
    
    # Additional Considerations
    financing_options: List[Dict[str, Any]] = Field(default=[], description="Available financing")
    tax_implications: Dict[str, Any] = Field(default={}, description="Tax considerations")
    exit_strategies: List[str] = Field(default=[], description="Potential exit strategies")


# SQLAlchemy Database Models
class UnifiedPropertyDB(Base):
    """SQLAlchemy model for unified property data"""
    __tablename__ = "unified_properties"
    
    id = Column(String, primary_key=True)
    source = Column(SQLEnum(PropertySource), nullable=False)
    
    # Basic info
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100))
    county = Column(String(50), nullable=False)
    state = Column(String(2), default="GA")
    zip_code = Column(String(10))
    parcel_number = Column(String(50))
    
    # Characteristics
    property_type = Column(SQLEnum(PropertyType), default=PropertyType.FOURPLEX)
    units = Column(Integer, nullable=False)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    square_footage = Column(Integer)
    lot_size = Column(Float)
    year_built = Column(Integer)
    
    # Financial
    asking_price = Column(Float)
    assessed_value = Column(Float)
    market_value = Column(Float)
    amount_owed = Column(Float)
    
    # Foreclosure
    foreclosure_status = Column(SQLEnum(ForeclosureStatus))
    foreclosure_stage = Column(String(100))
    sale_date = Column(DateTime)
    redemption_period = Column(String(255))
    
    # Violations
    has_code_violations = Column(Boolean, default=False)
    violation_count = Column(Integer, default=0)
    violation_types = Column(JSON)
    
    # Investment metrics
    cap_rate = Column(Float)
    noi = Column(Float)
    gross_income = Column(Float)
    operating_expenses = Column(Float)
    cash_flow = Column(Float)
    investment_score = Column(Float)
    risk_level = Column(SQLEnum(RiskLevel))
    
    # Status
    discovery_status = Column(SQLEnum(ProcessingStatus), nullable=False)
    valuation_status = Column(String(50))
    
    # Timestamps
    discovered_at = Column(DateTime, nullable=False)
    analyzed_at = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    analyses = relationship("IntegratedAnalysisDB", back_populates="property")


class IntegratedAnalysisDB(Base):
    """SQLAlchemy model for integrated analysis"""
    __tablename__ = "integrated_analyses"
    
    id = Column(String, primary_key=True)
    property_id = Column(String, ForeignKey("unified_properties.id"), nullable=False)
    
    analysis_date = Column(DateTime, default=datetime.utcnow)
    analyst = Column(String(100), default="AI_SYSTEM")
    confidence_score = Column(Float)
    
    # Scores
    foreclosure_opportunity_score = Column(Float)
    legal_complexity_score = Column(Float)
    overall_risk_score = Column(Float)
    
    # Financial projections
    acquisition_cost_estimate = Column(Float)
    renovation_cost_estimate = Column(Float)
    total_investment_required = Column(Float)
    projected_annual_income = Column(Float)
    projected_monthly_cashflow = Column(Float)
    projected_cap_rate = Column(Float)
    projected_irr = Column(Float)
    
    # Analysis data
    risk_categories = Column(JSON)
    comparable_properties = Column(JSON)
    market_trends = Column(JSON)
    financing_options = Column(JSON)
    
    # Recommendations
    investment_recommendation = Column(String(20))
    reasoning = Column(JSON)
    next_steps = Column(JSON)
    
    # Relationship
    property = relationship("UnifiedPropertyDB", back_populates="analyses")


class WorkflowJob(Base):
    """Track integrated workflow jobs"""
    __tablename__ = "workflow_jobs"
    
    id = Column(String, primary_key=True)
    property_id = Column(String, ForeignKey("unified_properties.id"))
    job_type = Column(String(50))  # discovery, validation, enrichment, analysis
    status = Column(String(20))    # pending, running, completed, failed
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    result_data = Column(JSON)
    
    # Processing metrics
    processing_time_seconds = Column(Float)
    records_processed = Column(Integer)
    confidence_score = Column(Float)