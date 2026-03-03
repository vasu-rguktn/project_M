"""
Pydantic Models for Request/Response Validation

This module defines all request and response models for API endpoints
to ensure type safety and validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# Portfolio Models
class PortfolioSummaryResponse(BaseModel):
    """Response model for portfolio summary"""
    total_value: float = Field(..., description="Total portfolio value in INR")
    today_change: float = Field(..., description="Change in value today in INR")
    change_percent: float = Field(..., description="Percentage change today")
    bottles: int = Field(..., description="Total number of bottles")
    regions: str = Field(..., description="Comma-separated list of regions")
    avg_roi: float = Field(..., description="Average ROI percentage")


class HoldingResponse(BaseModel):
    """Response model for a single holding"""
    asset_id: str
    asset_name: str
    vintage: Optional[int]
    region: str
    quantity: int
    current_value: float
    profit_loss: float
    roi_percent: float
    trend: str = Field(..., description="Price trend: up, down, or stable")


class PortfolioHoldingsResponse(BaseModel):
    """Response model for portfolio holdings list"""
    holdings: List[HoldingResponse]


# Trend Models
class TrendDataPoint(BaseModel):
    """Single data point for trend chart"""
    date: str = Field(..., description="Date in format 'Mon DD'")
    value: float = Field(..., description="Portfolio value on this date")


class PortfolioTrendResponse(BaseModel):
    """Response model for portfolio trend"""
    data: List[TrendDataPoint]


# Market Pulse Models
class MarketPulseResponse(BaseModel):
    """Response model for market pulse"""
    regions: dict = Field(..., description="Region name to percentage change mapping")


# Arbitrage Models
class ArbitrageOpportunityResponse(BaseModel):
    """Response model for arbitrage opportunity"""
    asset_id: str
    asset_name: str
    vintage: Optional[int]
    buy_region: str
    sell_region: str
    buy_price: float
    sell_price: float
    expected_profit: float
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    volume_available: int


# Alert Models
class AlertResponse(BaseModel):
    """Response model for an alert"""
    id: int
    type: str
    message: str
    severity: str = Field(..., description="critical, high, medium, or low")
    asset_id: Optional[str]
    value: Optional[float]
    threshold: Optional[float]
    created_at: Optional[str]
    read: bool
    explanation: Optional[str] = Field(None, description="Human-readable explanation of why this alert was generated")


# Watchlist Models
class WatchlistItemResponse(BaseModel):
    """Response model for a single watchlist item"""
    watchlist_id: int
    asset_id: str
    asset_name: str
    producer: Optional[str]
    region: str
    vintage: Optional[int]
    wine_type: Optional[str]
    base_price: float
    current_price: float
    trend: str = Field(..., description="Price trend: up, down, or stable")
    added_to_watchlist_at: Optional[str]


class WatchlistResponse(BaseModel):
    """Response model for user watchlist"""
    items: List[WatchlistItemResponse]
    count: int


class AddToWatchlistRequest(BaseModel):
    """Request model for adding to watchlist"""
    asset_id: str = Field(..., description="Asset ID to add to watchlist")


class RemoveFromWatchlistRequest(BaseModel):
    """Request model for removing from watchlist"""
    asset_id: str = Field(..., description="Asset ID to remove from watchlist")


# Holdings Models
class BuyHoldingRequest(BaseModel):
    """Request model for buying a holding"""
    asset_id: str = Field(..., description="Asset ID to buy")
    quantity: int = Field(..., gt=0, description="Quantity to buy (must be > 0)")
    buy_price: Optional[float] = Field(None, gt=0, description="Buy price (optional, uses current market price if not provided)")
    source: str = Field("MANUAL_BUY", description="Source of buy: MANUAL_BUY, ARBITRAGE_SIMULATION, or TRANSFER")


class SellHoldingRequest(BaseModel):
    """Request model for selling a holding"""
    holding_id: int = Field(..., description="Holding ID to sell")
    quantity: Optional[int] = Field(None, gt=0, description="Quantity to sell (optional, sells all if not provided)")
    sell_price: Optional[float] = Field(None, gt=0, description="Sell price (optional, uses current market price if not provided)")


class CloseHoldingRequest(BaseModel):
    """Request model for closing a holding"""
    holding_id: int = Field(..., description="Holding ID to close")


class HoldingDetailResponse(BaseModel):
    """Response model for a detailed holding"""
    id: int
    asset_id: str
    asset_name: str
    vintage: Optional[int]
    region: str
    quantity: int
    buy_price: float
    current_value: float
    source: str
    status: str
    opened_at: str
    closed_at: Optional[str]
    profit_loss: float
    roi_percent: float


class SoldHoldingResponse(BaseModel):
    """Response model for a sold holding"""
    event_id: int
    holding_id: int
    asset_id: str
    asset_name: str
    vintage: Optional[int]
    region: str
    quantity_sold: int
    buy_price: float
    sell_price: float
    cost_basis: float
    sale_proceeds: float
    realized_profit: float
    realized_roi: float
    sold_at: str
    source: str
    opened_at: str
    closed_at: Optional[str]


class RealizedProfitSummaryResponse(BaseModel):
    """Response model for realized profit summary"""
    total_sales: int
    total_quantity_sold: int
    total_cost_basis: float
    total_sale_proceeds: float
    total_realized_profit: float
    average_roi: float


# Phase 9: Agent Proposals Schemas
class AgentProposalResponse(BaseModel):
    """Response model for agent proposal in list"""
    proposal_id: str
    asset_id: str
    asset_name: str
    vintage: Optional[int]
    region: str
    proposal_type: str
    recommendation: str
    confidence_score: float
    expected_roi: Optional[float]
    risk_score: Optional[float]
    rationale: str
    compliance_status: Optional[str]
    compliance_reason: Optional[str]
    evidence: List[Dict] = []
    structured_explanation: Optional[Dict] = None  # Phase 10: Added for explainability
    created_at: str
    expires_at: Optional[str]


class AgentProposalDetailResponse(BaseModel):
    """Response model for detailed agent proposal with evidence"""
    proposal_id: str
    asset_id: str
    asset_name: str
    vintage: Optional[int]
    region: str
    proposal_type: str
    recommendation: str
    confidence_score: float
    expected_roi: Optional[float]
    risk_score: Optional[float]
    rationale: str
    compliance_status: Optional[str]
    compliance_reason: Optional[str]
    evidence: List[Dict] = []
    structured_explanation: Optional[Dict] = None  # Phase 10
    created_at: str
    expires_at: Optional[str]


class AgentRunRequest(BaseModel):
    """Request model for triggering agent analysis"""
    asset_id: Optional[str] = None


class AgentRunResponse(BaseModel):
    """Response model for agent run"""
    success: bool
    workflow: str
    run_id: Optional[str] = None
    results: Optional[Dict] = None
    error: Optional[str] = None


# Phase 11: Simulated Execution Schemas
class CreateSimulationRequest(BaseModel):
    """Request model for creating a simulated order from an AI recommendation"""
    proposal_id: str = Field(..., description="Agent proposal ID to simulate")
    quantity: int = Field(..., gt=0, description="Quantity to simulate (must be > 0)")


class ApproveSimulationRequest(BaseModel):
    """Request model for approving a simulated order"""
    simulation_id: str = Field(..., description="Simulation order ID to approve")


class RejectSimulationRequest(BaseModel):
    """Request model for rejecting a simulated order"""
    simulation_id: str = Field(..., description="Simulation order ID to reject")
    reason: Optional[str] = Field(None, description="Reason for rejection")


class SimulationResult(BaseModel):
    """Model for simulation result data"""
    projected_portfolio_value: Optional[float] = None
    projected_profit_loss: Optional[float] = None
    projected_roi: Optional[float] = None
    execution_steps: List[Dict] = []
    assumptions: List[str] = []
    warnings: List[str] = []


class SimulatedOrderResponse(BaseModel):
    """Response model for a simulated order"""
    id: str
    user_id: str
    asset_id: str
    asset_name: Optional[str] = None
    proposal_id: Optional[str] = None
    action: str
    quantity: int
    buy_region: Optional[str] = None
    sell_region: Optional[str] = None
    expected_roi: Optional[float] = None
    confidence: Optional[float] = None
    risk_score: Optional[float] = None
    simulation_result: Optional[SimulationResult] = None
    status: str
    created_at: str
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class SimulationsListResponse(BaseModel):
    """Response model for list of simulations"""
    simulations: List[SimulatedOrderResponse]
    count: int


class AuditLogEntryResponse(BaseModel):
    """Response model for an audit log entry"""
    id: str
    user_id: str
    entity_type: str
    entity_id: str
    action: str
    metadata: Optional[Dict] = None
    created_at: str


class AuditLogResponse(BaseModel):
    """Response model for audit log"""
    entries: List[AuditLogEntryResponse]
    count: int


# Phase 12: Outcome Tracking Schemas
class RecordOutcomeRequest(BaseModel):
    """Request model for recording an execution outcome"""
    simulation_id: str = Field(..., description="Simulation order ID")
    actual_roi: Optional[float] = Field(None, description="Actual ROI observed")
    holding_period_days: Optional[int] = Field(None, ge=0, description="Days held before outcome")
    volatility_observed: Optional[float] = Field(None, ge=0, description="Observed volatility")
    liquidity_signal: Optional[str] = Field(None, description="Liquidity signal: HIGH, MEDIUM, or LOW")
    market_drift: Optional[float] = Field(None, description="Market drift observed")
    outcome_status: str = Field(..., description="SUCCESS, NEUTRAL, or NEGATIVE")


class OutcomeResponse(BaseModel):
    """Response model for an execution outcome"""
    id: str
    simulation_id: str
    user_id: str
    asset_id: str
    asset_name: Optional[str] = None
    expected_roi: Optional[float] = None
    actual_roi: Optional[float] = None
    roi_delta: Optional[float] = None
    holding_period_days: Optional[int] = None
    volatility_observed: Optional[float] = None
    liquidity_signal: Optional[str] = None
    market_drift: Optional[float] = None
    outcome_status: str
    recorded_at: str
    recommendation_id: Optional[str] = None


class OutcomesListResponse(BaseModel):
    """Response model for list of outcomes"""
    outcomes: List[OutcomeResponse]
    count: int


class PerformanceMetricsResponse(BaseModel):
    """Response model for aggregated performance metrics (read-only)"""
    total_simulations: int
    total_outcomes: int
    average_expected_roi: Optional[float] = None
    average_actual_roi: Optional[float] = None
    average_roi_delta: Optional[float] = None
    success_rate: Optional[float] = None
    confidence_calibration_error: Optional[float] = None
    risk_underestimation_rate: Optional[float] = None
    region_drift_metrics: Dict[str, Dict] = {}
    outcome_distribution: Dict[str, int] = {}


# Phase 13: Learning & Calibration Schemas
class LearningMetricsResponse(BaseModel):
    """Response model for learning metrics (read-only)"""
    strategy_performance: List[Dict] = []
    confidence_calibration: List[Dict] = []
    overall_calibration_error: Optional[float] = None


# Phase 14: Guarded Autonomy Schemas
class AutonomyPolicyResponse(BaseModel):
    """Response model for autonomy policy"""
    id: str
    policy_name: str
    max_trade_value: float
    max_daily_trades: int
    allowed_assets: List[str] = []
    allowed_regions: List[str] = []
    confidence_threshold: float
    risk_threshold: float
    enabled: bool
    created_at: str
    updated_at: str


class AutonomyStatusResponse(BaseModel):
    """Response model for autonomy status"""
    autonomy_enabled: bool
    kill_switch_active: bool
    active_policies: List[AutonomyPolicyResponse] = []
    daily_limits: Dict[str, int] = {}
    total_trades_today: int = 0
    total_value_today: float = 0.0


class EnableAutonomyRequest(BaseModel):
    """Request model for enabling autonomy"""
    policy_name: Optional[str] = None
    max_trade_value: Optional[float] = Field(None, ge=0)
    max_daily_trades: Optional[int] = Field(None, ge=0, le=1)  # Hard limit: max 1 per day
    confidence_threshold: Optional[float] = Field(None, ge=0.85, le=1.0)  # Min 0.85
    risk_threshold: Optional[float] = Field(None, ge=0, le=0.30)  # Max 0.30


class AutonomyExecutionLogResponse(BaseModel):
    """Response model for autonomy execution log entry"""
    id: str
    user_id: str
    simulation_id: Optional[str] = None
    policy_id: Optional[str] = None
    execution_type: str
    trade_value: Optional[float] = None
    confidence_score: Optional[float] = None
    risk_score: Optional[float] = None
    policy_checks_passed: Optional[Dict] = None
    execution_result: Optional[str] = None
    error_message: Optional[str] = None
    executed_at: str


# Phase 16: Autonomous Execution Models
class AutonomousExecutionResponse(BaseModel):
    """Response model for autonomous execution record"""
    id: str
    simulation_id: str
    user_id: str
    decision: str = Field(..., description="EXECUTED, SKIPPED, or BLOCKED")
    policy_snapshot: Dict
    executed_at: str
    failure_reason: Optional[str] = None
    execution_result: Optional[Dict] = None


class AutonomousExecutionsListResponse(BaseModel):
    """Response model for list of autonomous executions"""
    executions: List[AutonomousExecutionResponse]
    total: int


class RunAutonomousExecutionRequest(BaseModel):
    """Request model for triggering autonomous execution"""
    simulation_id: str = Field(..., description="Simulation ID to execute autonomously")


class RunAutonomousExecutionResponse(BaseModel):
    """Response model for autonomous execution result"""
    success: bool
    decision: str = Field(..., description="EXECUTED, SKIPPED, or BLOCKED")
    execution_id: str
    reason: str
    execution_result: Optional[Dict] = None


# Error Models
class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")

