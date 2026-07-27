"""
Workflow Orchestrator for Integrated Property System
Manages the end-to-end pipeline from discovery to valuation analysis
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from uuid import uuid4

from .unified_models import UnifiedProperty, IntegratedAnalysis, PropertySource, ProcessingStatus
from services.database.connection import get_db_session
from agents.base_agent import AgentResult
from config.settings import Settings

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates the integrated property discovery and valuation workflow"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.foreclosure_api_url = getattr(settings, 'FORECLOSURE_API_URL', 'http://localhost:11050')
        self.valuation_api_url = getattr(settings, 'VALUATION_API_URL', 'http://localhost:3000')
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout
        
        # Workflow stages
        self.workflow_stages = [
            'discovery',
            'validation', 
            'enrichment',
            'valuation',
            'analysis',
            'scoring',
            'alerting'
        ]
        
    async def process_discovered_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete pipeline from discovery to investment analysis"""
        workflow_id = str(uuid4())
        
        logger.info(f"Starting integrated workflow {workflow_id} for property: {property_data.get('address')}")
        
        try:
            # Create unified property record
            unified_property = await self._create_unified_property(property_data, workflow_id)
            
            # Stage 1: Validation
            validation_result = await self._validate_4plex_property(unified_property)
            if not validation_result['is_valid']:
                logger.info(f"Property failed validation: {validation_result['reason']}")
                return self._create_workflow_result(workflow_id, 'validation_failed', validation_result)
            
            # Stage 2: Enrichment
            enriched_property = await self._enrich_property_data(unified_property)
            
            # Stage 3: Valuation Analysis
            valuation_result = await self._trigger_valuation_analysis(enriched_property)
            
            # Stage 4: Investment Scoring
            investment_score = await self._calculate_investment_score(enriched_property, valuation_result)
            
            # Stage 5: Generate Integrated Analysis
            integrated_analysis = await self._generate_integrated_analysis(
                enriched_property, valuation_result, investment_score
            )
            
            # Stage 6: Alert Generation
            await self._check_alert_thresholds(enriched_property, integrated_analysis)
            
            # Final result
            workflow_result = self._create_workflow_result(
                workflow_id, 'completed', {
                    'property': enriched_property.dict(),
                    'analysis': integrated_analysis.dict(),
                    'investment_score': investment_score
                }
            )
            
            logger.info(f"Workflow {workflow_id} completed successfully with score: {investment_score['total_score']}")
            return workflow_result
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            return self._create_workflow_result(workflow_id, 'failed', {'error': str(e)})
    
    async def _create_unified_property(self, property_data: Dict[str, Any], workflow_id: str) -> UnifiedProperty:
        """Create unified property model from discovery data"""
        
        # Map foreclosure discovery data to unified model
        unified_data = {
            'id': str(uuid4()),
            'source': PropertySource.FORECLOSURE_DISCOVERY,
            'name': f"4-Plex at {property_data.get('address', 'Unknown Address')}",
            'address': property_data.get('address', ''),
            'city': property_data.get('city', ''),
            'county': property_data.get('county', ''),
            'state': 'GA',
            'zip_code': property_data.get('zip_code'),
            'parcel_number': property_data.get('parcel_number'),
            'units': 4,  # Focus on 4-plex
            'assessed_value': property_data.get('assessed_value'),
            'amount_owed': property_data.get('amount_owed'),
            'foreclosure_status': property_data.get('foreclosure_type'),
            'foreclosure_stage': property_data.get('foreclosure_stage'),
            'sale_date': self._parse_date(property_data.get('sale_date')),
            'has_code_violations': property_data.get('has_violations', False),
            'violation_count': property_data.get('violation_count', 0),
            'discovery_status': ProcessingStatus.DISCOVERED,
            'discovered_at': datetime.utcnow(),
            'data_sources': [property_data.get('source_url', 'county_website')],
            'processing_notes': f"Discovered via workflow {workflow_id}"
        }
        
        return UnifiedProperty(**unified_data)
    
    async def _validate_4plex_property(self, property: UnifiedProperty) -> Dict[str, Any]:
        """Validate that property is suitable for analysis"""
        
        validation_checks = []
        
        # Check if it's actually a 4-plex
        if property.units != 4:
            return {'is_valid': False, 'reason': f"Property has {property.units} units, not 4"}
        
        # Check if address is complete
        if not property.address or len(property.address) < 10:
            return {'is_valid': False, 'reason': "Incomplete address information"}
        
        # Check if county is supported
        if property.county not in ['Fulton', 'DeKalb', 'Clayton', 'Cobb', 'Atlanta']:
            return {'is_valid': False, 'reason': f"County {property.county} not supported"}
        
        # Check if we have sufficient data for analysis
        if not property.assessed_value and not property.amount_owed:
            return {'is_valid': False, 'reason': "Insufficient financial data"}
        
        validation_checks.append("4-plex verification passed")
        validation_checks.append("Address validation passed")
        validation_checks.append("County validation passed")
        validation_checks.append("Financial data validation passed")
        
        return {
            'is_valid': True,
            'validation_checks': validation_checks,
            'confidence_score': 0.85
        }
    
    async def _enrich_property_data(self, property: UnifiedProperty) -> UnifiedProperty:
        """Enrich property data with additional market information"""
        
        try:
            # Call PropertyRadar API if available
            if self.settings.PROPERTYRADAR_API_KEY:
                propertyradar_data = await self._get_propertyradar_data(property)
                if propertyradar_data:
                    property = self._merge_propertyradar_data(property, propertyradar_data)
            
            # Call RealEstate API if available
            if self.settings.REALESTATE_API_KEY:
                realestate_data = await self._get_realestate_api_data(property)
                if realestate_data:
                    property = self._merge_realestate_data(property, realestate_data)
            
            # Call ATTOM Data API if available
            if self.settings.ATTOM_API_KEY:
                attom_data = await self._get_attom_data(property)
                if attom_data:
                    property = self._merge_attom_data(property, attom_data)
            
            # Update processing status
            property.discovery_status = ProcessingStatus.ENRICHED
            property.last_updated = datetime.utcnow()
            
            return property
            
        except Exception as e:
            logger.error(f"Property enrichment failed: {e}")
            # Continue with original data
            return property
    
    async def _trigger_valuation_analysis(self, property: UnifiedProperty) -> Dict[str, Any]:
        """Trigger valuation analysis using the multifamily valuation application"""
        
        try:
            # Prepare data for valuation system
            valuation_request = {
                'property': {
                    'name': property.name,
                    'address': property.address,
                    'city': property.city,
                    'state': property.state,
                    'type': 'multifamily',
                    'units': property.units,
                    'square_footage': property.square_footage,
                    'year_built': property.year_built
                },
                'financials': {
                    'asking_price': property.asking_price or property.assessed_value,
                    'assessed_value': property.assessed_value,
                    'estimated_rents': property.gross_income / 12 if property.gross_income else None
                },
                'source': 'foreclosure_discovery',
                'urgent': True  # Flag for high-priority processing
            }
            
            # Call valuation API
            response = await self.client.post(
                f"{self.valuation_api_url}/api/process",
                json=valuation_request
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Valuation API error: {response.status_code}")
                return await self._fallback_valuation_analysis(property)
                
        except Exception as e:
            logger.error(f"Valuation analysis failed: {e}")
            return await self._fallback_valuation_analysis(property)
    
    async def _calculate_investment_score(self, property: UnifiedProperty, 
                                        valuation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive investment score"""
        
        scores = {
            'discovery_factors': self._score_discovery_factors(property),
            'valuation_factors': self._score_valuation_factors(valuation_result),
            'risk_factors': self._score_risk_factors(property, valuation_result),
            'market_factors': self._score_market_factors(property)
        }
        
        # Weighted average
        weights = {
            'discovery_factors': 0.25,
            'valuation_factors': 0.40,
            'risk_factors': 0.20,
            'market_factors': 0.15
        }
        
        total_score = sum(scores[factor] * weights[factor] for factor in scores)
        
        return {
            'total_score': min(max(total_score, 0), 100),  # Clamp to 0-100
            'factor_scores': scores,
            'weights_used': weights,
            'confidence_level': self._calculate_confidence_level(property, valuation_result),
            'recommendation': self._generate_recommendation(total_score),
            'reasoning': self._generate_scoring_reasoning(scores, total_score)
        }
    
    async def _generate_integrated_analysis(self, property: UnifiedProperty, 
                                          valuation_result: Dict[str, Any],
                                          investment_score: Dict[str, Any]) -> IntegratedAnalysis:
        """Generate comprehensive integrated analysis"""
        
        analysis_data = {
            'id': str(uuid4()),
            'property_id': property.id,
            'confidence_score': investment_score['confidence_level'],
            
            # Foreclosure analysis
            'foreclosure_opportunity_score': investment_score['factor_scores']['discovery_factors'],
            'foreclosure_risk_factors': self._extract_foreclosure_risks(property),
            'legal_complexity_score': self._assess_legal_complexity(property),
            'timeline_to_acquisition': self._estimate_acquisition_timeline(property),
            
            # Financial analysis
            'acquisition_cost_estimate': self._estimate_acquisition_cost(property),
            'renovation_cost_estimate': valuation_result.get('renovation_estimate', 25000),
            'total_investment_required': 0,  # Will be calculated
            'projected_annual_income': valuation_result.get('projected_annual_income', 0),
            'projected_monthly_cashflow': valuation_result.get('monthly_cashflow', 0),
            'projected_cap_rate': valuation_result.get('cap_rate', 0),
            'projected_irr': valuation_result.get('irr', 0),
            'payback_period_years': valuation_result.get('payback_period', 0),
            
            # Risk assessment
            'overall_risk_score': investment_score['factor_scores']['risk_factors'],
            'risk_categories': self._categorize_risks(property, valuation_result),
            'mitigation_strategies': self._suggest_risk_mitigation(property),
            
            # Market analysis
            'market_trends': valuation_result.get('market_analysis', {}),
            'competitive_advantages': self._identify_competitive_advantages(property),
            
            # Recommendations
            'investment_recommendation': investment_score['recommendation'],
            'reasoning': investment_score['reasoning'],
            'next_steps': self._generate_next_steps(property, investment_score),
            
            # Additional considerations
            'financing_options': self._analyze_financing_options(property),
            'tax_implications': self._analyze_tax_implications(property),
            'exit_strategies': self._identify_exit_strategies(property)
        }
        
        # Calculate total investment required
        analysis_data['total_investment_required'] = (
            analysis_data['acquisition_cost_estimate'] + 
            analysis_data['renovation_cost_estimate']
        )
        
        return IntegratedAnalysis(**analysis_data)
    
    async def _check_alert_thresholds(self, property: UnifiedProperty, 
                                    analysis: IntegratedAnalysis):
        """Check if property meets alert thresholds and send notifications"""
        
        # High-value opportunity thresholds
        high_value_criteria = [
            analysis.overall_risk_score >= 75,  # Low risk (inverted scale)
            analysis.projected_cap_rate >= 0.08,  # 8%+ cap rate
            analysis.projected_monthly_cashflow >= 500,  # $500+ monthly cash flow
            analysis.confidence_score >= 0.8  # High confidence
        ]
        
        if sum(high_value_criteria) >= 3:  # Meet at least 3 criteria
            await self._send_high_value_alert(property, analysis)
        
        # Urgent action required alerts
        urgent_criteria = [
            property.sale_date and property.sale_date <= datetime.utcnow() + timedelta(days=7),
            analysis.foreclosure_opportunity_score >= 90,
            analysis.projected_irr >= 0.15  # 15%+ IRR
        ]
        
        if any(urgent_criteria):
            await self._send_urgent_alert(property, analysis)
    
    def _score_discovery_factors(self, property: UnifiedProperty) -> float:
        """Score factors related to foreclosure discovery"""
        score = 50  # Base score
        
        # Foreclosure stage scoring
        stage_scores = {
            'pre_foreclosure': 85,
            'notice_of_default': 75,
            'lis_pendens': 65,
            'auction_scheduled': 55,
            'auction_completed': 35,
            'reo': 45
        }
        
        if property.foreclosure_status:
            score = stage_scores.get(property.foreclosure_status.value, 50)
        
        # Adjust for amount owed vs assessed value
        if property.amount_owed and property.assessed_value:
            debt_ratio = property.amount_owed / property.assessed_value
            if debt_ratio < 0.5:
                score += 15  # Low debt
            elif debt_ratio > 0.8:
                score -= 10  # High debt
        
        # Adjust for code violations
        if property.has_code_violations:
            score -= min(property.violation_count * 5, 20)
        
        return min(max(score, 0), 100)
    
    def _score_valuation_factors(self, valuation_result: Dict[str, Any]) -> float:
        """Score factors from valuation analysis"""
        score = 50  # Base score
        
        # Cap rate scoring
        cap_rate = valuation_result.get('cap_rate', 0)
        if cap_rate >= 0.10:
            score += 25
        elif cap_rate >= 0.08:
            score += 15
        elif cap_rate >= 0.06:
            score += 5
        elif cap_rate < 0.04:
            score -= 15
        
        # Cash flow scoring
        monthly_cashflow = valuation_result.get('monthly_cashflow', 0)
        if monthly_cashflow >= 1000:
            score += 20
        elif monthly_cashflow >= 500:
            score += 10
        elif monthly_cashflow < 0:
            score -= 25
        
        # IRR scoring
        irr = valuation_result.get('irr', 0)
        if irr >= 0.15:
            score += 15
        elif irr >= 0.12:
            score += 10
        elif irr < 0.08:
            score -= 10
        
        return min(max(score, 0), 100)
    
    def _score_risk_factors(self, property: UnifiedProperty, 
                          valuation_result: Dict[str, Any]) -> float:
        """Score risk factors (higher score = lower risk)"""
        score = 75  # Start with low risk assumption
        
        # Legal complexity risks
        if property.has_code_violations:
            score -= min(property.violation_count * 10, 30)
        
        # Market risks
        if property.county in ['Clayton']:  # Higher risk counties
            score -= 10
        
        # Financial risks
        renovation_cost = valuation_result.get('renovation_estimate', 0)
        if renovation_cost > 50000:
            score -= 20
        elif renovation_cost > 25000:
            score -= 10
        
        # Timeline risks
        if property.sale_date:
            days_to_sale = (property.sale_date - datetime.utcnow()).days
            if days_to_sale < 14:
                score -= 15  # Very tight timeline
            elif days_to_sale < 30:
                score -= 8   # Tight timeline
        
        return min(max(score, 0), 100)
    
    def _score_market_factors(self, property: UnifiedProperty) -> float:
        """Score market factors"""
        score = 60  # Base market score
        
        # County-based market scoring
        county_scores = {
            'Fulton': 80,   # Strong market
            'DeKalb': 70,   # Good market
            'Atlanta': 85,  # Strong market
            'Cobb': 75,     # Good market
            'Clayton': 55   # Developing market
        }
        
        score = county_scores.get(property.county, 60)
        
        # Adjust for property characteristics
        if property.year_built and property.year_built > 1990:
            score += 10  # Newer property
        elif property.year_built and property.year_built < 1970:
            score -= 5   # Older property
        
        return min(max(score, 0), 100)
    
    # Helper methods for analysis generation
    def _extract_foreclosure_risks(self, property: UnifiedProperty) -> List[str]:
        """Extract foreclosure-specific risk factors"""
        risks = []
        
        if property.has_code_violations:
            risks.append(f"Property has {property.violation_count} code violations")
        
        if property.sale_date:
            days_to_sale = (property.sale_date - datetime.utcnow()).days
            if days_to_sale < 30:
                risks.append(f"Sale scheduled in {days_to_sale} days - tight timeline")
        
        if property.redemption_period:
            risks.append("Property may have redemption rights")
        
        return risks
    
    def _estimate_acquisition_cost(self, property: UnifiedProperty) -> float:
        """Estimate total acquisition cost"""
        base_cost = property.amount_owed or property.assessed_value or 200000
        
        # Add estimated closing costs, legal fees, etc.
        closing_costs = base_cost * 0.03  # 3% for closing costs
        legal_fees = 5000  # Estimated legal fees for foreclosure
        
        return base_cost + closing_costs + legal_fees
    
    def _generate_next_steps(self, property: UnifiedProperty, 
                           investment_score: Dict[str, Any]) -> List[str]:
        """Generate recommended next steps"""
        steps = []
        
        if investment_score['total_score'] >= 70:
            steps.append("Schedule property inspection")
            steps.append("Contact property owner or attorney")
            steps.append("Verify title and lien status")
            steps.append("Obtain financing pre-approval")
        elif investment_score['total_score'] >= 50:
            steps.append("Conduct additional market research")
            steps.append("Review comparable sales")
            steps.append("Assess renovation requirements")
        else:
            steps.append("Continue monitoring for status changes")
            steps.append("Look for similar opportunities in the area")
        
        return steps
    
    async def _send_high_value_alert(self, property: UnifiedProperty, 
                                   analysis: IntegratedAnalysis):
        """Send high-value opportunity alert"""
        # Implementation would send email, Slack, or other notifications
        logger.info(f"🚨 HIGH VALUE OPPORTUNITY: {property.address} - Score: {analysis.overall_risk_score}")
    
    async def _send_urgent_alert(self, property: UnifiedProperty, 
                               analysis: IntegratedAnalysis):
        """Send urgent action required alert"""
        logger.warning(f"⚡ URGENT: Action required for {property.address}")
    
    def _create_workflow_result(self, workflow_id: str, status: str, 
                              data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized workflow result"""
        return {
            'workflow_id': workflow_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
    
    # Placeholder methods for future implementation
    async def _get_propertyradar_data(self, property: UnifiedProperty) -> Optional[Dict]:
        """Get data from PropertyRadar API"""
        return None
    
    async def _get_realestate_api_data(self, property: UnifiedProperty) -> Optional[Dict]:
        """Get data from RealEstate API"""
        return None
    
    async def _get_attom_data(self, property: UnifiedProperty) -> Optional[Dict]:
        """Get data from ATTOM Data API"""
        return None
    
    async def _fallback_valuation_analysis(self, property: UnifiedProperty) -> Dict[str, Any]:
        """Fallback valuation when main system unavailable"""
        return {
            'cap_rate': 0.07,  # Conservative estimate
            'monthly_cashflow': 400,
            'irr': 0.10,
            'renovation_estimate': 30000,
            'confidence': 0.6
        }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return None