"""
Complete Financial Calculations Module
Extracted and integrated from Multifamily Valuation Application

Provides comprehensive real estate financial analysis including:
- All core financial metrics (NOI, Cap Rate, Cash-on-Cash, IRR, DSCR, LTV)
- Advanced viability scoring and investment grading
- Multi-year projections with growth assumptions
- Sensitivity analysis for key variables
- Professional report generation capabilities
- Input validation and error handling
"""

import math
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Configuration and Constants
VIABILITY_THRESHOLDS = {
    "cap_rate": 8,          # 8% cap rate = 100 points
    "cash_on_cash": 12,     # 12% CoC = 100 points  
    "irr": 15,              # 15% IRR = 100 points
    "dscr": 1.5,            # 1.5 DSCR = 100 points
    "ltv": 60,              # 60% LTV = 100 points (lower is better)
    "equity_multiple": 2    # 2x EM = 100 points
}

VIABILITY_WEIGHTS = {
    "cap_rate": 0.15,
    "cash_on_cash": 0.20,
    "irr": 0.25,            # Highest weight
    "dscr": 0.15,
    "ltv": 0.10,
    "equity_multiple": 0.15
}

MARKET_BENCHMARKS = {
    "cap_rate_range": {"low": 4.5, "high": 7.5, "median": 6.0},
    "expense_ratio_range": {"low": 30, "high": 50, "median": 40},
    "rent_per_sqft_range": {"low": 1.0, "high": 2.5, "median": 1.75}
}

DEFAULT_ASSUMPTIONS = {
    "hold_period": 5,
    "exit_cap_rate": 0.065,       # 6.5%
    "annual_rent_growth": 0.03,   # 3%
    "annual_expense_growth": 0.025, # 2.5%
    "vacancy_rate": 0.05,         # 5%
    "management_fee": 0.05,       # 5%
    "capital_reserve": 0.02,      # 2%
    "discount_rate": 0.10         # 10%
}

@dataclass
class FinancialInputs:
    """Complete financial inputs for analysis"""
    # Property details
    purchase_price: float
    gross_income: float
    operating_expenses: float
    vacancy: float = 5.0  # Percentage
    
    # Financing
    loan_amount: float = 0.0
    interest_rate: float = 5.5  # Percentage
    loan_term: int = 30  # Years
    cash_invested: float = 0.0
    
    # Growth assumptions
    appreciation_rate: float = 3.0  # Percentage
    rent_growth_rate: float = 3.0   # Percentage
    expense_growth_rate: float = 2.5 # Percentage
    
    # Analysis parameters
    holding_period: int = 5
    cap_rate_at_sale: float = 6.5  # Percentage
    
    # Optional overrides
    asking_price: Optional[float] = None
    
    def __post_init__(self):
        """Calculate derived values"""
        if self.cash_invested == 0.0:
            self.cash_invested = self.purchase_price - self.loan_amount

@dataclass 
class FinancialProjection:
    """Single year financial projection"""
    year: int
    gross_income: float
    operating_expenses: float
    noi: float
    debt_service: float
    cash_flow: float
    property_value: float
    cumulative_cash_flow: float
    noi_growth: float = 0.0

@dataclass
class CalculationResults:
    """Complete financial analysis results"""
    # Core metrics
    noi: float
    cap_rate: float
    cash_on_cash_return: float
    irr: float
    equity_multiple: float
    dscr: float
    ltv: float
    break_even_occupancy: float
    
    # Investment analysis
    viability_score: float
    viability_rating: str
    investment_grade: str
    
    # Projections and analysis
    projections: List[FinancialProjection]
    sensitivity_analysis: Dict[str, Any]
    
    # Summary metrics
    total_cash_returned: float
    average_annual_cash_flow: float
    final_property_value: float

class FinancialCalculator:
    """Advanced financial calculator with multifamily capabilities"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize calculator with configuration"""
        self.config = config or {}
        self.assumptions = {**DEFAULT_ASSUMPTIONS, **self.config.get("assumptions", {})}
        self.thresholds = {**VIABILITY_THRESHOLDS, **self.config.get("thresholds", {})}
        self.weights = {**VIABILITY_WEIGHTS, **self.config.get("weights", {})}
    
    # Core Financial Calculations
    def calculate_noi(self, gross_income: float, operating_expenses: float, vacancy: float) -> float:
        """Calculate Net Operating Income"""
        effective_gross_income = gross_income * (1 - vacancy / 100)
        return effective_gross_income - operating_expenses
    
    def calculate_cap_rate(self, noi: float, purchase_price: float) -> float:
        """Calculate Capitalization Rate"""
        if purchase_price == 0:
            return 0.0
        return (noi / purchase_price) * 100
    
    def calculate_cash_on_cash_return(self, annual_cash_flow: float, cash_invested: float) -> float:
        """Calculate Cash-on-Cash Return"""
        if cash_invested == 0:
            return 0.0
        return (annual_cash_flow / cash_invested) * 100
    
    def calculate_debt_service(self, loan_amount: float, interest_rate: float, loan_term: int) -> float:
        """Calculate monthly debt service payment"""
        if loan_amount == 0 or interest_rate == 0:
            return 0.0
        
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term * 12
        
        return loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
    
    def calculate_dscr(self, noi: float, annual_debt_service: float) -> float:
        """Calculate Debt Service Coverage Ratio"""
        if annual_debt_service == 0:
            return 0.0
        return noi / annual_debt_service
    
    def calculate_ltv(self, loan_amount: float, purchase_price: float) -> float:
        """Calculate Loan-to-Value Ratio"""
        if purchase_price == 0:
            return 0.0
        return (loan_amount / purchase_price) * 100
    
    def calculate_break_even_occupancy(self, operating_expenses: float, annual_debt_service: float, 
                                     gross_potential_income: float) -> float:
        """Calculate Break-even Occupancy"""
        if gross_potential_income == 0:
            return 0.0
        return ((operating_expenses + annual_debt_service) / gross_potential_income) * 100
    
    def calculate_irr(self, cash_flows: List[float], initial_guess: float = 0.1, 
                     tolerance: float = 1e-7, max_iterations: int = 100) -> float:
        """Calculate Internal Rate of Return using Newton-Raphson method"""
        
        def npv(rate: float) -> float:
            """Calculate Net Present Value"""
            return sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
        
        def npv_derivative(rate: float) -> float:
            """Calculate derivative of NPV"""
            return sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))
        
        rate = initial_guess
        
        for _ in range(max_iterations):
            npv_val = npv(rate)
            
            if abs(npv_val) < tolerance:
                return rate * 100  # Return as percentage
            
            npv_deriv = npv_derivative(rate)
            if abs(npv_deriv) < tolerance:
                break  # Avoid division by zero
            
            rate = rate - npv_val / npv_deriv
        
        return rate * 100 if rate > -1 else 0.0
    
    def calculate_equity_multiple(self, total_cash_returned: float, cash_invested: float) -> float:
        """Calculate Equity Multiple"""
        if cash_invested == 0:
            return 0.0
        return total_cash_returned / cash_invested
    
    # Advanced Analysis Functions
    def generate_projections(self, inputs: FinancialInputs) -> List[FinancialProjection]:
        """Generate multi-year financial projections"""
        projections = []
        
        # Calculate initial values
        monthly_debt_service = self.calculate_debt_service(inputs.loan_amount, inputs.interest_rate, inputs.loan_term)
        annual_debt_service = monthly_debt_service * 12
        
        cumulative_cash_flow = 0.0
        
        for year in range(1, inputs.holding_period + 1):
            # Apply growth rates
            gross_income = inputs.gross_income * (1 + inputs.rent_growth_rate / 100) ** (year - 1)
            operating_expenses = inputs.operating_expenses * (1 + inputs.expense_growth_rate / 100) ** (year - 1)
            
            # Calculate NOI
            effective_gross_income = gross_income * (1 - inputs.vacancy / 100)
            noi = effective_gross_income - operating_expenses
            
            # Calculate cash flow
            cash_flow = noi - annual_debt_service
            cumulative_cash_flow += cash_flow
            
            # Calculate property value
            property_value = inputs.purchase_price * (1 + inputs.appreciation_rate / 100) ** year
            
            # NOI growth calculation
            if year == 1:
                base_noi = self.calculate_noi(inputs.gross_income, inputs.operating_expenses, inputs.vacancy)
            noi_growth = ((noi / base_noi) - 1) * 100 if base_noi > 0 else 0.0
            
            projection = FinancialProjection(
                year=year,
                gross_income=round(gross_income, 0),
                operating_expenses=round(operating_expenses, 0),
                noi=round(noi, 0),
                debt_service=round(annual_debt_service, 0),
                cash_flow=round(cash_flow, 0),
                property_value=round(property_value, 0),
                cumulative_cash_flow=round(cumulative_cash_flow, 0),
                noi_growth=round(noi_growth, 2)
            )
            
            projections.append(projection)
        
        return projections
    
    def calculate_viability_score(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive viability score (0-100)"""
        
        # Extract metrics from property data
        cap_rate = property_data.get('cap_rate', 0.05)
        cash_on_cash = property_data.get('cash_on_cash_return', 0.08) 
        irr = property_data.get('irr', 0.10)
        dscr = property_data.get('dscr', 1.2)
        ltv = property_data.get('ltv_ratio', 0.8) * 100  # Convert to percentage
        equity_multiple = property_data.get('equity_multiple', 1.5)
        
        # If cash flows are provided, calculate IRR
        if 'cash_flows' in property_data and property_data['cash_flows']:
            try:
                irr = self.calculate_irr(property_data['cash_flows'])
            except:
                pass  # Use default
        
        # Calculate NOI and cap rate if needed
        if 'noi' in property_data and 'purchase_price' in property_data:
            cap_rate = self.calculate_cap_rate(property_data['noi'], property_data['purchase_price'])
        
        # Score each metric (0-100)
        cap_rate_score = min(100, max(0, (cap_rate / self.thresholds["cap_rate"]) * 100))
        coc_score = min(100, max(0, (cash_on_cash / self.thresholds["cash_on_cash"]) * 100))
        irr_score = min(100, max(0, (irr / self.thresholds["irr"]) * 100))
        dscr_score = min(100, max(0, ((dscr - 1) / (self.thresholds["dscr"] - 1)) * 100)) if dscr > 1 else 0
        ltv_score = min(100, max(0, ((80 - ltv) / 20) * 100))  # Lower LTV is better
        em_score = min(100, max(0, ((equity_multiple - 1) / (self.thresholds["equity_multiple"] - 1)) * 100)) if equity_multiple > 1 else 0
        
        # Calculate weighted score
        total_score = (
            cap_rate_score * self.weights["cap_rate"] +
            coc_score * self.weights["cash_on_cash"] +
            irr_score * self.weights["irr"] +
            dscr_score * self.weights["dscr"] +
            ltv_score * self.weights["ltv"] +
            em_score * self.weights["equity_multiple"]
        )
        
        score = round(total_score, 1)
        
        return {
            'score': score / 100,  # Return as decimal (0-1)
            'grade': self.get_investment_grade(score),
            'rating': self.get_viability_rating(score),
            'component_scores': {
                'cap_rate': cap_rate_score,
                'cash_on_cash': coc_score,
                'irr': irr_score,
                'dscr': dscr_score,
                'ltv': ltv_score,
                'equity_multiple': em_score
            }
        }
    
    def calculate_comprehensive_analysis(self, financial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive financial analysis from inputs"""
        
        try:
            # Extract inputs
            gross_monthly_income = financial_inputs.get('gross_monthly_income', 0)
            annual_operating_expenses = financial_inputs.get('annual_operating_expenses', 0)
            purchase_price = financial_inputs.get('purchase_price', 0)
            down_payment = financial_inputs.get('down_payment', 0)
            loan_amount = financial_inputs.get('loan_amount', 0)
            interest_rate = financial_inputs.get('interest_rate', 0.065)
            loan_term = financial_inputs.get('loan_term', 30)
            
            # Calculate basic metrics
            annual_gross_income = gross_monthly_income * 12
            vacancy_rate = 0.05  # 5% default
            effective_gross_income = annual_gross_income * (1 - vacancy_rate)
            noi = effective_gross_income - annual_operating_expenses
            
            # Calculate cap rate
            cap_rate = self.calculate_cap_rate(noi, purchase_price) if purchase_price > 0 else 0
            
            # Calculate debt service
            if loan_amount > 0 and interest_rate > 0:
                monthly_rate = interest_rate / 12
                num_payments = loan_term * 12
                monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
                annual_debt_service = monthly_payment * 12
            else:
                annual_debt_service = 0
            
            # Calculate cash flow
            cash_flow = noi - annual_debt_service
            
            # Calculate cash-on-cash return
            cash_on_cash_return = cash_flow / down_payment if down_payment > 0 else 0
            
            # Calculate DSCR
            dscr = noi / annual_debt_service if annual_debt_service > 0 else 0
            
            # Calculate LTV
            ltv_ratio = loan_amount / purchase_price if purchase_price > 0 else 0
            
            return {
                'gross_income': annual_gross_income,
                'effective_gross_income': effective_gross_income,
                'operating_expenses': annual_operating_expenses,
                'noi': noi,
                'cap_rate': cap_rate,
                'debt_service': annual_debt_service,
                'cash_flow': cash_flow,
                'cash_on_cash_return': cash_on_cash_return,
                'dscr': dscr,
                'ltv_ratio': ltv_ratio,
                'equity_multiple': 1.0,  # Default, would need more complex calculation
                'irr': 0.12  # Default, would need cash flow projection
            }
            
        except Exception as e:
            # Return defaults on error
            return {
                'gross_income': 0,
                'noi': 0,
                'cap_rate': 0,
                'cash_on_cash_return': 0,
                'dscr': 0,
                'ltv_ratio': 0,
                'error': str(e)
            }
    
    def get_viability_rating(self, score: float) -> str:
        """Get viability rating based on score"""
        if score >= 85:
            return "Excellent"
        elif score >= 70:
            return "Very Good"
        elif score >= 55:
            return "Good"
        elif score >= 40:
            return "Fair"
        elif score >= 25:
            return "Marginal"
        else:
            return "Poor"
    
    def get_investment_grade(self, score: float) -> str:
        """Get investment grade based on viability score"""
        if score >= 90:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"
    
    def create_sensitivity_analysis(self, inputs: FinancialInputs, base_results: CalculationResults) -> Dict[str, Any]:
        """Create sensitivity analysis for key variables"""
        
        # Define sensitivity ranges
        rent_growth_scenarios = [-1.0, 0.0, 2.0, 3.0, 5.0]  # Percentage
        cap_rate_scenarios = [4.5, 5.5, 6.0, 6.5, 7.5]      # Percentage
        expense_growth_scenarios = [1.0, 2.0, 2.5, 3.0, 4.0] # Percentage
        
        sensitivity_results = {
            "rent_growth_sensitivity": [],
            "cap_rate_sensitivity": [],
            "expense_growth_sensitivity": [],
            "base_case": {
                "noi": base_results.noi,
                "cap_rate": base_results.cap_rate,
                "property_value": base_results.final_property_value
            }
        }
        
        # Rent growth sensitivity
        for rent_growth in rent_growth_scenarios:
            temp_inputs = inputs
            temp_inputs.rent_growth_rate = rent_growth
            
            # Calculate scenario NOI for final year
            final_year_income = inputs.gross_income * (1 + rent_growth / 100) ** inputs.holding_period
            final_year_expenses = inputs.operating_expenses * (1 + inputs.expense_growth_rate / 100) ** inputs.holding_period
            scenario_noi = self.calculate_noi(final_year_income, final_year_expenses, inputs.vacancy)
            scenario_value = scenario_noi / (inputs.cap_rate_at_sale / 100)
            
            sensitivity_results["rent_growth_sensitivity"].append({
                "rent_growth": rent_growth,
                "final_noi": round(scenario_noi, 0),
                "exit_value": round(scenario_value, 0),
                "variance_from_base": round(((scenario_value / base_results.final_property_value) - 1) * 100, 1)
            })
        
        # Cap rate sensitivity  
        for cap_rate in cap_rate_scenarios:
            scenario_value = base_results.noi / (cap_rate / 100)
            sensitivity_results["cap_rate_sensitivity"].append({
                "cap_rate": cap_rate,
                "property_value": round(scenario_value, 0),
                "variance_from_base": round(((scenario_value / base_results.final_property_value) - 1) * 100, 1)
            })
        
        # Expense growth sensitivity
        for expense_growth in expense_growth_scenarios:
            final_year_expenses = inputs.operating_expenses * (1 + expense_growth / 100) ** inputs.holding_period
            final_year_income = inputs.gross_income * (1 + inputs.rent_growth_rate / 100) ** inputs.holding_period
            scenario_noi = self.calculate_noi(final_year_income, final_year_expenses, inputs.vacancy)
            scenario_value = scenario_noi / (inputs.cap_rate_at_sale / 100)
            
            sensitivity_results["expense_growth_sensitivity"].append({
                "expense_growth": expense_growth,
                "final_noi": round(scenario_noi, 0),
                "exit_value": round(scenario_value, 0),
                "variance_from_base": round(((scenario_value / base_results.final_property_value) - 1) * 100, 1)
            })
        
        return sensitivity_results
    
    def analyze_property(self, inputs: FinancialInputs) -> CalculationResults:
        """Perform comprehensive property analysis"""
        
        # Validate inputs
        validation_errors = self.validate_inputs(inputs)
        if validation_errors:
            raise ValueError(f"Input validation failed: {', '.join(validation_errors)}")
        
        # Calculate core metrics
        noi = self.calculate_noi(inputs.gross_income, inputs.operating_expenses, inputs.vacancy)
        cap_rate = self.calculate_cap_rate(noi, inputs.purchase_price)
        monthly_debt_service = self.calculate_debt_service(inputs.loan_amount, inputs.interest_rate, inputs.loan_term)
        annual_debt_service = monthly_debt_service * 12
        annual_cash_flow = noi - annual_debt_service
        cash_on_cash = self.calculate_cash_on_cash_return(annual_cash_flow, inputs.cash_invested)
        dscr = self.calculate_dscr(noi, annual_debt_service)
        ltv = self.calculate_ltv(inputs.loan_amount, inputs.purchase_price)
        break_even_occupancy = self.calculate_break_even_occupancy(inputs.operating_expenses, annual_debt_service, inputs.gross_income)
        
        # Generate projections
        projections = self.generate_projections(inputs)
        
        # Calculate IRR from cash flows
        cash_flows = [-inputs.cash_invested]  # Initial investment (negative)
        for proj in projections:
            cash_flows.append(proj.cash_flow)
        
        # Add sale proceeds to final year
        if projections:
            final_year = projections[-1]
            # Simplified sale calculation - in production would calculate loan balance
            remaining_loan_balance = inputs.loan_amount * 0.85  # Approximate
            sale_proceeds = final_year.property_value - remaining_loan_balance
            cash_flows[-1] += sale_proceeds
        
        irr = self.calculate_irr(cash_flows)
        
        # Calculate equity multiple
        total_cash_returned = sum(cash_flows[1:])  # Exclude initial investment
        equity_multiple = self.calculate_equity_multiple(total_cash_returned, inputs.cash_invested)
        
        # Calculate viability score and ratings
        viability_score = self.calculate_viability_score(cap_rate, cash_on_cash, irr, dscr, ltv, equity_multiple)
        viability_rating = self.get_viability_rating(viability_score)
        investment_grade = self.get_investment_grade(viability_score)
        
        # Create results object
        results = CalculationResults(
            noi=round(noi, 0),
            cap_rate=round(cap_rate, 2),
            cash_on_cash_return=round(cash_on_cash, 2),
            irr=round(irr, 2),
            equity_multiple=round(equity_multiple, 2),
            dscr=round(dscr, 2),
            ltv=round(ltv, 1),
            break_even_occupancy=round(break_even_occupancy, 1),
            viability_score=viability_score,
            viability_rating=viability_rating,
            investment_grade=investment_grade,
            projections=projections,
            sensitivity_analysis={},
            total_cash_returned=round(total_cash_returned, 0),
            average_annual_cash_flow=round(sum(p.cash_flow for p in projections) / len(projections), 0) if projections else 0,
            final_property_value=projections[-1].property_value if projections else inputs.purchase_price
        )
        
        # Add sensitivity analysis
        results.sensitivity_analysis = self.create_sensitivity_analysis(inputs, results)
        
        return results
    
    def validate_inputs(self, inputs: FinancialInputs) -> List[str]:
        """Validate financial inputs"""
        errors = []
        
        if inputs.purchase_price <= 0:
            errors.append("Purchase price must be positive")
        
        if inputs.gross_income <= 0:
            errors.append("Gross income must be positive")
        
        if inputs.operating_expenses < 0:
            errors.append("Operating expenses cannot be negative")
        
        if inputs.vacancy < 0 or inputs.vacancy > 100:
            errors.append("Vacancy rate must be between 0-100%")
        
        if inputs.loan_amount < 0:
            errors.append("Loan amount cannot be negative")
        
        if inputs.loan_amount > inputs.purchase_price:
            errors.append("Loan amount cannot exceed purchase price")
        
        if inputs.interest_rate < 0 or inputs.interest_rate > 30:
            errors.append("Interest rate must be between 0-30%")
        
        if inputs.loan_term <= 0 or inputs.loan_term > 50:
            errors.append("Loan term must be between 1-50 years")
        
        if inputs.cash_invested < 0:
            errors.append("Cash invested cannot be negative")
        
        if inputs.holding_period <= 0 or inputs.holding_period > 50:
            errors.append("Holding period must be between 1-50 years")
        
        return errors

# Utility Functions
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

def format_number(value: float) -> str:
    """Format number with commas"""
    return f"{value:,.0f}"

def get_viability_color(score: float) -> str:
    """Get color class for viability score"""
    if score >= 85:
        return "bg-green-100 text-green-800 border-green-200"
    elif score >= 70:
        return "bg-blue-100 text-blue-800 border-blue-200"
    elif score >= 55:
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
    elif score >= 40:
        return "bg-orange-100 text-orange-800 border-orange-200"
    else:
        return "bg-red-100 text-red-800 border-red-200"

# Quick Analysis Functions
def quick_analysis(purchase_price: float, monthly_rent: float, monthly_expenses: float, 
                  vacancy: float = 5.0, cap_rate_threshold: float = 6.0) -> Dict[str, Any]:
    """Quick property screening analysis"""
    
    annual_income = monthly_rent * 12
    effective_annual_income = annual_income * (1 - vacancy / 100)
    annual_expenses = monthly_expenses * 12
    noi = effective_annual_income - annual_expenses
    
    # Basic calculations
    cap_rate = (noi / purchase_price) * 100 if purchase_price > 0 else 0
    gross_rent_multiplier = purchase_price / annual_income if annual_income > 0 else 0
    one_percent_rule = (monthly_rent / purchase_price) * 100 if purchase_price > 0 else 0
    
    # Rough cash flow estimate (assuming 75% LTV at 5.5%)
    estimated_loan = purchase_price * 0.75
    estimated_payment = estimated_loan * 0.055 / 12  # Rough monthly payment
    estimated_cash_flow = (noi / 12) - estimated_payment
    
    return {
        "noi": round(noi, 0),
        "cap_rate": round(cap_rate, 2),
        "monthly_cash_flow": round(estimated_cash_flow, 0),
        "1_percent_rule": round(one_percent_rule, 2),
        "gross_rent_multiplier": round(gross_rent_multiplier, 1),
        "meets_cap_rate_threshold": cap_rate >= cap_rate_threshold,
        "meets_1_percent_rule": one_percent_rule >= 1.0,
        "positive_cash_flow": estimated_cash_flow > 0,
        "recommendation": "Further Analysis" if cap_rate >= cap_rate_threshold and estimated_cash_flow > 0 else "Consider Passing"
    }

# Export data functions
def export_analysis_data(results: CalculationResults, inputs: FinancialInputs) -> Dict[str, Any]:
    """Export analysis data in structured format"""
    
    return {
        "timestamp": datetime.now().isoformat(),
        "property_analysis": {
            "inputs": asdict(inputs),
            "results": {
                "core_metrics": {
                    "noi": results.noi,
                    "cap_rate": results.cap_rate,
                    "cash_on_cash_return": results.cash_on_cash_return,
                    "irr": results.irr,
                    "equity_multiple": results.equity_multiple,
                    "dscr": results.dscr,
                    "ltv": results.ltv,
                    "break_even_occupancy": results.break_even_occupancy
                },
                "investment_analysis": {
                    "viability_score": results.viability_score,
                    "viability_rating": results.viability_rating,
                    "investment_grade": results.investment_grade,
                    "total_cash_returned": results.total_cash_returned,
                    "average_annual_cash_flow": results.average_annual_cash_flow,
                    "final_property_value": results.final_property_value
                },
                "projections": [asdict(p) for p in results.projections],
                "sensitivity_analysis": results.sensitivity_analysis
            }
        },
        "metadata": {
            "calculation_date": datetime.now().isoformat(),
            "version": "1.0",
            "source": "4plex-platform-financial-engine"
        }
    }