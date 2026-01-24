"""
Pydantic Schemas for Agent State and Outputs

Defines the shared state structure passed between LangGraph nodes.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AgentState(BaseModel):
    """
    Shared state passed across all LangGraph nodes.
    This state is updated by each node and passed to the next.
    """
    
    # User Context
    user_id: str = Field(..., description="Authenticated user ID")
    
    # Input (optional asset filter)
    asset_id: Optional[str] = Field(None, description="Optional asset ID to focus analysis on")
    
    # Data Fetched from Backend
    portfolio_summary: Optional[Dict[str, Any]] = Field(None, description="Portfolio summary from backend")
    holdings: Optional[List[Dict[str, Any]]] = Field(None, description="User holdings from backend")
    market_pulse: Optional[Dict[str, float]] = Field(None, description="Market pulse by region")
    arbitrage_opportunities: Optional[List[Dict[str, Any]]] = Field(None, description="Available arbitrage opportunities")
    
    # Agent Analysis Results
    price_predictions: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Price predictions by asset_id")
    arbitrage_analysis: Optional[List[Dict[str, Any]]] = Field(None, description="Analyzed arbitrage opportunities")
    recommendation: Optional[Dict[str, Any]] = Field(None, description="Final recommendation (BUY/SELL/HOLD)")
    compliance_status: Optional[str] = Field(None, description="Compliance check result: PASS, FAIL, or PENDING")
    explanation: Optional[str] = Field(None, description="Human-readable explanation of the recommendation")
    
    # Metadata
    errors: List[str] = Field(default_factory=list, description="List of errors encountered during execution")
    warnings: List[str] = Field(default_factory=list, description="List of warnings encountered")
    execution_time_ms: Optional[int] = Field(None, description="Total execution time in milliseconds")
    
    class Config:
        """Pydantic config"""
        extra = "allow"  # Allow additional fields for flexibility


class AgentOutput(BaseModel):
    """
    Final output from agent execution.
    This is what gets returned to the caller.
    """
    
    success: bool = Field(..., description="Whether execution succeeded")
    user_id: str = Field(..., description="User ID")
    recommendation: Optional[Dict[str, Any]] = Field(None, description="Final recommendation")
    explanation: Optional[str] = Field(None, description="Human-readable explanation (Phase 9 compatibility)")
    structured_explanation: Optional[Dict[str, Any]] = Field(None, description="Phase 10 structured explanation")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in recommendation (0-1)")
    compliance_status: Optional[str] = Field(None, description="Compliance status")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Any warnings")
    execution_time_ms: Optional[int] = Field(None, description="Execution time")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of execution")
    agent_version: str = Field(default="phase-10", description="Agent version identifier")
    terminated_reason: str = Field(default="completed", description="completed, early_exit, or timeout")


class PricePrediction(BaseModel):
    """Price prediction for a single asset"""
    
    asset_id: str
    asset_name: str
    current_price: float
    predicted_price: float
    confidence: float = Field(ge=0.0, le=1.0)
    trend: str = Field(..., description="up, down, or stable")
    reasoning: str


class ArbitrageAnalysis(BaseModel):
    """Arbitrage opportunity analysis"""
    
    asset_id: str
    asset_name: str
    buy_region: str
    sell_region: str
    buy_price: float
    sell_price: float
    expected_profit: float
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    reasoning: str


class Recommendation(BaseModel):
    """Trading recommendation"""
    
    action: str = Field(..., description="BUY, SELL, or HOLD")
    asset_id: Optional[str] = None
    quantity: Optional[int] = None
    expected_roi: Optional[float] = None
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    compliance_status: str = Field(..., description="PASS, FAIL, or PENDING")


# Phase 10: Structured Explanation Schemas
class ExplanationFactor(BaseModel):
    """Individual factor contributing to the recommendation"""
    
    name: str = Field(..., description="Name of the factor")
    impact: str = Field(..., description="positive, negative, or neutral")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight of this factor (0-1)")
    evidence: str = Field(..., description="Short factual justification derived from real data")


class RiskAnalysis(BaseModel):
    """Risk analysis breakdown"""
    
    liquidity: str = Field(..., description="low, medium, or high")
    volatility: str = Field(..., description="low, medium, or high")
    market_stability: str = Field(..., description="low, medium, or high")


class StructuredExplanation(BaseModel):
    """Phase 10 structured explanation for AI recommendations"""
    
    summary: str = Field(..., description="2-3 sentence human-readable explanation grounded only in computed signals")
    factors: List[ExplanationFactor] = Field(default_factory=list, description="List of factors contributing to the decision")
    risk_analysis: Optional[RiskAnalysis] = Field(None, description="Risk analysis breakdown")
    uncertainties: List[str] = Field(default_factory=list, description="Explicit data gaps or confidence limitations")