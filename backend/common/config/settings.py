"""
Configuration Settings for 4-Plex Foreclosure Research System
Centralized configuration management using Pydantic
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Configuration
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    HOST: str = Field(default="0.0.0.0", description="Application host")
    PORT: int = Field(default=11050, description="Application port")
    
    # AI and LLM Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    VLLM_GATEWAY_URL: str = Field(default="http://localhost:9000", description="vLLM AI Gateway URL")
    AI_STACK_API_KEY: str = Field(default="vllm-key", description="AI Stack API key")
    
    # Real Estate API Keys
    PROPERTYRADAR_API_KEY: Optional[str] = Field(default=None, description="PropertyRadar API key")
    PROPERTYRADAR_BASE_URL: str = Field(default="https://api.propertyradar.com", description="PropertyRadar base URL")
    
    REALESTATE_API_KEY: Optional[str] = Field(default=None, description="RealEstate API key")
    REALESTATE_BASE_URL: str = Field(default="https://api.realestateapi.com", description="RealEstate API base URL")
    
    ATTOM_API_KEY: Optional[str] = Field(default=None, description="ATTOM Data API key")
    ATTOM_BASE_URL: str = Field(default="https://api.gateway.attomdata.com", description="ATTOM Data base URL")
    
    # Scraping Configuration
    SCRAPERAPI_KEY: Optional[str] = Field(default=None, description="ScraperAPI key")
    SCRAPERAPI_BASE_URL: str = Field(default="https://api.scraperapi.com", description="ScraperAPI base URL")
    
    USER_AGENTS: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36|Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36|Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        description="Pipe-separated user agents for web scraping"
    )
    
    # Proxy Settings
    PROXY_HOST: Optional[str] = Field(default=None, description="Proxy host")
    PROXY_PORT: Optional[int] = Field(default=None, description="Proxy port")
    PROXY_USERNAME: Optional[str] = Field(default=None, description="Proxy username")
    PROXY_PASSWORD: Optional[str] = Field(default=None, description="Proxy password")
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql://foreclosure_user:foreclosure_pass@localhost:5432/foreclosure_db",
        description="PostgreSQL database URL"
    )
    NEO4J_URL: str = Field(default="bolt://localhost:7687", description="Neo4j database URL")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="password", description="Neo4j password")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    
    # County-Specific URLs
    # Fulton County
    FULTON_TAX_SALES_URL: str = Field(
        default="https://fultoncountyga.gov/inside-fulton-county/fulton-county-departments/sheriff/tax-sales",
        description="Fulton County tax sales URL"
    )
    FULTON_CODE_ENFORCEMENT_URL: str = Field(
        default="https://www.fultoncountyga.gov/services/public-safety/code-enforcement",
        description="Fulton County code enforcement URL"
    )
    
    # DeKalb County
    DEKALB_TAX_SALES_URL: str = Field(
        default="https://dekalbtax.org/tax-sales-general-information",
        description="DeKalb County tax sales URL"
    )
    DEKALB_FORECLOSURE_REGISTRY_URL: str = Field(
        default="https://www.dekalbcountyga.gov/beautification/foreclosure-registry-faq",
        description="DeKalb County foreclosure registry URL"
    )
    DEKALB_CODE_ENFORCEMENT_URL: str = Field(
        default="https://www.dekalbcountyga.gov/beautification/code-enforcement-general-information",
        description="DeKalb County code enforcement URL"
    )
    
    # City of Atlanta
    ATLANTA_MUNICIPAL_COURT_URL: str = Field(
        default="https://atlantaga.gov/government/departments/municipal-court",
        description="Atlanta municipal court URL"
    )
    
    # Clayton County
    CLAYTON_TAX_SALES_URL: str = Field(
        default="https://publicaccess.claytoncountyga.gov",
        description="Clayton County tax sales URL"
    )
    CLAYTON_TAX_LISTING_URL: str = Field(
        default="https://publicaccess.claytoncountyga.gov/content/PDF",
        description="Clayton County tax listing URL"
    )
    
    # Cobb County
    COBB_CODE_ENFORCEMENT_URL: str = Field(
        default="http://cobbcounty.elaws.us/code",
        description="Cobb County code enforcement URL"
    )
    
    # Web Scraping Settings
    SCRAPING_DELAY_MIN: int = Field(default=1, description="Minimum delay between requests (seconds)")
    SCRAPING_DELAY_MAX: int = Field(default=5, description="Maximum delay between requests (seconds)")
    MAX_CONCURRENT_REQUESTS: int = Field(default=5, description="Maximum concurrent requests")
    REQUEST_TIMEOUT: int = Field(default=30, description="Request timeout (seconds)")
    MAX_RETRIES: int = Field(default=3, description="Maximum number of retries")
    
    # Monitoring and Alerting
    SLACK_WEBHOOK_URL: Optional[str] = Field(default=None, description="Slack webhook URL")
    EMAIL_SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP host")
    EMAIL_SMTP_PORT: int = Field(default=587, description="SMTP port")
    EMAIL_USERNAME: Optional[str] = Field(default=None, description="Email username")
    EMAIL_PASSWORD: Optional[str] = Field(default=None, description="Email password")
    EMAIL_RECIPIENTS: str = Field(default="", description="Comma-separated email recipients")
    
    # Background Task Configuration
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", description="Celery result backend URL")
    
    # Data Collection Schedules (cron format)
    FORECLOSURE_DATA_SCHEDULE: str = Field(default="0 8 * * *", description="Foreclosure data collection schedule")
    CODE_VIOLATION_SCHEDULE: str = Field(default="0 12 * * *", description="Code violation collection schedule")
    TAX_LIEN_SCHEDULE: str = Field(default="0 16 * * *", description="Tax lien collection schedule")
    MARKET_ANALYSIS_SCHEDULE: str = Field(default="0 20 * * 1", description="Market analysis schedule")
    
    # Property Filtering Criteria
    MIN_UNITS: int = Field(default=4, description="Minimum number of units")
    MAX_UNITS: int = Field(default=4, description="Maximum number of units")
    MIN_SQUARE_FOOTAGE: int = Field(default=2000, description="Minimum square footage")
    MAX_PRICE: float = Field(default=500000, description="Maximum property price")
    TARGET_COUNTIES: str = Field(default="Fulton,DeKalb,Clayton,Cobb,Atlanta", description="Target counties")
    
    # Investment Analysis Parameters
    MIN_CAP_RATE: float = Field(default=0.08, description="Minimum cap rate")
    MAX_RENOVATION_COST: float = Field(default=50000, description="Maximum renovation cost")
    MIN_CASH_FLOW: float = Field(default=500, description="Minimum monthly cash flow")
    MARKET_RENT_BUFFER: float = Field(default=0.1, description="Market rent buffer percentage")
    
    # Legal and Compliance
    TERMS_OF_SERVICE_COMPLIANCE: bool = Field(default=True, description="Terms of service compliance")
    RESPECT_ROBOTS_TXT: bool = Field(default=True, description="Respect robots.txt")
    DATA_RETENTION_DAYS: int = Field(default=365, description="Data retention period in days")
    PRIVACY_MODE: str = Field(default="enabled", description="Privacy mode")
    
    @validator('EMAIL_RECIPIENTS')
    def validate_email_recipients(cls, v):
        """Validate email recipients format"""
        if v:
            emails = [email.strip() for email in v.split(',')]
            for email in emails:
                if email and '@' not in email:
                    raise ValueError(f"Invalid email format: {email}")
        return v
    
    @validator('TARGET_COUNTIES')
    def validate_target_counties(cls, v):
        """Validate target counties"""
        valid_counties = ['Fulton', 'DeKalb', 'Clayton', 'Cobb', 'Atlanta']
        counties = [county.strip() for county in v.split(',')]
        for county in counties:
            if county not in valid_counties:
                raise ValueError(f"Invalid county: {county}. Valid counties: {valid_counties}")
        return v
    
    @property
    def user_agent_list(self) -> List[str]:
        """Get list of user agents"""
        return self.USER_AGENTS.split('|')
    
    @property
    def target_county_list(self) -> List[str]:
        """Get list of target counties"""
        return [county.strip() for county in self.TARGET_COUNTIES.split(',')]
    
    @property
    def email_recipient_list(self) -> List[str]:
        """Get list of email recipients"""
        if not self.EMAIL_RECIPIENTS:
            return []
        return [email.strip() for email in self.EMAIL_RECIPIENTS.split(',') if email.strip()]
    
    @property
    def proxy_config(self) -> Optional[dict]:
        """Get proxy configuration"""
        if not self.PROXY_HOST:
            return None
        
        config = {
            'host': self.PROXY_HOST,
            'port': self.PROXY_PORT or 8080
        }
        
        if self.PROXY_USERNAME and self.PROXY_PASSWORD:
            config['auth'] = (self.PROXY_USERNAME, self.PROXY_PASSWORD)
            
        return config
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        validate_default = True


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


# Development/Testing settings override
class TestSettings(Settings):
    """Test-specific settings"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "postgresql://test_user:test_pass@localhost:5432/test_foreclosure_db"
    NEO4J_URL: str = "bolt://localhost:7687"
    NEO4J_PASSWORD: str = "test_password"
    REDIS_URL: str = "redis://localhost:6379/15"
    
    # Faster schedules for testing
    FORECLOSURE_DATA_SCHEDULE: str = "*/5 * * * *"  # Every 5 minutes
    CODE_VIOLATION_SCHEDULE: str = "*/10 * * * *"   # Every 10 minutes
    TAX_LIEN_SCHEDULE: str = "*/15 * * * *"         # Every 15 minutes
    
    # Lower thresholds for testing
    MIN_CAP_RATE: float = 0.05
    MIN_CASH_FLOW: float = 100
    MAX_PRICE: float = 100000


def get_test_settings() -> TestSettings:
    """Get test settings"""
    return TestSettings()