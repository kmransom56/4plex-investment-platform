"""
Financial Calculation Engine for 4-Plex Investment Platform
Extracted and enhanced from Multifamily Valuation Application

Provides comprehensive real estate financial analysis including:
- NOI, Cap Rate, Cash-on-Cash, IRR, DSCR, LTV calculations
- Multi-year projections with growth assumptions
- Investment scoring and grading algorithms
- Risk assessment and sensitivity analysis
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass
import json
from enum import Enum

from models import (
    FinancialMetrics, 
    FinancialProjection, 
    InvestmentGrade, 
    RiskLevel,
    calculate_investment_score,
    determine_investment_grade
)

class PropertyClass(str, Enum):
    """Property classification for benchmarking"""
    CLASS_A = "class_a"
    CLASS_B = "class_b" 
    CLASS_C = "class_c"
    CLASS_D = "class_d"

@dataclass
class FinancialInputs:
    """Input data for financial analysis"""
    # Property Info
    purchase_price: float
    closing_costs: float = 0.0
    renovation_costs: float = 0.0
    
    # Income Data
    monthly_rent: float = 0.0
    other_income: float = 0.0
    vacancy_rate: float = 0.05  # 5%
    
    # Expense Data
    property_taxes: float = 0.0
    insurance: float = 0.0
    maintenance: float = 0.0
    management_fee_percent: float = 0.0
    utilities: float = 0.0
    other_expenses: float = 0.0
    
    # Financing
    down_payment_percent: float = 0.25
    interest_rate: float = 0.055
    loan_term: int = 30
    
    # Projections
    rent_growth_rate: float = 0.03
    expense_growth_rate: float = 0.025
    appreciation_rate: float = 0.03
    hold_period: int = 5
    exit_cap_rate: float = 0.065

@dataclass 
class CalculationResults:
    """Complete financial analysis results"""
    # Core Metrics
    financial_metrics: FinancialMetrics
    
    # Investment Analysis
    investment_score: float
    investment_grade: InvestmentGrade
    viability_score: float
    risk_level: RiskLevel
    
    # Projections
    projections: List[FinancialProjection]
    
    # Analysis Summary
    key_metrics: Dict[str, Any]
    recommendations: List[str]
    risk_factors: List[str]
    opportunities: List[str]

class FinancialEngine:
    """Main financial calculation engine"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with configuration"""
        self.config = config or self._default_config()
        self.market_data = self._load_market_data()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for calculations"""
        return {
            "financial_assumptions": {
                "hold_period": 5,
                "exit_cap_rate": 0.065,
                "annual_rent_growth": 0.03,
                "annual_expense_growth": 0.025,
                "vacancy_rate": 0.05,
                "management_fee": 0.05,
                "capital_reserve": 0.02,
                "discount_rate": 0.10
            },
            "scoring_weights": {
                "cap_rate": 0.15,
                "cash_on_cash": 0.20,
                "irr": 0.25,
                "dscr": 0.15,
                "ltv": 0.10,
                "equity_multiple": 0.15
            },
            "thresholds": {
                "min_cap_rate": 6.0,
                "min_cash_on_cash": 8.0,
                "min_dscr": 1.25,
                "max_ltv": 80.0,
                "min_irr": 12.0
            }
        }
    
    def _load_market_data(self) -> Dict[str, Any]:
        """Load market benchmarking data"""
        return {
            PropertyClass.CLASS_A: {
                "cap_rate": 0.045,
                "price_per_unit": 180000,
                "grm_multiple": 8.5,
                "typical_rent_psf": 1.8
            },
            PropertyClass.CLASS_B: {
                "cap_rate": 0.055, 
                "price_per_unit": 140000,
                "grm_multiple": 7.5,
                "typical_rent_psf": 1.4
            },
            PropertyClass.CLASS_C: {
                "cap_rate": 0.065,
                "price_per_unit": 100000, 
                "grm_multiple": 6.5,
                "typical_rent_psf": 1.0
            },
            PropertyClass.CLASS_D: {
                "cap_rate": 0.080,
                "price_per_unit": 70000,
                "grm_multiple": 5.5,
                "typical_rent_psf": 0.8
            }
        }
    
    def analyze_property(self, inputs: FinancialInputs) -> CalculationResults:
        """Complete property financial analysis"""
        
        # Calculate financial metrics
        financial_metrics = self._calculate_financial_metrics(inputs)
        
        # Generate projections
        projections = self._generate_projections(inputs, financial_metrics)
        
        # Calculate investment score
        investment_score = calculate_investment_score(financial_metrics)
        investment_grade = determine_investment_grade(investment_score)
        
        # Calculate viability score
        viability_score = self._calculate_viability_score(financial_metrics)
        
        # Assess risk
        risk_level = self._assess_risk(financial_metrics, inputs)
        
        # Generate insights
        key_metrics = self._generate_key_metrics(financial_metrics, projections)
        recommendations = self._generate_recommendations(financial_metrics, inputs)
        risk_factors = self._identify_risk_factors(financial_metrics, inputs)
        opportunities = self._identify_opportunities(financial_metrics, inputs)
        
        return CalculationResults(
            financial_metrics=financial_metrics,
            investment_score=investment_score,
            investment_grade=investment_grade,
            viability_score=viability_score,
            risk_level=risk_level,
            projections=projections,
            key_metrics=key_metrics,
            recommendations=recommendations,
            risk_factors=risk_factors,
            opportunities=opportunities
        )
    
    def _calculate_financial_metrics(self, inputs: FinancialInputs) -> FinancialMetrics:
        """Calculate core financial metrics"""
        
        # Basic calculations
        total_investment = inputs.purchase_price + inputs.closing_costs + inputs.renovation_costs
        loan_amount = inputs.purchase_price * (1 - inputs.down_payment_percent)
        cash_invested = total_investment - loan_amount
        
        # Income calculations
        annual_rental_income = inputs.monthly_rent * 12
        effective_gross_income = annual_rental_income * (1 - inputs.vacancy_rate)
        total_income = effective_gross_income + inputs.other_income
        
        # Expense calculations
        management_fee = total_income * inputs.management_fee_percent
        total_expenses = (
            inputs.property_taxes + 
            inputs.insurance + 
            inputs.maintenance + 
            management_fee + 
            inputs.utilities + 
            inputs.other_expenses
        )
        
        # Net Operating Income
        noi = total_income - total_expenses
        
        # Financing calculations
        annual_debt_service = self._calculate_debt_service(
            loan_amount, inputs.interest_rate, inputs.loan_term
        ) * 12
        
        # Cash flow
        annual_cash_flow = noi - annual_debt_service
        monthly_cash_flow = annual_cash_flow / 12
        
        # Key ratios
        cap_rate = (noi / inputs.purchase_price) * 100 if inputs.purchase_price > 0 else 0
        cash_on_cash = (annual_cash_flow / cash_invested) * 100 if cash_invested > 0 else 0
        dscr = noi / annual_debt_service if annual_debt_service > 0 else 0
        ltv = (loan_amount / inputs.purchase_price) * 100 if inputs.purchase_price > 0 else 0
        
        # Calculate IRR
        cash_flows = self._generate_cash_flows_for_irr(inputs, noi, annual_cash_flow)
        irr = self._calculate_irr(cash_flows)
        
        return FinancialMetrics(
            purchase_price=inputs.purchase_price,
            closing_costs=inputs.closing_costs,
            renovation_costs=inputs.renovation_costs,
            total_investment=total_investment,
            gross_rental_income=annual_rental_income,
            other_income=inputs.other_income,
            total_income=total_income,
            vacancy_rate=inputs.vacancy_rate,
            effective_gross_income=effective_gross_income,
            management_fees=management_fee,
            maintenance_repairs=inputs.maintenance,
            property_taxes=inputs.property_taxes,
            insurance=inputs.insurance,
            utilities=inputs.utilities,
            other_expenses=inputs.other_expenses,
            total_expenses=total_expenses,
            net_operating_income=noi,
            loan_amount=loan_amount,
            interest_rate=inputs.interest_rate,
            loan_term=inputs.loan_term,
            annual_debt_service=annual_debt_service,
            cap_rate=cap_rate,
            cash_on_cash_return=cash_on_cash,
            debt_service_coverage_ratio=dscr,
            loan_to_value=ltv,
            internal_rate_of_return=irr,
            monthly_cash_flow=monthly_cash_flow,
            annual_cash_flow=annual_cash_flow
        )
    
    def _calculate_debt_service(self, loan_amount: float, annual_rate: float, term_years: int) -> float:
        """Calculate monthly debt service payment"""
        if loan_amount == 0 or annual_rate == 0:
            return 0
        
        monthly_rate = annual_rate / 12
        num_payments = term_years * 12
        
        payment = loan_amount * (
            (monthly_rate * (1 + monthly_rate) ** num_payments) /
            ((1 + monthly_rate) ** num_payments - 1)
        )
        
        return payment
    
    def _calculate_irr(self, cash_flows: List[float], max_iterations: int = 100, tolerance: float = 1e-7) -> float:
        """Calculate Internal Rate of Return using Newton-Raphson method"""
        
        def npv(rate: float) -> float:
            """Calculate Net Present Value"""
            return sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
        
        def npv_derivative(rate: float) -> float:
            """Calculate derivative of NPV"""
            return sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))
        
        # Initial guess
        rate = 0.1
        
        for _ in range(max_iterations):
            npv_val = npv(rate)
            
            if abs(npv_val) < tolerance:
                return rate * 100  # Return as percentage
            
            npv_deriv = npv_derivative(rate)
            if abs(npv_deriv) < tolerance:
                break
            
            rate = rate - npv_val / npv_deriv
        
        return rate * 100 if rate > -1 else 0
    
    def _generate_cash_flows_for_irr(self, inputs: FinancialInputs, initial_noi: float, initial_cash_flow: float) -> List[float]:
        """Generate cash flows for IRR calculation"""
        cash_flows = [-inputs.purchase_price - inputs.closing_costs - inputs.renovation_costs]  # Initial investment
        
        current_noi = initial_noi
        current_cash_flow = initial_cash_flow
        
        # Annual cash flows
        for year in range(1, inputs.hold_period + 1):
            # Grow NOI
            current_noi *= (1 + inputs.rent_growth_rate)
            # Adjust for expense growth
            current_cash_flow *= (1 + (inputs.rent_growth_rate - inputs.expense_growth_rate))
            cash_flows.append(current_cash_flow)
        
        # Exit value in final year
        exit_value = current_noi / inputs.exit_cap_rate
        cash_flows[-1] += exit_value
        
        return cash_flows
    
    def _generate_projections(self, inputs: FinancialInputs, base_metrics: FinancialMetrics) -> List[FinancialProjection]:
        """Generate multi-year financial projections"""
        projections = []
        
        current_income = base_metrics.total_income or 0
        current_expenses = base_metrics.total_expenses or 0
        current_noi = base_metrics.net_operating_income
        current_property_value = inputs.purchase_price
        
        for year in range(1, inputs.hold_period + 1):
            # Apply growth rates
            projected_income = current_income * ((1 + inputs.rent_growth_rate) ** year)
            projected_expenses = current_expenses * ((1 + inputs.expense_growth_rate) ** year)
            projected_noi = projected_income - projected_expenses
            projected_property_value = current_property_value * ((1 + inputs.appreciation_rate) ** year)
            
            # Calculate cash flow (NOI - debt service)
            debt_service = base_metrics.annual_debt_service or 0
            cash_flow = projected_noi - debt_service
            
            projection = FinancialProjection(
                year=year,
                gross_income=round(projected_income, 0),
                total_expenses=round(projected_expenses, 0),
                net_operating_income=round(projected_noi, 0),
                debt_service=round(debt_service, 0),
                cash_flow=round(cash_flow, 0),
                property_value=round(projected_property_value, 0),
                appreciation_rate=inputs.appreciation_rate,
                income_growth_rate=inputs.rent_growth_rate,
                expense_growth_rate=inputs.expense_growth_rate
            )
            
            projections.append(projection)
        
        return projections
    
    def _calculate_viability_score(self, metrics: FinancialMetrics) -> float:
        """Calculate comprehensive viability score (0-100)"""
        weights = self.config["scoring_weights"]
        
        # Individual metric scores (0-100 scale)
        cap_rate_score = min(100, max(0, (metrics.cap_rate / 8) * 100)) if metrics.cap_rate else 0
        coc_score = min(100, max(0, (metrics.cash_on_cash_return / 12) * 100)) if metrics.cash_on_cash_return else 0
        irr_score = min(100, max(0, (metrics.internal_rate_of_return / 15) * 100)) if metrics.internal_rate_of_return else 0
        dscr_score = min(100, max(0, ((metrics.debt_service_coverage_ratio - 1) / 0.5) * 100)) if metrics.debt_service_coverage_ratio else 0
        ltv_score = min(100, max(0, ((80 - metrics.loan_to_value) / 20) * 100)) if metrics.loan_to_value else 0
        
        # Calculate equity multiple for final score
        total_cash_returned = (metrics.annual_cash_flow or 0) * 5  # Simple 5-year estimate
        cash_invested = metrics.total_investment - (metrics.loan_amount or 0)
        equity_multiple = total_cash_returned / cash_invested if cash_invested > 0 else 0
        em_score = min(100, max(0, ((equity_multiple - 1) / 1) * 100))
        
        # Weighted total score
        total_score = (
            cap_rate_score * weights["cap_rate"] +
            coc_score * weights["cash_on_cash"] +
            irr_score * weights["irr"] +
            dscr_score * weights["dscr"] +
            ltv_score * weights["ltv"] +
            em_score * weights["equity_multiple"]
        ) * 100
        
        return round(total_score, 1)
    
    def _assess_risk(self, metrics: FinancialMetrics, inputs: FinancialInputs) -> RiskLevel:
        """Assess overall investment risk"""
        risk_score = 0
        
        # DSCR risk
        if metrics.debt_service_coverage_ratio and metrics.debt_service_coverage_ratio < 1.25:
            risk_score += 2
        elif metrics.debt_service_coverage_ratio and metrics.debt_service_coverage_ratio < 1.5:
            risk_score += 1
        
        # LTV risk
        if metrics.loan_to_value and metrics.loan_to_value > 80:
            risk_score += 2
        elif metrics.loan_to_value and metrics.loan_to_value > 70:
            risk_score += 1
        
        # Cap rate risk
        if metrics.cap_rate and metrics.cap_rate < 6:
            risk_score += 2
        elif metrics.cap_rate and metrics.cap_rate < 7:
            risk_score += 1
        
        # Vacancy rate risk
        if inputs.vacancy_rate > 0.1:
            risk_score += 2
        elif inputs.vacancy_rate > 0.07:
            risk_score += 1
        
        # Cash flow risk
        if metrics.monthly_cash_flow and metrics.monthly_cash_flow < 0:
            risk_score += 3
        elif metrics.monthly_cash_flow and metrics.monthly_cash_flow < 200:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 6:
            return RiskLevel.VERY_HIGH
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_key_metrics(self, metrics: FinancialMetrics, projections: List[FinancialProjection]) -> Dict[str, Any]:
        """Generate key metrics summary"""
        
        # 5-year totals
        total_cash_flow = sum(p.cash_flow for p in projections)
        avg_annual_cash_flow = total_cash_flow / len(projections) if projections else 0
        
        # Final year values
        final_year = projections[-1] if projections else None
        final_property_value = final_year.property_value if final_year else 0
        
        # Calculate total return
        cash_invested = metrics.total_investment - (metrics.loan_amount or 0)
        total_return = total_cash_flow + final_property_value
        total_return_multiple = total_return / cash_invested if cash_invested > 0 else 0
        
        return {
            "monthly_cash_flow": metrics.monthly_cash_flow,
            "annual_cash_flow": metrics.annual_cash_flow,
            "total_5_year_cash_flow": round(total_cash_flow, 0),
            "average_annual_cash_flow": round(avg_annual_cash_flow, 0),
            "final_property_value": round(final_property_value, 0),
            "total_return_multiple": round(total_return_multiple, 2),
            "cap_rate": metrics.cap_rate,
            "cash_on_cash_return": metrics.cash_on_cash_return,
            "irr": metrics.internal_rate_of_return,
            "dscr": metrics.debt_service_coverage_ratio,
            "ltv": metrics.loan_to_value,
            "noi": metrics.net_operating_income
        }
    
    def _generate_recommendations(self, metrics: FinancialMetrics, inputs: FinancialInputs) -> List[str]:
        """Generate investment recommendations"""
        recommendations = []
        
        # Cap rate recommendations
        if metrics.cap_rate and metrics.cap_rate > 8:
            recommendations.append("Strong cap rate indicates good income potential relative to purchase price")
        elif metrics.cap_rate and metrics.cap_rate < 6:
            recommendations.append("Consider negotiating purchase price to improve cap rate")
        
        # Cash flow recommendations
        if metrics.monthly_cash_flow and metrics.monthly_cash_flow > 500:
            recommendations.append("Excellent cash flow provides strong monthly returns")
        elif metrics.monthly_cash_flow and metrics.monthly_cash_flow < 0:
            recommendations.append("Negative cash flow requires additional capital injection or higher rents")
        
        # DSCR recommendations
        if metrics.debt_service_coverage_ratio and metrics.debt_service_coverage_ratio > 1.5:
            recommendations.append("Strong debt coverage provides good safety margin")
        elif metrics.debt_service_coverage_ratio and metrics.debt_service_coverage_ratio < 1.25:
            recommendations.append("Consider larger down payment to improve debt service coverage")
        
        # Vacancy rate recommendations
        if inputs.vacancy_rate > 0.1:
            recommendations.append("High vacancy assumption may be conservative - verify local market rates")
        
        # Investment grade recommendations
        investment_score = calculate_investment_score(metrics)
        if investment_score > 80:
            recommendations.append("High-quality investment opportunity with strong fundamentals")
        elif investment_score < 60:
            recommendations.append("Consider passing on this opportunity or negotiating better terms")
        
        return recommendations
    
    def _identify_risk_factors(self, metrics: FinancialMetrics, inputs: FinancialInputs) -> List[str]:
        """Identify key risk factors"""
        risks = []
        
        # Financial risks
        if metrics.debt_service_coverage_ratio and metrics.debt_service_coverage_ratio < 1.25:
            risks.append("Low debt service coverage ratio increases default risk")
        
        if metrics.loan_to_value and metrics.loan_to_value > 80:
            risks.append("High loan-to-value ratio limits equity buffer")
        
        if metrics.monthly_cash_flow and metrics.monthly_cash_flow < 200:
            risks.append("Minimal cash flow provides little cushion for unexpected expenses")
        
        # Market risks
        if inputs.vacancy_rate > 0.08:
            risks.append("High vacancy rate assumption indicates potential rental market challenges")
        
        if metrics.cap_rate and metrics.cap_rate < 6:
            risks.append("Low cap rate may indicate overpriced market or aggressive assumptions")
        
        # Operational risks
        if inputs.management_fee_percent == 0:
            risks.append("Self-management increases operational burden and risk")
        
        if inputs.maintenance < (inputs.monthly_rent * 12 * 0.05):
            risks.append("Maintenance budget may be insufficient for 4-plex property")
        
        return risks
    
    def _identify_opportunities(self, metrics: FinancialMetrics, inputs: FinancialInputs) -> List[str]:
        """Identify investment opportunities"""
        opportunities = []
        
        # Value-add opportunities
        if inputs.renovation_costs > 0:
            opportunities.append("Renovation improvements can drive rent increases and property appreciation")
        
        # Income opportunities
        if inputs.other_income == 0:
            opportunities.append("Consider additional income streams (parking, laundry, storage)")
        
        # Expense optimization
        if inputs.management_fee_percent > 0.08:
            opportunities.append("Self-management or lower-cost property manager could improve cash flow")
        
        # Market opportunities
        if metrics.cap_rate and metrics.cap_rate > 8:
            opportunities.append("High cap rate suggests potential for appreciation as market improves")
        
        # Financing opportunities
        if inputs.interest_rate > 0.06:
            opportunities.append("Future refinancing at lower rates could significantly improve cash flow")
        
        return opportunities

# Utility functions for external use
def quick_analysis(purchase_price: float, monthly_rent: float, expenses: float) -> Dict[str, float]:
    """Quick financial analysis for basic screening"""
    annual_income = monthly_rent * 12
    annual_expenses = expenses * 12
    noi = annual_income - annual_expenses
    
    return {
        "noi": noi,
        "cap_rate": (noi / purchase_price) * 100 if purchase_price > 0 else 0,
        "monthly_cash_flow": (noi / 12) - (purchase_price * 0.75 * 0.055 / 12),  # Rough estimate
        "1_percent_rule": (monthly_rent / purchase_price) * 100,
        "gross_rent_multiplier": purchase_price / annual_income if annual_income > 0 else 0
    }

def format_currency(amount: float, compact: bool = False) -> str:
    """Format currency for display"""
    if compact and abs(amount) >= 1000000:
        return f"${amount/1000000:.1f}M"
    elif compact and abs(amount) >= 1000:
        return f"${amount/1000:.0f}K"
    else:
        return f"${amount:,.0f}"

def format_percentage(value: float, decimals: int = 1) -> str:
    """Format percentage for display"""
    return f"{value:.{decimals}f}%"