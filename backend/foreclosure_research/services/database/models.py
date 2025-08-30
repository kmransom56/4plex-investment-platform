"""
Database Models for 4-Plex Foreclosure Research System
SQLAlchemy models for PostgreSQL database
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, JSON, Numeric, Date, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class PropertyStatus(enum.Enum):
    """Property status enumeration"""
    ACTIVE = "active"
    FORECLOSURE = "foreclosure" 
    TAX_LIEN = "tax_lien"
    CODE_VIOLATION = "code_violation"
    SOLD = "sold"
    ARCHIVED = "archived"


class ForeclosureStage(enum.Enum):
    """Foreclosure stage enumeration"""
    PRE_FORECLOSURE = "pre_foreclosure"
    NOTICE_OF_DEFAULT = "notice_of_default"
    LIS_PENDENS = "lis_pendens"
    AUCTION_SCHEDULED = "auction_scheduled"
    AUCTION_COMPLETED = "auction_completed"
    REO = "reo"


class PropertyRecord(Base):
    """Main property record table"""
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Property Information
    address = Column(String(255), nullable=False, index=True)
    city = Column(String(100))
    county = Column(String(50), nullable=False, index=True)
    state = Column(String(2), default="GA")
    zip_code = Column(String(10))
    
    # Property Identification
    parcel_number = Column(String(50), index=True)
    apn = Column(String(50))  # Assessor's Parcel Number
    legal_description = Column(Text)
    
    # Property Characteristics
    property_type = Column(String(50))
    units = Column(Integer, index=True)  # Focus on 4-unit properties
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    square_footage = Column(Integer)
    lot_size = Column(Float)
    year_built = Column(Integer)
    
    # Status and Classification
    status = Column(Enum(PropertyStatus), default=PropertyStatus.ACTIVE, index=True)
    foreclosure_stage = Column(Enum(ForeclosureStage))
    is_4plex = Column(Boolean, default=False, index=True)
    
    # Financial Information
    assessed_value = Column(Numeric(12, 2))
    market_value = Column(Numeric(12, 2))
    tax_amount = Column(Numeric(10, 2))
    amount_owed = Column(Numeric(12, 2))
    
    # Investment Analysis
    estimated_rental_income = Column(Numeric(10, 2))
    cap_rate = Column(Float)
    cash_flow_projection = Column(Numeric(10, 2))
    renovation_estimate = Column(Numeric(10, 2))
    investment_score = Column(Float)  # 0-100 scoring system
    
    # Owner Information
    owner_name = Column(String(255))
    owner_address = Column(String(255))
    owner_phone = Column(String(20))
    owner_email = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_verified = Column(DateTime)
    
    # Relationships
    foreclosure_records = relationship("ForeclosureRecord", back_populates="property")
    tax_records = relationship("TaxRecord", back_populates="property")
    code_violations = relationship("CodeViolation", back_populates="property")
    market_analyses = relationship("MarketAnalysis", back_populates="property")
    data_sources = relationship("DataSource", back_populates="property")


class ForeclosureRecord(Base):
    """Foreclosure tracking records"""
    __tablename__ = "foreclosure_records"
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    
    # Foreclosure Details
    foreclosure_type = Column(String(50))  # judicial, non-judicial, tax_sale
    case_number = Column(String(100))
    filing_date = Column(Date)
    sale_date = Column(Date)
    auction_date = Column(Date)
    
    # Legal Information
    lender_name = Column(String(255))
    attorney_name = Column(String(255))
    original_loan_amount = Column(Numeric(12, 2))
    outstanding_balance = Column(Numeric(12, 2))
    
    # Sale Information
    minimum_bid = Column(Numeric(12, 2))
    opening_bid = Column(Numeric(12, 2))
    final_bid = Column(Numeric(12, 2))
    winning_bidder = Column(String(255))
    
    # Status Tracking
    current_stage = Column(Enum(ForeclosureStage))
    is_cancelled = Column(Boolean, default=False)
    redemption_period_expires = Column(Date)
    
    # Documents and Links
    notice_document_url = Column(String(500))
    court_records_url = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship
    property = relationship("PropertyRecord", back_populates="foreclosure_records")


class TaxRecord(Base):
    """Tax lien and delinquency records"""
    __tablename__ = "tax_records"
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    
    # Tax Information
    tax_year = Column(Integer, nullable=False)
    assessed_value = Column(Numeric(12, 2))
    tax_amount = Column(Numeric(10, 2))
    amount_owed = Column(Numeric(10, 2))
    penalties = Column(Numeric(8, 2))
    interest = Column(Numeric(8, 2))
    total_due = Column(Numeric(10, 2))
    
    # Delinquency Status
    is_delinquent = Column(Boolean, default=False, index=True)
    years_delinquent = Column(Integer)
    delinquency_date = Column(Date)
    
    # Sale Information
    tax_sale_date = Column(Date)
    minimum_bid = Column(Numeric(10, 2))
    redemption_period = Column(Integer)  # months
    redemption_expires = Column(Date)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship
    property = relationship("PropertyRecord", back_populates="tax_records")


class CodeViolation(Base):
    """Code enforcement violations"""
    __tablename__ = "code_violations"
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    
    # Violation Information
    violation_type = Column(String(100))
    violation_code = Column(String(50))
    description = Column(Text)
    severity = Column(String(20))  # minor, major, critical
    
    # Status and Dates
    citation_date = Column(Date)
    compliance_deadline = Column(Date)
    resolution_date = Column(Date)
    is_resolved = Column(Boolean, default=False, index=True)
    
    # Financial Impact
    fine_amount = Column(Numeric(8, 2))
    court_costs = Column(Numeric(8, 2))
    total_amount = Column(Numeric(8, 2))
    
    # Case Information
    case_number = Column(String(100))
    inspector_name = Column(String(255))
    court_date = Column(Date)
    
    # Resolution Details
    resolution_method = Column(String(100))
    resolution_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship
    property = relationship("PropertyRecord", back_populates="code_violations")


class MarketAnalysis(Base):
    """Market analysis and investment metrics"""
    __tablename__ = "market_analyses"
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    
    # Market Data
    comparable_sales_count = Column(Integer)
    average_sale_price = Column(Numeric(12, 2))
    price_per_sqft = Column(Numeric(8, 2))
    days_on_market_average = Column(Integer)
    
    # Rental Analysis
    market_rent_per_unit = Column(Numeric(8, 2))
    total_monthly_rental = Column(Numeric(10, 2))
    annual_rental_income = Column(Numeric(12, 2))
    vacancy_rate = Column(Float)
    
    # Investment Metrics
    purchase_price_estimate = Column(Numeric(12, 2))
    renovation_cost_estimate = Column(Numeric(10, 2))
    total_investment = Column(Numeric(12, 2))
    projected_cap_rate = Column(Float)
    projected_cash_flow = Column(Numeric(8, 2))
    roi_percentage = Column(Float)
    
    # Risk Assessment
    neighborhood_score = Column(Float)  # 0-100
    crime_rate = Column(Float)
    school_rating = Column(Float)
    walkability_score = Column(Float)
    risk_level = Column(String(20))  # low, medium, high
    
    # Market Trends
    price_trend = Column(String(20))  # increasing, stable, decreasing
    rental_demand = Column(String(20))  # high, medium, low
    
    # Analysis Metadata
    analysis_date = Column(Date)
    data_sources = Column(JSON)
    confidence_score = Column(Float)  # 0-1
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship
    property = relationship("PropertyRecord", back_populates="market_analyses")


class DataSource(Base):
    """Track data sources and collection metadata"""
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    
    # Source Information
    source_name = Column(String(100), nullable=False)  # county_website, api, manual
    source_url = Column(String(500))
    source_type = Column(String(50))  # web_scraping, api, manual_entry
    
    # Collection Metadata
    collected_at = Column(DateTime, nullable=False)
    agent_name = Column(String(100))
    collection_method = Column(String(100))
    
    # Data Quality
    data_completeness = Column(Float)  # 0-1
    data_accuracy = Column(Float)  # 0-1
    verification_status = Column(String(50))  # verified, pending, failed
    
    # Raw Data Storage
    raw_data = Column(JSON)
    processed_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationship
    property = relationship("PropertyRecord", back_populates="data_sources")


class AgentTask(Base):
    """Agent task tracking and performance"""
    __tablename__ = "agent_tasks"
    
    id = Column(Integer, primary_key=True)
    
    # Task Information
    task_id = Column(String(100), unique=True, nullable=False)
    agent_name = Column(String(100), nullable=False)
    task_type = Column(String(50))  # data_collection, analysis, monitoring
    task_description = Column(Text)
    
    # Execution Details
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    status = Column(String(20))  # pending, running, completed, failed
    
    # Performance Metrics
    records_processed = Column(Integer)
    records_created = Column(Integer)
    records_updated = Column(Integer)
    error_count = Column(Integer)
    
    # Results
    result_data = Column(JSON)
    error_messages = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())


class SystemAlert(Base):
    """System alerts and notifications"""
    __tablename__ = "system_alerts"
    
    id = Column(Integer, primary_key=True)
    
    # Alert Information
    alert_type = Column(String(50))  # new_property, price_drop, urgent
    severity = Column(String(20))  # low, medium, high, critical
    title = Column(String(255))
    message = Column(Text)
    
    # Related Data
    property_id = Column(Integer, ForeignKey("properties.id"))
    agent_name = Column(String(100))
    
    # Status
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    action_taken = Column(String(100))
    
    # Delivery
    notification_channels = Column(JSON)  # email, slack, webhook
    sent_at = Column(DateTime)
    
    # Timestamps  
    created_at = Column(DateTime, server_default=func.now())


# Indexes for performance
from sqlalchemy import Index

Index('idx_properties_county_status', PropertyRecord.county, PropertyRecord.status)
Index('idx_properties_4plex_status', PropertyRecord.is_4plex, PropertyRecord.status)
Index('idx_foreclosure_stage_date', ForeclosureRecord.current_stage, ForeclosureRecord.sale_date)
Index('idx_tax_delinquent_county', TaxRecord.is_delinquent, PropertyRecord.county)
Index('idx_violations_unresolved', CodeViolation.is_resolved, CodeViolation.citation_date)