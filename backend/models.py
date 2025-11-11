"""
Unified Database Models for 4-Plex Investment Platform
Combines foreclosure discovery with multifamily valuation capabilities
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid

# Enums for standardized values
class PropertyType(str, Enum):
    FOURPLEX = "4-plex"
    FOURPLEX_ALT = "4plex"
    QUADPLEX = "quadplex" 
    FOURPLEX_WORD = "fourplex"
    MULTIFAMILY = "multifamily"
    DUPLEX = "duplex"
    TRIPLEX = "triplex"
    APARTMENT_COMPLEX = "apartment_complex"

class PropertyStatus(str, Enum):
    DISCOVERED = "discovered"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    UNDER_REVIEW = "under_review"
    OPPORTUNITY = "opportunity"
    ACQUIRED = "acquired"
    PASSED = "passed"
    ARCHIVED = "archived"

class ForeclosureStage(str, Enum):
    DISCOVERED = "discovered"
    PRE_FORECLOSURE = "pre-foreclosure"
    NOTICE_OF_DEFAULT = "notice_of_default"
    AUCTION = "auction"
    REO = "reo"
    SHORT_SALE = "short_sale"
    CASH_SALE = "cash_sale"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    OPPORTUNITY = "opportunity"

class InvestmentGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    D = "D"
    F = "F"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

# Core Property Model
class Property(BaseModel):
    """Unified property model supporting both foreclosure discovery and multifamily valuation"""
    
    # Basic Property Information
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    address: str
    city: str
    county: Optional[str] = None
    state: str = "GA"
    zip_code: Optional[str] = None
    
    # Property Classification
    property_type: PropertyType
    units: Optional[int] = None
    square_footage: Optional[int] = None
    lot_size: Optional[float] = None
    year_built: Optional[int] = None
    
    # Status and Discovery
    status: PropertyStatus = PropertyStatus.DISCOVERED
    discovered_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    data_sources: List[str] = Field(default_factory=list)
    
    # Foreclosure-Specific Data
    foreclosure_stage: Optional[ForeclosureStage] = None
    foreclosure_date: Optional[date] = None
    auction_date: Optional[date] = None
    notice_date: Optional[date] = None
    case_number: Optional[str] = None
    outstanding_debt: Optional[float] = None
    
    # Financial Data
    estimated_value: Optional[float] = None
    assessed_value: Optional[float] = None
    purchase_price: Optional[float] = None
    list_price: Optional[float] = None
    annual_taxes: Optional[float] = None
    
    # Investment Metrics (Basic)
    investment_score: Optional[float] = Field(None, ge=0, le=100)
    roi_estimate: Optional[float] = None
    cap_rate: Optional[float] = None
    
    # Additional Data
    agent_notes: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    documents: List[str] = Field(default_factory=list)
    
    # Metadata
    created_by: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

# Financial Metrics (from Multifamily App)
class FinancialMetrics(BaseModel):
    """Comprehensive financial analysis metrics"""
    
    # Purchase and Investment
    purchase_price: float
    closing_costs: Optional[float] = None
    renovation_costs: Optional[float] = None
    total_investment: float
    
    # Income Analysis
    gross_rental_income: Optional[float] = None
    other_income: Optional[float] = None
    total_income: Optional[float] = None
    vacancy_rate: Optional[float] = 0.05  # 5% default
    effective_gross_income: Optional[float] = None
    
    # Expense Analysis
    management_fees: Optional[float] = None
    maintenance_repairs: Optional[float] = None
    property_taxes: Optional[float] = None
    insurance: Optional[float] = None
    utilities: Optional[float] = None
    marketing: Optional[float] = None
    other_expenses: Optional[float] = None
    total_expenses: Optional[float] = None
    
    # Net Operating Income
    net_operating_income: float
    
    # Financing
    loan_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    loan_term: Optional[int] = None  # years
    annual_debt_service: Optional[float] = None
    
    # Key Performance Indicators
    cap_rate: Optional[float] = None
    cash_on_cash_return: Optional[float] = None
    debt_service_coverage_ratio: Optional[float] = None
    loan_to_value: Optional[float] = None
    internal_rate_of_return: Optional[float] = None
    
    # Cash Flow
    monthly_cash_flow: Optional[float] = None
    annual_cash_flow: Optional[float] = None
    
    # Calculated automatically
    @validator('total_investment', always=True)
    def calculate_total_investment(cls, v, values):
        purchase = values.get('purchase_price', 0)
        closing = values.get('closing_costs', 0) or 0
        renovation = values.get('renovation_costs', 0) or 0
        return purchase + closing + renovation
    
    @validator('effective_gross_income', always=True)
    def calculate_egi(cls, v, values):
        total_income = values.get('total_income', 0) or 0
        vacancy_rate = values.get('vacancy_rate', 0.05)
        return total_income * (1 - vacancy_rate)

# Financial Projections
class FinancialProjection(BaseModel):
    """Multi-year financial projections"""
    
    year: int
    gross_income: float
    total_expenses: float
    net_operating_income: float
    debt_service: Optional[float] = None
    cash_flow: float
    property_value: float
    appreciation_rate: Optional[float] = None
    
    # Assumptions
    income_growth_rate: Optional[float] = 0.03  # 3% default
    expense_growth_rate: Optional[float] = 0.025  # 2.5% default

# Property Analysis (Enhanced from Multifamily App)
class PropertyAnalysis(BaseModel):
    """Comprehensive property investment analysis"""
    
    # Basic Info
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    property_id: str
    analysis_type: str = "investment"
    generated_at: datetime = Field(default_factory=datetime.now)
    
    # Financial Analysis
    financial_metrics: FinancialMetrics
    projections: List[FinancialProjection] = Field(default_factory=list)
    
    # Market Analysis
    market_analysis: Dict[str, Any] = Field(default_factory=dict)
    comparable_properties: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Risk Assessment
    overall_risk: RiskLevel = RiskLevel.MEDIUM
    risk_factors: List[str] = Field(default_factory=list)
    risk_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Investment Recommendation
    investment_grade: Optional[InvestmentGrade] = None
    recommendation: Optional[str] = None
    confidence_level: Optional[float] = Field(None, ge=0, le=100)
    viability_score: Optional[float] = Field(None, ge=0, le=100)
    
    # AI Analysis (from Multifamily App)
    ai_insights: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    key_factors: List[str] = Field(default_factory=list)
    
    # Analysis Settings
    analysis_assumptions: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

# Document Processing (from Multifamily App)
class ProcessingFile(BaseModel):
    """File metadata for document processing"""
    
    filename: str
    original_name: str
    file_type: str
    file_size: int
    upload_time: datetime = Field(default_factory=datetime.now)
    processed: bool = False
    processing_status: Optional[str] = None
    extracted_data: Dict[str, Any] = Field(default_factory=dict)

class ProcessingJob(BaseModel):
    """Background job tracking for property analysis and document processing"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str  # discovery, analysis, processing, report
    status: str = "pending"  # pending, running, completed, failed
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    
    # Related entities
    property_id: Optional[str] = None
    files: List[ProcessingFile] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Results
    results: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    
    # Settings
    settings: Dict[str, Any] = Field(default_factory=dict)

# Discovery Job (Foreclosure-specific)
class DiscoveryJob(ProcessingJob):
    """Specialized job for property discovery"""
    
    job_type: str = "discovery"
    counties: List[str] = Field(default_factory=list)
    property_types: List[PropertyType] = Field(default_factory=list)
    max_results: int = 50
    search_parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Results
    properties_found: List[Property] = Field(default_factory=list)
    total_properties: int = 0

# User and Portfolio Management
class User(BaseModel):
    """User model with portfolio management"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: Optional[str] = None
    role: str = "investor"  # investor, analyst, admin
    
    # Preferences
    preferred_counties: List[str] = Field(default_factory=list)
    preferred_property_types: List[PropertyType] = Field(default_factory=list)
    investment_criteria: Dict[str, Any] = Field(default_factory=dict)
    
    # Portfolio
    properties: List[str] = Field(default_factory=list)  # Property IDs
    watchlist: List[str] = Field(default_factory=list)   # Property IDs
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True

# Activity Tracking
class ActivityLog(BaseModel):
    """System activity logging"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    activity_type: str  # discovery, analysis, report, etc.
    user_id: Optional[str] = None
    property_id: Optional[str] = None
    
    # Activity details
    title: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    status: str = "info"  # info, success, warning, error
    is_public: bool = True  # Whether to show in public activity feed

# Investment Report
class InvestmentReport(BaseModel):
    """Investment report generation model"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    property_id: str
    report_type: str = "comprehensive"  # summary, comprehensive, pitch_deck
    
    # Content
    executive_summary: Optional[str] = None
    financial_analysis: Optional[Dict[str, Any]] = None
    market_analysis: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    recommendations: List[str] = Field(default_factory=list)
    
    # Generation metadata
    generated_at: datetime = Field(default_factory=datetime.now)
    generated_by: Optional[str] = None
    template_used: Optional[str] = None
    
    # File outputs
    pdf_path: Optional[str] = None
    excel_path: Optional[str] = None
    powerpoint_path: Optional[str] = None
    
    # Settings used for generation
    report_settings: Dict[str, Any] = Field(default_factory=dict)

# System Configuration
class PlatformConfig(BaseModel):
    """Platform configuration and settings"""
    
    # Discovery settings
    default_counties: List[str] = Field(default_factory=lambda: ["Fulton", "DeKalb", "Gwinnett", "Cobb"])
    max_discovery_results: int = 100
    discovery_interval_hours: int = 24
    
    # Analysis settings
    default_cap_rate_threshold: float = 8.0
    default_roi_threshold: float = 15.0
    default_vacancy_rate: float = 0.05
    
    # AI settings
    ai_provider: str = "openai"  # openai, anthropic, local
    analysis_model: str = "gpt-4"
    max_ai_tokens: int = 4000
    
    # Notification settings
    email_notifications: bool = True
    webhook_urls: List[str] = Field(default_factory=list)
    
    # Export settings
    supported_export_formats: List[str] = Field(default_factory=lambda: ["pdf", "excel", "json", "csv"])
    report_template_dir: str = "/app/templates"
    
    # Database settings
    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    neo4j_url: Optional[str] = None

# Data validation and utility functions
def calculate_investment_score(financial_metrics: FinancialMetrics, market_data: Dict[str, Any] = None) -> float:
    """Calculate overall investment score (0-100)"""
    score = 0.0
    max_score = 100.0
    
    # Cap Rate Score (30 points)
    if financial_metrics.cap_rate:
        cap_rate_score = min(30, (financial_metrics.cap_rate / 12.0) * 30)
        score += cap_rate_score
    
    # Cash-on-Cash Return (25 points)
    if financial_metrics.cash_on_cash_return:
        coc_score = min(25, (financial_metrics.cash_on_cash_return / 20.0) * 25)
        score += coc_score
    
    # DSCR Score (20 points)
    if financial_metrics.debt_service_coverage_ratio:
        dscr_score = min(20, ((financial_metrics.debt_service_coverage_ratio - 1.0) / 0.5) * 20)
        score += dscr_score
    
    # LTV Score (15 points) - Lower LTV is better
    if financial_metrics.loan_to_value:
        ltv_score = max(0, 15 - (financial_metrics.loan_to_value / 100.0) * 15)
        score += ltv_score
    
    # Cash Flow Score (10 points)
    if financial_metrics.monthly_cash_flow:
        cf_score = min(10, (financial_metrics.monthly_cash_flow / 1000.0) * 10)
        score += cf_score
    
    return min(max_score, max(0.0, score))

def determine_investment_grade(score: float) -> InvestmentGrade:
    """Determine investment grade based on score"""
    if score >= 90:
        return InvestmentGrade.A_PLUS
    elif score >= 85:
        return InvestmentGrade.A
    elif score >= 80:
        return InvestmentGrade.B_PLUS
    elif score >= 75:
        return InvestmentGrade.B
    elif score >= 70:
        return InvestmentGrade.B_MINUS
    elif score >= 65:
        return InvestmentGrade.C_PLUS
    elif score >= 60:
        return InvestmentGrade.C
    elif score >= 50:
        return InvestmentGrade.D
    else:
        return InvestmentGrade.F

# Export the main models for easy importing
__all__ = [
    "Property",
    "FinancialMetrics", 
    "FinancialProjection",
    "PropertyAnalysis",
    "ProcessingJob",
    "DiscoveryJob",
    "ProcessingFile",
    "User",
    "ActivityLog",
    "InvestmentReport",
    "PlatformConfig",
    "PropertyType",
    "PropertyStatus", 
    "ForeclosureStage",
    "InvestmentGrade",
    "RiskLevel",
    "calculate_investment_score",
    "determine_investment_grade"
]