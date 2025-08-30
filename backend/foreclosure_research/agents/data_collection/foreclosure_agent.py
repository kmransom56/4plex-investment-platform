"""
Foreclosure Data Agent for 4-Plex Foreclosure Research System
Specialized agent for collecting foreclosure data from Georgia county sources
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ..base_agent import BaseForeclosureAgent, AgentResult
from services.scraping.web_scraper import WebScraper
from services.apis.property_api import PropertyAPIClient
from config.settings import Settings


class ForeclosureDataAgent(BaseForeclosureAgent):
    """Agent specialized in collecting foreclosure data from multiple Georgia county sources"""
    
    def __init__(self, settings: Settings):
        super().__init__("ForeclosureDataAgent", settings)
        self.web_scraper = WebScraper(settings)
        self.property_api = PropertyAPIClient(settings)
        
        # County-specific configuration
        self.county_configs = {
            'fulton': {
                'name': 'Fulton County',
                'tax_sales_url': settings.FULTON_TAX_SALES_URL,
                'sheriff_url': 'https://fultoncountyga.gov/inside-fulton-county/fulton-county-departments/sheriff',
                'search_patterns': [r'4.*plex', r'quadplex', r'4.*unit'],
                'date_format': '%B %d, %Y'
            },
            'dekalb': {
                'name': 'DeKalb County', 
                'tax_sales_url': settings.DEKALB_TAX_SALES_URL,
                'foreclosure_registry_url': settings.DEKALB_FORECLOSURE_REGISTRY_URL,
                'search_patterns': [r'4.*plex', r'quadplex', r'4.*unit'],
                'date_format': '%m/%d/%Y'
            },
            'clayton': {
                'name': 'Clayton County',
                'tax_sales_url': settings.CLAYTON_TAX_SALES_URL,
                'listing_url': settings.CLAYTON_TAX_LISTING_URL,
                'search_patterns': [r'4.*plex', r'quadplex', r'4.*unit'],
                'date_format': '%m/%d/%Y'
            },
            'atlanta': {
                'name': 'City of Atlanta',
                'municipal_court_url': settings.ATLANTA_MUNICIPAL_COURT_URL,
                'search_patterns': [r'4.*plex', r'quadplex', r'4.*unit'],
                'date_format': '%B %d, %Y'
            },
            'cobb': {
                'name': 'Cobb County',
                'code_enforcement_url': settings.COBB_CODE_ENFORCEMENT_URL,
                'search_patterns': [r'4.*plex', r'quadplex', r'4.*unit'],
                'date_format': '%m/%d/%Y'
            }
        }
        
    def _get_agent_role(self) -> str:
        return "Foreclosure Data Specialist"
        
    def _get_agent_goal(self) -> str:
        return "Monitor and collect foreclosure data for 4-plex properties across Georgia counties, tracking tax sales, sheriff sales, and court filings with precise data extraction and validation"
        
    def _get_agent_backstory(self) -> str:
        return """You are an expert foreclosure data analyst with deep knowledge of Georgia real estate law and county-specific foreclosure processes. You specialize in identifying 4-plex properties in various stages of foreclosure, from initial notices to auction sales. Your expertise includes understanding legal terminology, parsing court documents, and extracting key data points for investment analysis."""
        
    async def execute_task(self, task_data: Dict[str, Any]) -> AgentResult:
        """Execute foreclosure data collection task"""
        start_time = datetime.utcnow()
        task_id = task_data.get('task_id', f"foreclosure_{int(start_time.timestamp())}")
        county = task_data.get('county', 'all')
        
        self.logger.info(f"Starting foreclosure data collection for county: {county}")
        
        try:
            if county == 'all':
                # Collect from all counties
                all_results = []
                for county_key in self.county_configs.keys():
                    county_data = await self._collect_county_data(county_key)
                    all_results.extend(county_data)
            else:
                # Collect from specific county
                all_results = await self._collect_county_data(county)
                
            # Filter for 4-plex properties
            fourplex_results = []
            for result in all_results:
                if self.validate_4plex_property(result):
                    property_id = await self.save_property_record(result, f"{county}_foreclosure")
                    if property_id:
                        result['property_id'] = property_id
                        fourplex_results.append(result)
                        
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.log_performance(start_time, len(fourplex_results), "Foreclosure Data Collection")
            
            return AgentResult(
                agent_name=self.name,
                task_id=task_id,
                success=True,
                data={'properties': fourplex_results},
                message=f"Successfully collected {len(fourplex_results)} 4-plex foreclosure properties",
                timestamp=datetime.utcnow(),
                processing_time=processing_time,
                records_processed=len(fourplex_results)
            )
            
        except Exception as e:
            self.logger.error(f"Foreclosure data collection failed: {e}")
            return AgentResult(
                agent_name=self.name,
                task_id=task_id,
                success=False,
                data={},
                message=f"Foreclosure data collection failed: {str(e)}",
                timestamp=datetime.utcnow(),
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                errors=[str(e)]
            )
            
    async def _collect_county_data(self, county: str) -> List[Dict[str, Any]]:
        """Collect foreclosure data for a specific county"""
        config = self.county_configs.get(county)
        if not config:
            self.logger.warning(f"No configuration found for county: {county}")
            return []
            
        self.logger.info(f"Collecting data for {config['name']}")
        
        results = []
        
        # Collect tax sale data
        tax_sale_data = await self._collect_tax_sales(county, config)
        results.extend(tax_sale_data)
        
        # Collect foreclosure registry data (if available)
        if 'foreclosure_registry_url' in config:
            registry_data = await self._collect_foreclosure_registry(county, config)
            results.extend(registry_data)
            
        # Collect sheriff sale data
        sheriff_data = await self._collect_sheriff_sales(county, config)
        results.extend(sheriff_data)
        
        return results
        
    async def _collect_tax_sales(self, county: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect tax sale listings"""
        self.logger.info(f"Collecting tax sales for {config['name']}")
        
        try:
            # Handle different county formats
            if county == 'clayton':
                return await self._collect_clayton_tax_sales(config)
            elif county == 'fulton':
                return await self._collect_fulton_tax_sales(config)
            elif county == 'dekalb':
                return await self._collect_dekalb_tax_sales(config)
            else:
                return await self._collect_generic_tax_sales(county, config)
                
        except Exception as e:
            self.logger.error(f"Tax sale collection failed for {county}: {e}")
            return []
            
    async def _collect_clayton_tax_sales(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect Clayton County tax sale data (PDF format)"""
        results = []
        
        try:
            # Get current month's tax sale listing
            current_date = datetime.now()
            months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                     'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
            
            # Try current and next month
            for month_offset in [0, 1]:
                target_date = current_date + timedelta(days=30 * month_offset)
                month_name = months[target_date.month - 1]
                year = target_date.year
                
                pdf_url = f"{config['listing_url']}/{month_name} {year} TAX SALE LISTING.pdf"
                
                # Use web scraper to download and parse PDF
                pdf_data = await self.web_scraper.download_pdf(pdf_url)
                if pdf_data:
                    properties = self._parse_clayton_pdf(pdf_data, config['name'])
                    results.extend(properties)
                    
        except Exception as e:
            self.logger.error(f"Clayton tax sale collection error: {e}")
            
        return results
        
    async def _collect_fulton_tax_sales(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect Fulton County tax sale data (web scraping)"""
        results = []
        
        try:
            html_content = await self.web_scraper.get_page_content(config['tax_sales_url'])
            if not html_content:
                return results
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for property listings
            property_elements = soup.find_all(['div', 'table', 'tr'], 
                                            class_=re.compile(r'property|listing|sale'))
            
            for element in property_elements:
                property_data = self._extract_property_data(element, config['name'])
                if property_data and self._matches_4plex_patterns(property_data, config):
                    results.append(property_data)
                    
        except Exception as e:
            self.logger.error(f"Fulton tax sale collection error: {e}")
            
        return results
        
    async def _collect_dekalb_tax_sales(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect DeKalb County tax sale data"""
        results = []
        
        try:
            # Use Selenium for dynamic content
            driver = self._get_selenium_driver()
            
            try:
                driver.get(config['tax_sales_url'])
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Look for property listings
                property_elements = driver.find_elements(By.CSS_SELECTOR, 
                                                       '[class*="property"], [class*="listing"]')
                
                for element in property_elements:
                    property_data = self._extract_selenium_property_data(element, config['name'])
                    if property_data and self._matches_4plex_patterns(property_data, config):
                        results.append(property_data)
                        
            finally:
                driver.quit()
                
        except Exception as e:
            self.logger.error(f"DeKalb tax sale collection error: {e}")
            
        return results
        
    async def _collect_generic_tax_sales(self, county: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generic tax sale collection for other counties"""
        results = []
        
        try:
            html_content = await self.web_scraper.get_page_content(config['tax_sales_url'])
            if not html_content:
                return results
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Generic property extraction
            property_elements = soup.find_all(text=re.compile(r'address|property|sale'))
            
            for element in property_elements:
                parent = element.parent
                property_data = self._extract_property_data(parent, config['name'])
                if property_data and self._matches_4plex_patterns(property_data, config):
                    results.append(property_data)
                    
        except Exception as e:
            self.logger.error(f"Generic tax sale collection error for {county}: {e}")
            
        return results
        
    async def _collect_foreclosure_registry(self, county: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect foreclosure registry data"""
        # Implementation for foreclosure registry collection
        # This would be specific to counties that maintain registries
        return []
        
    async def _collect_sheriff_sales(self, county: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect sheriff sale data"""
        # Implementation for sheriff sale collection
        return []
        
    def _parse_clayton_pdf(self, pdf_data: bytes, county: str) -> List[Dict[str, Any]]:
        """Parse Clayton County PDF tax sale listings"""
        # Implementation for PDF parsing
        # Would use PyPDF2 or pdfplumber to extract property data
        return []
        
    def _extract_property_data(self, element: Any, county: str) -> Optional[Dict[str, Any]]:
        """Extract property data from HTML element"""
        try:
            text_content = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element)
            
            # Extract address
            address_match = re.search(r'(\d+[^,]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|way|blvd|boulevard)[^,]*)', text_content, re.IGNORECASE)
            address = address_match.group(1) if address_match else None
            
            # Extract parcel number
            parcel_match = re.search(r'(?:parcel|apn|pin)[:\s#]*([A-Z0-9\-]+)', text_content, re.IGNORECASE)
            parcel_number = parcel_match.group(1) if parcel_match else None
            
            # Extract sale date
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})', text_content)
            sale_date = date_match.group(1) if date_match else None
            
            # Extract amount owed
            amount_match = re.search(r'\$([0-9,]+\.?\d*)', text_content)
            amount_owed = amount_match.group(1).replace(',', '') if amount_match else None
            
            if address:
                return {
                    'address': address,
                    'county': county,
                    'parcel_number': parcel_number,
                    'sale_date': sale_date,
                    'amount_owed': float(amount_owed) if amount_owed and amount_owed.replace('.', '').isdigit() else None,
                    'foreclosure_type': 'tax_sale',
                    'source_url': None,  # Would be set by caller
                    'collected_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.warning(f"Property data extraction error: {e}")
            
        return None
        
    def _extract_selenium_property_data(self, element: Any, county: str) -> Optional[Dict[str, Any]]:
        """Extract property data from Selenium WebElement"""
        try:
            text_content = element.text
            return self._extract_property_data(type('MockElement', (), {'get_text': lambda x: text_content})(), county)
        except Exception as e:
            self.logger.warning(f"Selenium property data extraction error: {e}")
            return None
            
    def _matches_4plex_patterns(self, property_data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Check if property matches 4-plex patterns"""
        text_to_search = f"{property_data.get('address', '')} {property_data.get('description', '')}"
        
        for pattern in config['search_patterns']:
            if re.search(pattern, text_to_search, re.IGNORECASE):
                return True
                
        return False
        
    def _get_selenium_driver(self) -> webdriver.Chrome:
        """Get configured Selenium Chrome driver"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--user-agent={self.settings.USER_AGENTS.split("|")[0]}')
        
        return webdriver.Chrome(options=options)