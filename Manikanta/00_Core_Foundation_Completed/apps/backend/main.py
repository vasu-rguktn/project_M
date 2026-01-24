"""
ChronoShift Wine Trading Intelligence Dashboard API

Tech Stack: Python + FastAPI + PostgreSQL

We chose Python + FastAPI + PostgreSQL to support:
- Agentic workflows and AI-driven extensions
- Temporal simulations and time-series analysis
- Advanced data processing and analytics
- Future machine learning integrations
- Production scalability with PostgreSQL

This replaces the previous Node.js/Express setup to better support
the intelligent trading features and agent-based architecture.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import uuid
import json
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel
from models.schemas import (
    PortfolioSummaryResponse,
    ErrorResponse,
    AlertResponse,
    ArbitrageOpportunityResponse,
    WatchlistResponse,
    WatchlistItemResponse,
    AddToWatchlistRequest,
    RemoveFromWatchlistRequest,
    BuyHoldingRequest,
    SellHoldingRequest,
    CloseHoldingRequest,
    HoldingDetailResponse,
    SoldHoldingResponse,
    RealizedProfitSummaryResponse,
    AgentProposalResponse,
    AgentProposalDetailResponse,
    AgentRunRequest,
    AgentRunResponse,
    CreateSimulationRequest,
    ApproveSimulationRequest,
    RejectSimulationRequest,
    SimulatedOrderResponse,
    SimulationsListResponse,
    AuditLogResponse,
    RecordOutcomeRequest,
    OutcomeResponse,
    OutcomesListResponse,
    PerformanceMetricsResponse,
    LearningMetricsResponse,
    AutonomyStatusResponse,
    AutonomyPolicyResponse,
    EnableAutonomyRequest,
    AutonomyExecutionLogResponse,
    AutonomousExecutionResponse,
    AutonomousExecutionsListResponse,
    RunAutonomousExecutionRequest,
    RunAutonomousExecutionResponse
)
from middleware.logging_middleware import LoggingMiddleware, log_authentication_attempt, log_portfolio_access
# Import authentication - try production auth, fallback to basic
try:
    from auth.clerk_verify import get_current_user_production
    get_authenticated_user = get_current_user_production
except (ImportError, AttributeError):
    from auth.clerk_auth import get_current_user
    get_authenticated_user = get_current_user

from services.portfolio_service import calculate_portfolio_summary
from services.snapshot_service import get_portfolio_trend, create_portfolio_snapshot
from services.user_service import ensure_user_portfolio_initialized
from services.snapshot_initialization import ensure_snapshot_exists
from services.agent_service import trigger_agent_workflow, get_user_proposals, get_proposal_detail
from services.simulation_service import (
    create_simulation_from_proposal,
    approve_simulation,
    reject_simulation,
    execute_simulation,
    get_user_simulations,
    get_simulation_detail
)
from services.outcome_service import (
    record_outcome,
    get_user_outcomes,
    compute_performance_metrics
)
from services.outcome_realization_service import (
    realize_outcomes_for_executed_simulations,
    get_realized_outcomes
)
from services.learning_service import (
    compute_learning_metrics,
    update_strategy_performance
)
from services.feedback_signal_service import (
    generate_feedback_signals,
    get_feedback_signals
)
from services.portfolio_capital_service import (
    get_portfolio_capital,
    compute_exposure,
    get_portfolio_constraints,
    set_portfolio_constraint,
    validate_constraints,
    initialize_portfolio_capital
)
from services.strategy_service import (
    get_strategy_performance,
    assign_strategy_to_simulation
)
from services.audit_service import (
    get_decision_lineage,
    get_policy_evaluations
)
from services.explainability_service import (
    compute_confidence_drift,
    compute_proposal_diff,
    generate_narrative_summary,
    compute_strategy_reliability
)
from services.autonomy_service import (
    toggle_kill_switch,
    check_kill_switch,
    get_autonomy_status,
    check_autonomy_policy,
    execute_autonomous_simulation as execute_autonomous_simulation_phase14
)
from services.execution_engine import (
    execute_autonomous_simulation,
    get_pending_approved_simulations
)
from services.execution_audit import (
    log_execution_event,
    get_execution_audit_log
)
from services.watchlist_service import (
    add_to_watchlist,
    remove_from_watchlist,
    get_user_watchlist,
    is_in_watchlist
)
from services.holdings_service import (
    create_holding,
    sell_holding,
    close_holding,
    get_active_holdings,
    get_holdings_history
)
from services.sold_holdings_service import (
    get_sold_holdings,
    get_total_realized_profit
)

# Optional dotenv support so the backend still runs even if python-dotenv
# is not installed. In that case you can set env vars via PowerShell or system env.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return None

app = FastAPI(
    title="ChronoShift API", 
    version="1.0.0",
    description="Wine trading intelligence dashboard API. Built with Python + FastAPI + PostgreSQL to support agentic workflows, temporal simulations, and future AI-driven extensions."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "Content-Type"],
)

# Logging middleware for audit trail
app.add_middleware(LoggingMiddleware)

# Configure logger for this module
logger = logging.getLogger("chronoshift.api")

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required. Please set it in your .env file")

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"ok": True, "database": "connected"}
    except Exception as e:
        return {"ok": False, "database": "disconnected", "error": str(e)}

@app.get("/api/portfolio/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(user_id: str = Depends(get_authenticated_user)):
    """Get portfolio summary for authenticated user"""
    try:
        conn = get_db_connection()
        
        # Ensure user has initialized portfolio (for new users)
        ensure_user_portfolio_initialized(conn, user_id)
        
        # Calculate portfolio summary dynamically
        summary = calculate_portfolio_summary(conn, user_id)
        
        # Ensure today's snapshot exists for trend chart (always up-to-date)
        ensure_snapshot_exists(conn, user_id)
        
        log_portfolio_access(user_id, "/api/portfolio/summary", True)
        
        conn.close()
        return PortfolioSummaryResponse(**summary)
    except HTTPException:
        raise
    except Exception as e:
        log_portfolio_access(user_id, "/api/portfolio/summary", False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch portfolio summary: {str(e)}"
        )

@app.get("/api/portfolio/holdings")
async def get_portfolio_holdings(user_id: str = Depends(get_authenticated_user)):
    """Get portfolio holdings for authenticated user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Ensure user_id is validated (defensive check)
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=401, detail="Invalid user ID")
        
        cursor.execute("""
            SELECT 
                h.id,
                h.asset_id,
                a.name as asset_name,
                a.vintage,
                a.region,
                h.quantity,
                h.buy_price,
                h.current_value,
                h.source,
                h.status,
                h.opened_at,
                h.closed_at,
                (h.current_value - h.buy_price) * h.quantity as profit_loss,
                ((h.current_value - h.buy_price) / h.buy_price * 100) as roi_percent
            FROM holdings h
            JOIN assets a ON h.asset_id = a.asset_id
            WHERE h.user_id = %s
            AND h.status IN ('OPEN', 'PARTIALLY_SOLD')
            ORDER BY h.opened_at DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        
        holdings = []
        for row in rows:
            # Get latest trend from price_history
            cursor2 = conn.cursor(cursor_factory=RealDictCursor)
            cursor2.execute("""
                SELECT trend FROM price_history
                WHERE asset_id = %s AND region = %s
                ORDER BY date DESC
                LIMIT 1
            """, (row["asset_id"], row["region"]))
            trend_row = cursor2.fetchone()
            trend = trend_row["trend"] if trend_row else "stable"
            cursor2.close()
            
            holdings.append({
                "id": row["id"],
                "asset_id": row["asset_id"],
                "asset_name": row["asset_name"],
                "vintage": row["vintage"],
                "region": row["region"],
                "quantity": row["quantity"],
                "buy_price": round(float(row["buy_price"]), 2),
                "current_value": round(float(row["current_value"]), 2),
                "source": row["source"],
                "status": row["status"],
                "profit_loss": round(float(row["profit_loss"]), 2),
                "roi_percent": round(float(row["roi_percent"]), 2),
                "trend": trend
            })
        
        conn.close()
        return holdings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/pulse")
async def get_market_pulse():
    """Get market pulse by region (public endpoint - no auth required)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get latest prices for each region
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT 
                a.region,
                AVG(CASE WHEN ph.date = %s THEN ph.price ELSE NULL END) as today_price,
                AVG(CASE WHEN ph.date = %s THEN ph.price ELSE NULL END) as yesterday_price
            FROM assets a
            LEFT JOIN price_history ph ON a.asset_id = ph.asset_id AND a.region = ph.region
            WHERE ph.date IN (%s, %s)
            GROUP BY a.region
        """, (today, yesterday, today, yesterday))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        pulse = {}
        for row in rows:
            today_price = float(row["today_price"]) if row["today_price"] else None
            yesterday_price = float(row["yesterday_price"]) if row["yesterday_price"] else None
            if today_price and yesterday_price:
                change_percent = ((today_price - yesterday_price) / yesterday_price) * 100
                pulse[row["region"]] = round(change_percent, 2)
            else:
                pulse[row["region"]] = 0.0
        
        return pulse
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/arbitrage", response_model=List[ArbitrageOpportunityResponse])
async def get_arbitrage_opportunities(limit: int = 10):
    """Get arbitrage opportunities (public endpoint - no auth required)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                a.asset_id,
                a.name as asset_name,
                a.vintage,
                arb.buy_region,
                arb.sell_region,
                arb.buy_price,
                arb.sell_price,
                arb.expected_profit,
                arb.confidence,
                arb.volume_available
            FROM arbitrage_opportunities arb
            JOIN assets a ON arb.asset_id = a.asset_id
            ORDER BY arb.expected_profit DESC
            LIMIT %s
        """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        opportunities = []
        for row in rows:
            opportunities.append({
                "asset_id": row["asset_id"],
                "asset_name": row["asset_name"],
                "vintage": row["vintage"],
                "buy_region": row["buy_region"],
                "sell_region": row["sell_region"],
                "buy_price": round(float(row["buy_price"]), 2),
                "sell_price": round(float(row["sell_price"]), 2),
                "expected_profit": round(float(row["expected_profit"]), 2),
                "confidence": round(float(row["confidence"]), 2),
                "volume_available": row["volume_available"]
            })
        
        return opportunities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/trend")
async def get_portfolio_trend_endpoint(user_id: str = Depends(get_authenticated_user), days: int = 30):
    """Get portfolio trend data for authenticated user"""
    try:
        conn = get_db_connection()
        
        # Ensure user_id is validated
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=401, detail="Invalid user ID")
        
        # Ensure user has initialized portfolio
        ensure_user_portfolio_initialized(conn, user_id)
        
        # Ensure snapshot exists before fetching trend
        ensure_snapshot_exists(conn, user_id)
        
        # Get trend data from snapshots (ensures today's snapshot exists)
        trend_data = get_portfolio_trend(conn, user_id, days, ensure_today=True)
        
        log_portfolio_access(user_id, "/api/portfolio/trend", True)
        
        conn.close()
        return trend_data
    except HTTPException:
        raise
    except Exception as e:
        log_portfolio_access(user_id, "/api/portfolio/trend", False)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts", response_model=List[AlertResponse])
async def get_alerts(
    user_id: str = Depends(get_authenticated_user), 
    limit: int = 20,
    offset: int = 0
):
    """Get alerts for authenticated user"""
    conn = None
    cursor = None
    try:
        # Ensure user_id is validated (defensive check)
        if not user_id or user_id.strip() == "":
            logger.warning(f"Invalid user_id in alerts endpoint: {user_id}")
            return []
        
        # Validate limit parameter
        if limit < 1 or limit > 100:
            limit = 20
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get alerts for user's holdings (alerts related to assets user owns)
        # Also include general alerts (where asset_id is NULL)
        # Query logic: Show alerts if they are general (asset_id IS NULL) OR if user owns the asset
        # Get alerts for user's watchlist and holdings
        # Log for debugging
        logger.info(f"Fetching alerts for user {user_id} (limit={limit}, offset={offset})")
        
        # Query alerts for user's watchlist and holdings
        # Note: Using DISTINCT is not needed here since alerts are unique by id
        # and we're filtering by user-specific watchlist/holdings
        cursor.execute("""
            SELECT
                a.id,
                a.type,
                a.message,
                a.severity,
                a.asset_id,
                a.value,
                a.threshold,
                a.explanation,
                a.created_at,
                COALESCE(a.read, FALSE) as read
            FROM alerts a
            WHERE (
                a.asset_id IS NULL 
                OR a.asset_id IN (SELECT asset_id FROM holdings WHERE user_id = %s)
                OR a.asset_id IN (SELECT asset_id FROM watchlists WHERE user_id = %s)
            )
            ORDER BY 
                CASE a.severity
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 1
                    ELSE 0
                END DESC,
                a.created_at DESC NULLS LAST
            LIMIT %s OFFSET %s
        """, (user_id, user_id, limit, offset))
        
        rows = cursor.fetchall()
        logger.info(f"Found {len(rows)} alerts for user {user_id}")
        
        alerts = []
        for row in rows:
            try:
                # Safe type conversions with proper null handling
                alert_data = {
                    "id": int(row.get("id", 0)) if row.get("id") is not None else 0,
                    "type": str(row.get("type", "")) if row.get("type") else "unknown",
                    "message": str(row.get("message", "")) if row.get("message") else "",
                    "severity": str(row.get("severity", "low")) if row.get("severity") else "low",
                    "asset_id": str(row.get("asset_id")) if row.get("asset_id") else None,
                    "explanation": str(row.get("explanation")) if row.get("explanation") else None,
                    "value": None,
                    "threshold": None,
                    "created_at": None,
                    "read": bool(row.get("read", False)) if row.get("read") is not None else False
                }
                
                # Safe float conversion for value
                if row.get("value") is not None:
                    try:
                        alert_data["value"] = round(float(row["value"]), 2)
                    except (ValueError, TypeError):
                        alert_data["value"] = None
                
                # Safe float conversion for threshold
                if row.get("threshold") is not None:
                    try:
                        alert_data["threshold"] = round(float(row["threshold"]), 2)
                    except (ValueError, TypeError):
                        alert_data["threshold"] = None
                
                # Safe datetime conversion
                if row.get("created_at") is not None:
                    try:
                        alert_data["created_at"] = str(row["created_at"])
                    except (ValueError, TypeError):
                        alert_data["created_at"] = None
                
                alerts.append(alert_data)
            except Exception as row_error:
                logger.error(f"Error processing alert row: {row_error}, row: {row}")
                continue  # Skip problematic rows instead of failing entire request
        
        return alerts
        
    except psycopg2.Error as db_error:
        logger.error(f"Database error in alerts endpoint: {db_error}")
        # Return empty list instead of failing - graceful degradation
        return []
    except HTTPException:
        # Re-raise HTTP exceptions (like auth failures)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in alerts endpoint: {e}", exc_info=True)
        # Return empty list instead of 500 error - graceful degradation
        return []
    finally:
        # Ensure database connections are always closed
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

# Watchlist endpoints
@app.get("/api/watchlist", response_model=WatchlistResponse)
async def get_watchlist(user_id: str = Depends(get_authenticated_user)):
    """Get user's watchlist"""
    try:
        conn = get_db_connection()
        items = get_user_watchlist(conn, user_id)
        conn.close()
        return WatchlistResponse(
            items=[WatchlistItemResponse(**item) for item in items],
            count=len(items)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watchlist/add")
async def add_watchlist_item(
    request: AddToWatchlistRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Add asset to user's watchlist"""
    try:
        conn = get_db_connection()
        if not request.asset_id or not request.asset_id.strip():
            raise HTTPException(status_code=400, detail="asset_id is required")
        added = add_to_watchlist(conn, user_id, request.asset_id)
        conn.close()
        return {"success": True, "message": "Asset added to watchlist"} if added else {"success": False, "message": "Asset already in watchlist"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/watchlist/remove")
async def remove_watchlist_item(
    request: RemoveFromWatchlistRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Remove asset from user's watchlist"""
    try:
        conn = get_db_connection()
        if not request.asset_id or not request.asset_id.strip():
            raise HTTPException(status_code=400, detail="asset_id is required")
        removed = remove_from_watchlist(conn, user_id, request.asset_id)
        conn.close()
        return {"success": True, "message": "Asset removed from watchlist"} if removed else {"success": False, "message": "Asset not in watchlist"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/watchlist/check/{asset_id}")
async def check_watchlist_status(
    asset_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Check if an asset is in user's watchlist"""
    try:
        conn = get_db_connection()
        in_watchlist = is_in_watchlist(conn, user_id, asset_id)
        conn.close()
        return {"asset_id": asset_id, "in_watchlist": in_watchlist}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Holdings endpoints
@app.post("/api/holdings/buy")
async def buy_holding(
    request: BuyHoldingRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Simulate buying a holding"""
    conn = None
    try:
        conn = get_db_connection()
        holding = create_holding(
            conn, user_id, request.asset_id, request.quantity,
            request.buy_price, request.source
        )
        return {"success": True, "holding": holding}
    except ValueError as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        import traceback
        logger.error(f"Error buying holding: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.post("/api/holdings/sell")
async def sell_holding_endpoint(
    request: SellHoldingRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Sell a holding (partial or full)"""
    conn = None
    try:
        conn = get_db_connection()
        holding = sell_holding(
            conn, user_id, request.holding_id,
            request.quantity, request.sell_price
        )
        # Note: sell_holding already creates snapshot, but we ensure it's updated
        from services.snapshot_service import create_portfolio_snapshot
        create_portfolio_snapshot(conn, user_id, force_update=True)
        return {
            "success": True, 
            "holding": holding,
            "message": f"Successfully sold {abs(holding.get('quantity_change', 0)) if 'quantity_change' in holding else 'holding'}"
        }
    except ValueError as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        import traceback
        logger.error(f"Error selling holding: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.post("/api/holdings/close")
async def close_holding_endpoint(
    request: CloseHoldingRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Close a holding (cancel it)"""
    try:
        conn = get_db_connection()
        holding = close_holding(conn, user_id, request.holding_id)
        conn.close()
        return {"success": True, "holding": holding}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/holdings/active")
async def get_active_holdings_endpoint(
    user_id: str = Depends(get_authenticated_user)
):
    """Get active holdings for authenticated user (OPEN and PARTIALLY_SOLD)"""
    try:
        conn = get_db_connection()
        holdings = get_active_holdings(conn, user_id)
        conn.close()
        
        # Add trend data for each holding
        result = []
        for h in holdings:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT trend FROM price_history
                WHERE asset_id = %s AND region = %s
                ORDER BY date DESC
                LIMIT 1
            """, (h["asset_id"], h["region"]))
            trend_row = cursor.fetchone()
            trend = trend_row["trend"] if trend_row else "stable"
            cursor.close()
            conn.close()
            
            h["trend"] = trend
            result.append(h)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/holdings/history")
async def get_holdings_history_endpoint(
    user_id: str = Depends(get_authenticated_user),
    limit: int = 100
):
    """Get holdings history for authenticated user (all statuses)"""
    try:
        conn = get_db_connection()
        holdings = get_holdings_history(conn, user_id, limit)
        conn.close()
        
        # Add trend data for each holding
        result = []
        for h in holdings:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT trend FROM price_history
                WHERE asset_id = %s AND region = %s
                ORDER BY date DESC
                LIMIT 1
            """, (h["asset_id"], h["region"]))
            trend_row = cursor.fetchone()
            trend = trend_row["trend"] if trend_row else "stable"
            cursor.close()
            conn.close()
            
            h["trend"] = trend
            result.append(h)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/holdings/sold", response_model=List[SoldHoldingResponse])
async def get_sold_holdings_endpoint(
    user_id: str = Depends(get_authenticated_user),
    limit: int = 100
):
    """Get sold holdings with realized profit/loss for authenticated user"""
    try:
        conn = get_db_connection()
        sold_holdings = get_sold_holdings(conn, user_id, limit)
        conn.close()
        return sold_holdings
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/holdings/realized-profit", response_model=RealizedProfitSummaryResponse)
async def get_realized_profit_summary(
    user_id: str = Depends(get_authenticated_user)
):
    """Get total realized profit/loss summary for authenticated user"""
    try:
        conn = get_db_connection()
        summary = get_total_realized_profit(conn, user_id)
        conn.close()
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/run", response_model=AgentRunResponse)
async def run_agent_analysis(
    request: AgentRunRequest,
    user_id: str = Depends(get_authenticated_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Trigger agent analysis workflow for authenticated user"""
    import logging
    import asyncio
    import concurrent.futures
    logger = logging.getLogger(__name__)
    
    try:
        # Input validation: Log warning if asset_id is None but don't reject
        # (asset_id=None is explicitly supported for portfolio-wide analysis)
        if request.asset_id is not None and request.asset_id.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="asset_id cannot be an empty string. Use null for portfolio-wide analysis."
            )
        
        logger.info(f"Starting agent analysis for user {user_id}, asset_id={request.asset_id}")
        
        # Run agent workflow in thread pool to avoid blocking FastAPI event loop
        # This ensures the endpoint returns quickly while agent runs in background
        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Execute with timeout to prevent hanging
        # Use 55 seconds to leave buffer before subprocess timeout (60s)
        MAX_AGENT_TIMEOUT = 55.0
        
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    trigger_agent_workflow,
                    user_id,
                    request.asset_id
                ),
                timeout=MAX_AGENT_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"Agent execution timed out after {MAX_AGENT_TIMEOUT} seconds")
            return AgentRunResponse(
                success=False,
                workflow="advisor_graph",
                error=f"Agent execution timed out after {MAX_AGENT_TIMEOUT} seconds. The analysis may be taking longer than expected."
            )
        finally:
            executor.shutdown(wait=False)
        
        logger.info(f"Agent analysis completed: success={result.get('success')}, error={result.get('error')}")
        
        if result.get("success"):
            return AgentRunResponse(
                success=True,
                workflow="advisor_graph",
                run_id=result.get("proposal_id"),
                results=result
            )
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Agent analysis failed: {error_msg}")
            return AgentRunResponse(
                success=False,
                workflow="advisor_graph",
                error=error_msg
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception during agent analysis: {str(e)}", exc_info=True)
        return AgentRunResponse(
            success=False,
            workflow="advisor_graph",
            error=f"Internal error: {str(e)}"
        )


@app.get("/api/agent/proposals", response_model=List[AgentProposalResponse])
async def get_agent_proposals(
    user_id: str = Depends(get_authenticated_user),
    limit: int = 50,
    proposal_type: Optional[str] = None
):
    """Get agent proposals for authenticated user"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Fetching agent proposals for user {user_id}, limit={limit}, type={proposal_type}")
        conn = get_db_connection()
        proposals = get_user_proposals(conn, user_id, limit, proposal_type)
        logger.info(f"Found {len(proposals)} proposals from database")
        
        # CRITICAL FIX: Add evidence AND structured_explanation to each proposal
        for proposal in proposals:
            try:
                detail = get_proposal_detail(conn, proposal["proposal_id"], user_id)
                if detail:
                    # Add evidence if available
                    if detail.get("evidence"):
                        proposal["evidence"] = detail["evidence"]
                        logger.debug(f"Added {len(detail['evidence'])} evidence items to proposal {proposal['proposal_id']}")
                    
                    # CRITICAL: Add structured_explanation if available
                    if detail.get("structured_explanation"):
                        proposal["structured_explanation"] = detail["structured_explanation"]
                        logger.info(f"Added structured_explanation to proposal {proposal['proposal_id']}")
                    else:
                        logger.warning(f"No structured_explanation found for proposal {proposal['proposal_id']}")
                    
                    # Ensure risk_score is properly set
                    if detail.get("risk_score") is not None:
                        proposal["risk_score"] = detail["risk_score"]
                else:
                    logger.warning(f"get_proposal_detail returned None for proposal {proposal['proposal_id']}")
            except Exception as detail_error:
                logger.error(f"Error fetching detail for proposal {proposal.get('proposal_id', 'unknown')}: {detail_error}", exc_info=True)
                # Continue with other proposals even if one fails
        
        conn.close()
        logger.info(f"Returning {len(proposals)} proposals with structured_explanation")
        return proposals
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent proposals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/proposals/{proposal_id}", response_model=AgentProposalDetailResponse)
async def get_agent_proposal_detail(
    proposal_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get detailed agent proposal with evidence"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Fetching proposal detail for proposal_id={proposal_id}, user_id={user_id}")
        conn = get_db_connection()
        proposal = get_proposal_detail(conn, proposal_id, user_id)
        conn.close()
        
        if not proposal:
            logger.warning(f"Proposal {proposal_id} not found for user {user_id}")
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Log structured_explanation status
        if proposal.get("structured_explanation"):
            logger.info(f"Proposal {proposal_id} has structured_explanation with {len(proposal.get('structured_explanation', {}).get('factors', []))} factors")
        else:
            logger.warning(f"Proposal {proposal_id} missing structured_explanation")
        
        # Log risk_score status
        if proposal.get("risk_score") is not None:
            logger.info(f"Proposal {proposal_id} has risk_score: {proposal['risk_score']}")
        else:
            logger.warning(f"Proposal {proposal_id} missing risk_score")
        
        return proposal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching proposal detail for {proposal_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 11: Simulated Execution Endpoints
def _convert_simulation_to_response(simulation: Dict) -> SimulatedOrderResponse:
    """Helper to convert simulation dict to SimulatedOrderResponse"""
    from models.schemas import SimulationResult
    
    sim_result = None
    if simulation.get('simulation_result'):
        sr = simulation['simulation_result']
        if isinstance(sr, dict):
            sim_result = SimulationResult(**sr)
        elif isinstance(sr, str):
            try:
                import json
                sim_result = SimulationResult(**json.loads(sr))
            except (json.JSONDecodeError, TypeError):
                pass
    
    return SimulatedOrderResponse(
        id=str(simulation['id']),
        user_id=simulation['user_id'],
        asset_id=simulation['asset_id'],
        asset_name=simulation.get('asset_name'),
        proposal_id=simulation.get('proposal_id'),
        action=simulation['action'],
        quantity=simulation['quantity'],
        buy_region=simulation.get('buy_region'),
        sell_region=simulation.get('sell_region'),
        expected_roi=simulation.get('expected_roi'),
        confidence=simulation.get('confidence'),
        risk_score=simulation.get('risk_score'),
        simulation_result=sim_result,
        status=simulation['status'],
        created_at=simulation['created_at'].isoformat() if isinstance(simulation['created_at'], datetime) else str(simulation['created_at']),
        approved_at=simulation['approved_at'].isoformat() if simulation.get('approved_at') and isinstance(simulation['approved_at'], datetime) else None,
        executed_at=simulation['executed_at'].isoformat() if simulation.get('executed_at') and isinstance(simulation['executed_at'], datetime) else None,
        rejection_reason=simulation.get('rejection_reason')
    )


@app.post("/api/simulations/create", response_model=SimulatedOrderResponse)
async def create_simulation(
    request: CreateSimulationRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Create a simulated order from an AI recommendation"""
    logger.info(f"Creating simulation from proposal {request.proposal_id} for user {user_id}")
    
    try:
        conn = get_db_connection()
        simulation = create_simulation_from_proposal(
            user_id=user_id,
            proposal_id=request.proposal_id,
            quantity=request.quantity,
            conn=conn
        )
        conn.close()
        
        return _convert_simulation_to_response(simulation)
    except ValueError as e:
        logger.error(f"Validation error creating simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulations/approve", response_model=SimulatedOrderResponse)
async def approve_simulation_endpoint(
    request: ApproveSimulationRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Approve a simulated order (user-initiated)"""
    logger.info(f"User {user_id} approving simulation {request.simulation_id}")
    
    try:
        conn = get_db_connection()
        simulation = approve_simulation(
            user_id=user_id,
            simulation_id=request.simulation_id,
            conn=conn
        )
        conn.close()
        
        return _convert_simulation_to_response(simulation)
    except ValueError as e:
        logger.error(f"Validation error approving simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulations/reject", response_model=SimulatedOrderResponse)
async def reject_simulation_endpoint(
    request: RejectSimulationRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Reject a simulated order (user-initiated)"""
    logger.info(f"User {user_id} rejecting simulation {request.simulation_id}")
    
    try:
        conn = get_db_connection()
        simulation = reject_simulation(
            user_id=user_id,
            simulation_id=request.simulation_id,
            reason=request.reason,
            conn=conn
        )
        conn.close()
        
        return _convert_simulation_to_response(simulation)
    except ValueError as e:
        logger.error(f"Validation error rejecting simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rejecting simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulations/{simulation_id}/execute", response_model=SimulatedOrderResponse)
async def execute_simulation_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Mark a simulation as executed (simulated only - no real trading)"""
    logger.info(f"Executing simulation {simulation_id} for user {user_id}")
    
    try:
        conn = get_db_connection()
        simulation = execute_simulation(
            user_id=user_id,
            simulation_id=simulation_id,
            conn=conn
        )
        conn.close()
        
        return _convert_simulation_to_response(simulation)
    except ValueError as e:
        logger.error(f"Validation error executing simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulations", response_model=SimulationsListResponse)
async def get_simulations(
    user_id: str = Depends(get_authenticated_user),
    status: Optional[str] = None,
    limit: int = 50
):
    """Get all simulations for authenticated user"""
    logger.info(f"Fetching simulations for user {user_id}, status={status}, limit={limit}")
    
    try:
        conn = get_db_connection()
        simulations = get_user_simulations(
            user_id=user_id,
            status=status,
            limit=limit,
            conn=conn
        )
        conn.close()
        
        # Convert to response format
        simulation_responses = [_convert_simulation_to_response(sim) for sim in simulations]
        
        return SimulationsListResponse(
            simulations=simulation_responses,
            count=len(simulation_responses)
        )
    except Exception as e:
        logger.error(f"Error fetching simulations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulations/{simulation_id}", response_model=SimulatedOrderResponse)
async def get_simulation_detail_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get detailed simulation data including audit log"""
    logger.info(f"Fetching simulation detail {simulation_id} for user {user_id}")
    
    try:
        conn = get_db_connection()
        simulation = get_simulation_detail(
            simulation_id=simulation_id,
            user_id=user_id,
            conn=conn
        )
        conn.close()
        
        if not simulation:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        return _convert_simulation_to_response(simulation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching simulation detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 12: Outcome Tracking Endpoints (Read-Only for Agents)
@app.post("/api/outcomes/record", response_model=OutcomeResponse)
async def record_outcome_endpoint(
    request: RecordOutcomeRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Record an execution outcome for a simulated order (IMMUTABLE)"""
    logger.info(f"Recording outcome for simulation {request.simulation_id} (user {user_id})")
    
    try:
        # Validate outcome_status
        if request.outcome_status not in ['SUCCESS', 'NEUTRAL', 'NEGATIVE']:
            raise HTTPException(status_code=400, detail="outcome_status must be SUCCESS, NEUTRAL, or NEGATIVE")
        
        # Validate liquidity_signal if provided
        if request.liquidity_signal and request.liquidity_signal not in ['HIGH', 'MEDIUM', 'LOW']:
            raise HTTPException(status_code=400, detail="liquidity_signal must be HIGH, MEDIUM, or LOW")
        
        conn = get_db_connection()
        outcome = record_outcome(
            user_id=user_id,
            simulation_id=request.simulation_id,
            actual_roi=request.actual_roi,
            holding_period_days=request.holding_period_days,
            volatility_observed=request.volatility_observed,
            liquidity_signal=request.liquidity_signal,
            market_drift=request.market_drift,
            outcome_status=request.outcome_status,
            conn=conn
        )
        conn.close()
        
        return OutcomeResponse(
            id=str(outcome['id']),
            simulation_id=str(outcome['simulation_id']),
            user_id=outcome['user_id'],
            asset_id=outcome['asset_id'],
            asset_name=outcome.get('asset_name'),
            expected_roi=outcome.get('expected_roi'),
            actual_roi=outcome.get('actual_roi'),
            roi_delta=outcome.get('roi_delta'),
            holding_period_days=outcome.get('holding_period_days'),
            volatility_observed=outcome.get('volatility_observed'),
            liquidity_signal=outcome.get('liquidity_signal'),
            market_drift=outcome.get('market_drift'),
            outcome_status=outcome['outcome_status'],
            recorded_at=outcome['recorded_at'].isoformat() if isinstance(outcome['recorded_at'], datetime) else str(outcome['recorded_at']),
            recommendation_id=outcome.get('recommendation_id')
        )
    except ValueError as e:
        logger.error(f"Validation error recording outcome: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error recording outcome: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/outcomes", response_model=OutcomesListResponse)
async def get_outcomes(
    user_id: str = Depends(get_authenticated_user),
    limit: int = 50
):
    """Get all execution outcomes for authenticated user (READ-ONLY)"""
    logger.info(f"Fetching outcomes for user {user_id}, limit={limit}")
    
    try:
        conn = get_db_connection()
        outcomes = get_user_outcomes(
            user_id=user_id,
            limit=limit,
            conn=conn
        )
        conn.close()
        
        outcome_responses = []
        for outcome in outcomes:
            outcome_responses.append(OutcomeResponse(
                id=str(outcome['id']),
                simulation_id=str(outcome['simulation_id']),
                user_id=outcome['user_id'],
                asset_id=outcome['asset_id'],
                asset_name=outcome.get('asset_name'),
                expected_roi=outcome.get('expected_roi'),
                actual_roi=outcome.get('actual_roi'),
                roi_delta=outcome.get('roi_delta'),
                holding_period_days=outcome.get('holding_period_days'),
                volatility_observed=outcome.get('volatility_observed'),
                liquidity_signal=outcome.get('liquidity_signal'),
                market_drift=outcome.get('market_drift'),
                outcome_status=outcome['outcome_status'],
                recorded_at=outcome['recorded_at'].isoformat() if isinstance(outcome['recorded_at'], datetime) else str(outcome['recorded_at']),
                recommendation_id=outcome.get('recommendation_id')
            ))
        
        return OutcomesListResponse(
            outcomes=outcome_responses,
            count=len(outcome_responses)
        )
    except Exception as e:
        logger.error(f"Error fetching outcomes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 17: Outcome Realization Endpoints
@app.post("/api/outcomes/realize")
async def realize_outcomes_endpoint(
    user_id: str = Depends(get_authenticated_user),
    min_holding_period_days: int = 1
):
    """Manually trigger outcome realization for executed simulations (Phase 17)"""
    logger.info(f"User {user_id} triggering outcome realization (min_holding_period: {min_holding_period_days} days)")
    
    try:
        conn = get_db_connection()
        result = realize_outcomes_for_executed_simulations(
            user_id=user_id,
            min_holding_period_days=min_holding_period_days,
            conn=conn
        )
        conn.close()
        
        return {
            'success': True,
            'processed': result['processed'],
            'realized': result['realized'],
            'skipped': result['skipped'],
            'errors': result['errors'],
            'details': result['details']
        }
    except Exception as e:
        logger.error(f"Error realizing outcomes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/outcomes/realized", response_model=OutcomesListResponse)
async def get_realized_outcomes_endpoint(
    user_id: str = Depends(get_authenticated_user),
    limit: int = 50
):
    """Get realized outcomes for authenticated user (Phase 17)"""
    logger.info(f"Fetching realized outcomes for user {user_id}, limit={limit}")
    
    try:
        conn = get_db_connection()
        outcomes = get_realized_outcomes(
            user_id=user_id,
            limit=limit,
            conn=conn
        )
        conn.close()
        
        # Convert to OutcomeResponse format for compatibility
        outcome_responses = []
        for outcome in outcomes:
            outcome_responses.append(OutcomeResponse(
                id=str(outcome['id']),
                simulation_id=str(outcome['simulation_id']),
                user_id=outcome['user_id'],
                asset_id=outcome['asset_id'],
                asset_name=outcome.get('asset_name'),
                expected_roi=outcome.get('expected_roi'),
                actual_roi=outcome.get('actual_roi'),
                roi_delta=outcome.get('roi_delta'),
                holding_period_days=outcome.get('holding_period_days'),
                volatility_observed=outcome.get('volatility_observed'),
                liquidity_signal=outcome.get('liquidity_signal'),
                market_drift=outcome.get('market_drift'),
                outcome_status=outcome['outcome_status'],
                recorded_at=outcome['evaluated_at'].isoformat() if isinstance(outcome['evaluated_at'], datetime) else str(outcome['evaluated_at']),
                recommendation_id=None  # Will be linked via decision_outcome_links if needed
            ))
        
        return OutcomesListResponse(
            outcomes=outcome_responses,
            count=len(outcome_responses)
        )
    except Exception as e:
        logger.error(f"Error fetching realized outcomes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/outcomes/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    user_id: str = Depends(get_authenticated_user)
):
    """Get aggregated performance metrics (READ-ONLY, no behavior modification)"""
    logger.info(f"Computing performance metrics for user {user_id}")
    
    try:
        conn = get_db_connection()
        metrics = compute_performance_metrics(
            user_id=user_id,
            conn=conn
        )
        conn.close()
        
        return PerformanceMetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"Error computing performance metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 13: Learning & Calibration Endpoints (Read-Only)
@app.get("/api/learning/metrics", response_model=LearningMetricsResponse)
async def get_learning_metrics(
    user_id: str = Depends(get_authenticated_user)
):
    """Get learning metrics and calibration data (READ-ONLY, no behavior modification)"""
    logger.info(f"Fetching learning metrics for user {user_id}")
    
    try:
        conn = get_db_connection()
        metrics = compute_learning_metrics(user_id=user_id, conn=conn)
        conn.close()
        
        return LearningMetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"Error fetching learning metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 14: Guarded Autonomy Endpoints
@app.get("/api/autonomy/status", response_model=AutonomyStatusResponse)
async def get_autonomy_status_endpoint(
    user_id: str = Depends(get_authenticated_user)
):
    """Get current autonomy status and limits"""
    logger.info(f"Fetching autonomy status for user {user_id}")
    
    try:
        conn = get_db_connection()
        status = get_autonomy_status(user_id=user_id, conn=conn)
        conn.close()
        
        # Convert policies to response format
        policy_responses = []
        for policy in status.get('active_policies', []):
            policy_responses.append(AutonomyPolicyResponse(
                id=str(policy['id']),
                policy_name=policy['policy_name'],
                max_trade_value=float(policy['max_trade_value']),
                max_daily_trades=int(policy['max_daily_trades']),
                allowed_assets=policy.get('allowed_assets', []) if isinstance(policy.get('allowed_assets'), list) else [],
                allowed_regions=policy.get('allowed_regions', []) if isinstance(policy.get('allowed_regions'), list) else [],
                confidence_threshold=float(policy['confidence_threshold']),
                risk_threshold=float(policy['risk_threshold']),
                enabled=bool(policy['enabled']),
                created_at=policy['created_at'].isoformat() if isinstance(policy['created_at'], datetime) else str(policy['created_at']),
                updated_at=policy['updated_at'].isoformat() if isinstance(policy['updated_at'], datetime) else str(policy['updated_at'])
            ))
        
        return AutonomyStatusResponse(
            autonomy_enabled=status['autonomy_enabled'],
            kill_switch_active=status['kill_switch_active'],
            active_policies=policy_responses,
            daily_limits=status.get('daily_limits', {}),
            total_trades_today=status.get('total_trades_today', 0),
            total_value_today=status.get('total_value_today', 0.0)
        )
    except Exception as e:
        logger.error(f"Error fetching autonomy status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/autonomy/enable")
async def enable_autonomy(
    request: EnableAutonomyRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Enable guarded autonomy with strict limits (requires explicit confirmation)"""
    logger.warning(f"User {user_id} attempting to enable autonomy")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check kill switch - if active, disable it automatically (user has confirmed)
            if check_kill_switch(conn):
                logger.warning(f"Kill switch is active for user {user_id}, disabling it to enable autonomy")
                # Use INSERT ... ON CONFLICT to handle both insert and update
                cursor.execute("""
                    INSERT INTO autonomy_kill_switch (id, enabled, reason, disabled_by, last_updated)
                    VALUES (1, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET
                        enabled = EXCLUDED.enabled,
                        reason = EXCLUDED.reason,
                        disabled_at = CASE WHEN EXCLUDED.enabled = FALSE THEN CURRENT_TIMESTAMP ELSE NULL END,
                        disabled_by = EXCLUDED.disabled_by,
                        last_updated = CURRENT_TIMESTAMP
                """, (
                    True,  # enabled=True means kill switch is OFF (autonomy allowed)
                    f"Disabled by user {user_id} to enable autonomy",
                    user_id
                ))
                logger.warning(f"Kill switch DISABLED by user {user_id} to enable autonomy")
            
            # Validate hard limits
            max_daily = min(1, request.max_daily_trades or 1)  # Hard limit: max 1
            confidence_threshold = max(0.85, request.confidence_threshold or 0.85)  # Hard limit: min 0.85
            risk_threshold = min(0.30, request.risk_threshold or 0.30)  # Hard limit: max 0.30
            
            # Create or update policy
            policy_id = str(uuid.uuid4())
            policy_name = request.policy_name or "default_policy"
            
            cursor.execute("""
                INSERT INTO autonomy_policies (
                    id, policy_name, max_trade_value, max_daily_trades,
                    confidence_threshold, risk_threshold, enabled, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (policy_name) DO UPDATE SET
                    max_trade_value = EXCLUDED.max_trade_value,
                    max_daily_trades = EXCLUDED.max_daily_trades,
                    confidence_threshold = EXCLUDED.confidence_threshold,
                    risk_threshold = EXCLUDED.risk_threshold,
                    enabled = EXCLUDED.enabled,
                    updated_at = EXCLUDED.updated_at
            """, (
                policy_id,
                policy_name,
                request.max_trade_value or 0.0,
                max_daily,
                confidence_threshold,
                risk_threshold,
                True,
                datetime.now()
            ))
            
            conn.commit()
            logger.warning(f"Autonomy ENABLED for user {user_id} with policy {policy_id}")
            
            return {
                "success": True,
                "message": "Autonomy enabled with strict limits",
                "policy_id": policy_id,
                "limits": {
                    "max_daily_trades": max_daily,
                    "confidence_threshold": confidence_threshold,
                    "risk_threshold": risk_threshold
                }
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error enabling autonomy: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling autonomy: {e}", exc_info=True)
        error_detail = str(e)
        # Provide more helpful error messages
        if "autonomy_kill_switch" in error_detail.lower():
            error_detail = "Database error: autonomy_kill_switch table may not exist. Please run the Phase 14 migration."
        elif "autonomy_policies" in error_detail.lower():
            error_detail = "Database error: autonomy_policies table may not exist. Please run the Phase 14 migration."
        elif "unique constraint" in error_detail.lower() or "duplicate key" in error_detail.lower():
            error_detail = f"Policy '{request.policy_name or 'default_policy'}' already exists. Try a different policy name."
        raise HTTPException(status_code=500, detail=error_detail)


@app.post("/api/autonomy/disable")
async def disable_autonomy(
    user_id: str = Depends(get_authenticated_user),
    reason: Optional[str] = None
):
    """Disable all autonomous execution immediately (kill switch)"""
    logger.warning(f"User {user_id} DISABLING autonomy (kill switch)")
    
    try:
        conn = get_db_connection()
        
        # Disable all policies
        cursor = conn.cursor()
        cursor.execute("UPDATE autonomy_policies SET enabled = FALSE")
        
        # Activate kill switch
        toggle_kill_switch(enabled=False, reason=reason or "Disabled by user", disabled_by=user_id, conn=conn)
        
        conn.commit()
        conn.close()
        
        logger.warning(f"Autonomy DISABLED (kill switch activated) by user {user_id}")
        
        return {
            "success": True,
            "message": "Autonomy disabled immediately. Kill switch activated.",
            "kill_switch_active": True
        }
    except Exception as e:
        logger.error(f"Error disabling autonomy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/autonomy/execute/{simulation_id}")
async def execute_autonomous_simulation_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Execute a simulation autonomously if policy allows (STRICT LIMITS ENFORCED) - Phase 14"""
    logger.warning(f"User {user_id} attempting autonomous execution of simulation {simulation_id}")
    
    try:
        conn = get_db_connection()
        result = execute_autonomous_simulation_phase14(
            user_id=user_id,
            simulation_id=simulation_id,
            conn=conn
        )
        conn.close()
        
        logger.warning(f"Autonomous execution SUCCESS for simulation {simulation_id}")
        
        return {
            "success": True,
            "message": "Simulation executed autonomously",
            **result
        }
    except ValueError as e:
        logger.warning(f"Autonomous execution REJECTED: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error in autonomous execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 16: Autonomous Execution Engine Endpoints
@app.get("/api/executions/autonomous", response_model=AutonomousExecutionsListResponse)
async def get_autonomous_executions(
    user_id: str = Depends(get_authenticated_user),
    limit: int = 50
):
    """Get autonomous execution history for authenticated user"""
    logger.info(f"Fetching autonomous executions for user {user_id}, limit={limit}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'autonomous_executions'
            ) as exists
        """)
        result = cursor.fetchone()
        table_exists = result['exists'] if result else False
        
        if not table_exists:
            logger.warning("autonomous_executions table does not exist. Returning empty list.")
            return AutonomousExecutionsListResponse(
                executions=[],
                total=0
            )
        
        cursor.execute("""
            SELECT * FROM autonomous_executions
            WHERE user_id = %s
            ORDER BY executed_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        executions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        execution_responses = []
        for exec_record in executions:
            exec_dict = dict(exec_record)
            policy_snapshot = exec_dict.get('policy_snapshot', {})
            if isinstance(policy_snapshot, str):
                try:
                    policy_snapshot = json.loads(policy_snapshot)
                except:
                    policy_snapshot = {}
            
            execution_result = exec_dict.get('execution_result')
            if isinstance(execution_result, str):
                try:
                    execution_result = json.loads(execution_result)
                except:
                    execution_result = None
            
            execution_responses.append(AutonomousExecutionResponse(
                id=str(exec_dict['id']),
                simulation_id=str(exec_dict['simulation_id']),
                user_id=exec_dict['user_id'],
                decision=exec_dict['decision'],
                policy_snapshot=policy_snapshot,
                executed_at=exec_dict['executed_at'].isoformat() if isinstance(exec_dict['executed_at'], datetime) else str(exec_dict['executed_at']),
                failure_reason=exec_dict.get('failure_reason'),
                execution_result=execution_result
            ))
        
        return AutonomousExecutionsListResponse(
            executions=execution_responses,
            total=len(execution_responses)
        )
    except Exception as e:
        logger.error(f"Error fetching autonomous executions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/executions/run-autonomous", response_model=RunAutonomousExecutionResponse)
async def run_autonomous_execution(
    request: RunAutonomousExecutionRequest,
    user_id: str = Depends(get_authenticated_user)
):
    """Execute an approved simulation autonomously (Phase 16 - Controlled Execution Engine)"""
    logger.warning(f"User {user_id} requesting autonomous execution of simulation {request.simulation_id}")
    
    try:
        conn = get_db_connection()
        result = execute_autonomous_simulation(
            user_id=user_id,
            simulation_id=request.simulation_id,
            conn=conn
        )
        conn.close()
        
        return RunAutonomousExecutionResponse(
            success=result['success'],
            decision=result['decision'],
            execution_id=result['execution_id'],
            reason=result['reason'],
            execution_result=result.get('execution_result')
        )
    except ValueError as e:
        logger.warning(f"Autonomous execution rejected: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error in autonomous execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Internal Agent Endpoints (for agent service only)
# These endpoints use an internal API key instead of Clerk auth
INTERNAL_AGENT_API_KEY = os.getenv("INTERNAL_AGENT_API_KEY", "agent-internal-key-change-in-production")

def verify_internal_key(request):
    """Verify internal API key for agent requests"""
    from fastapi import Request
    internal_key = request.headers.get("X-Internal-Agent-Key")
    if not internal_key or internal_key != INTERNAL_AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing internal agent API key")

@app.get("/api/internal/portfolio/summary")
async def get_portfolio_summary_internal(
    user_id: str,
    request: Request
):
    """Internal endpoint for agent service - portfolio summary"""
    verify_internal_key(request)
    try:
        conn = get_db_connection()
        ensure_user_portfolio_initialized(conn, user_id)
        summary = calculate_portfolio_summary(conn, user_id)
        ensure_snapshot_exists(conn, user_id)
        conn.close()
        return PortfolioSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/internal/portfolio/holdings")
async def get_portfolio_holdings_internal(
    user_id: str,
    request: Request
):
    """Internal endpoint for agent service - portfolio holdings"""
    verify_internal_key(request)
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT 
                h.id,
                h.asset_id,
                a.name as asset_name,
                a.vintage,
                a.region,
                h.quantity,
                h.buy_price,
                h.current_value,
                h.source,
                h.status,
                h.opened_at,
                h.closed_at,
                (h.current_value - h.buy_price) * h.quantity as profit_loss,
                ((h.current_value - h.buy_price) / h.buy_price * 100) as roi_percent
            FROM holdings h
            JOIN assets a ON h.asset_id = a.asset_id
            WHERE h.user_id = %s
            AND h.status IN ('OPEN', 'PARTIALLY_SOLD')
            ORDER BY h.opened_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        holdings = []
        for row in rows:
            cursor2 = conn.cursor(cursor_factory=RealDictCursor)
            cursor2.execute("""
                SELECT trend FROM price_history
                WHERE asset_id = %s AND region = %s
                ORDER BY date DESC
                LIMIT 1
            """, (row["asset_id"], row["region"]))
            trend_row = cursor2.fetchone()
            trend = trend_row["trend"] if trend_row else "stable"
            cursor2.close()
            holdings.append({
                "id": row["id"],
                "asset_id": row["asset_id"],
                "asset_name": row["asset_name"],
                "vintage": row["vintage"],
                "region": row["region"],
                "quantity": row["quantity"],
                "buy_price": round(float(row["buy_price"]), 2),
                "current_value": round(float(row["current_value"]), 2),
                "source": row["source"],
                "status": row["status"],
                "profit_loss": round(float(row["profit_loss"]), 2),
                "roi_percent": round(float(row["roi_percent"]), 2),
                "trend": trend
            })
        conn.close()
        return holdings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Phase 20: Portfolio & Capital Engine Endpoints
@app.get("/api/portfolio/capital")
async def get_portfolio_capital_endpoint(
    user_id: str = Depends(get_authenticated_user)
):
    """Get portfolio capital for authenticated user (Phase 20)"""
    logger.info(f"Fetching portfolio capital for user {user_id}")
    
    try:
        conn = get_db_connection()
        capital = get_portfolio_capital(user_id, conn=conn)
        conn.close()
        
        return capital
    except Exception as e:
        logger.error(f"Error fetching portfolio capital: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/exposure")
async def get_portfolio_exposure_endpoint(
    user_id: str = Depends(get_authenticated_user)
):
    """Get portfolio exposure breakdown (Phase 20)"""
    logger.info(f"Computing portfolio exposure for user {user_id}")
    
    try:
        conn = get_db_connection()
        exposure = compute_exposure(user_id, conn=conn)
        conn.close()
        
        return exposure
    except Exception as e:
        logger.error(f"Error computing exposure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/constraints")
async def get_portfolio_constraints_endpoint(
    user_id: str = Depends(get_authenticated_user)
):
    """Get portfolio constraints for authenticated user (Phase 20)"""
    logger.info(f"Fetching portfolio constraints for user {user_id}")
    
    try:
        conn = get_db_connection()
        constraints = get_portfolio_constraints(user_id, conn=conn)
        conn.close()
        
        return {'constraints': constraints}
    except Exception as e:
        logger.error(f"Error fetching portfolio constraints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/constraints")
async def set_portfolio_constraint_endpoint(
    constraint_type: str,
    constraint_value: float,
    user_id: str = Depends(get_authenticated_user)
):
    """Set or update a portfolio constraint (Phase 20)"""
    logger.info(f"Setting constraint {constraint_type} = {constraint_value} for user {user_id}")
    
    try:
        conn = get_db_connection()
        constraint = set_portfolio_constraint(
            user_id=user_id,
            constraint_type=constraint_type,
            constraint_value=constraint_value,
            conn=conn
        )
        conn.close()
        
        return constraint
    except Exception as e:
        logger.error(f"Error setting portfolio constraint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 21: Strategy Layer Endpoints
@app.get("/api/strategies/performance")
async def get_strategy_performance_endpoint(
    user_id: str = Depends(get_authenticated_user)
):
    """Get strategy performance for authenticated user (Phase 21)"""
    logger.info(f"Fetching strategy performance for user {user_id}")
    
    try:
        conn = get_db_connection()
        performance = get_strategy_performance(user_id, conn=conn)
        conn.close()
        
        return {'strategies': performance}
    except Exception as e:
        logger.error(f"Error fetching strategy performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 23: Governance & Audit Endpoints
@app.get("/api/audit/decision-lineage")
async def get_decision_lineage_endpoint(
    user_id: str = Depends(get_authenticated_user),
    simulation_id: Optional[str] = None
):
    """Get decision lineage records (Phase 23)"""
    logger.info(f"Fetching decision lineage for user {user_id}, simulation={simulation_id}")
    
    try:
        conn = get_db_connection()
        lineage = get_decision_lineage(user_id, simulation_id, conn=conn)
        conn.close()
        
        return {'lineage': lineage}
    except Exception as e:
        logger.error(f"Error fetching decision lineage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit/policy-evaluations")
async def get_policy_evaluations_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get policy evaluations for a simulation (Phase 23)"""
    logger.info(f"Fetching policy evaluations for simulation {simulation_id}")
    
    try:
        conn = get_db_connection()
        evaluations = get_policy_evaluations(simulation_id, conn=conn)
        conn.close()
        
        return {'evaluations': evaluations}
    except Exception as e:
        logger.error(f"Error fetching policy evaluations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase 24: UX Trust & Explainability Endpoints
@app.get("/api/explainability/confidence-drift")
async def get_confidence_drift_endpoint(
    user_id: str = Depends(get_authenticated_user),
    days: int = 30
):
    """Get confidence drift analysis (Phase 24)"""
    logger.info(f"Computing confidence drift for user {user_id}, days={days}")
    
    try:
        conn = get_db_connection()
        drift = compute_confidence_drift(user_id, days, conn=conn)
        conn.close()
        
        return drift
    except Exception as e:
        logger.error(f"Error computing confidence drift: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/explainability/proposal-diff/{proposal_id}")
async def get_proposal_diff_endpoint(
    proposal_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get diff between current and previous proposal (Phase 24)"""
    logger.info(f"Computing proposal diff for proposal {proposal_id}, user {user_id}")
    
    try:
        conn = get_db_connection()
        diff = compute_proposal_diff(proposal_id, user_id, conn=conn)
        conn.close()
        
        return diff
    except Exception as e:
        logger.error(f"Error computing proposal diff: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/explainability/narrative/{proposal_id}")
async def get_narrative_summary_endpoint(
    proposal_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get natural language narrative summary (Phase 24)"""
    logger.info(f"Generating narrative summary for proposal {proposal_id}, user {user_id}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get proposal
        cursor.execute("""
            SELECT ap.*, a.name as asset_name
            FROM agent_proposals ap
            LEFT JOIN assets a ON ap.asset_id = a.asset_id
            WHERE ap.proposal_id = %s AND ap.user_id = %s
        """, (proposal_id, user_id))
        
        proposal = cursor.fetchone()
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Get lineage if available
        lineage = get_decision_lineage(user_id, None, conn=conn)
        lineage_for_proposal = next((l for l in lineage if l.get('simulation_id')), None)
        
        narrative = generate_narrative_summary(dict(proposal), lineage_for_proposal)
        
        cursor.close()
        conn.close()
        
        return {'narrative': narrative, 'proposal_id': proposal_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating narrative summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/explainability/strategy-reliability/{strategy_id}")
async def get_strategy_reliability_endpoint(
    strategy_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get strategy reliability score (Phase 24)"""
    logger.info(f"Computing strategy reliability for strategy {strategy_id}, user {user_id}")
    
    try:
        conn = get_db_connection()
        reliability = compute_strategy_reliability(strategy_id, user_id, conn=conn)
        conn.close()
        
        return reliability
    except Exception as e:
        logger.error(f"Error computing strategy reliability: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase C1: Execution Engine Endpoints
@app.get("/api/executions/{simulation_id}/steps")
async def get_execution_steps_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get execution steps for a simulation (Phase C1)"""
    logger.info(f"Fetching execution steps for simulation {simulation_id}, user {user_id}")
    
    try:
        # Verify simulation belongs to user
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id FROM simulated_orders
            WHERE id = %s AND user_id = %s
        """, (simulation_id, user_id))
        
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        from services.execution_engine_c1 import get_execution_steps
        steps = get_execution_steps(simulation_id, conn=conn)
        conn.close()
        
        return {'steps': steps, 'simulation_id': simulation_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution steps: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/executions/{simulation_id}/execute-step")
async def execute_step_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Execute the next pending step for a simulation (Phase C1)"""
    logger.info(f"Executing next step for simulation {simulation_id}, user {user_id}")
    
    try:
        # Verify simulation belongs to user and is APPROVED or EXECUTED
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, status FROM simulated_orders
            WHERE id = %s AND user_id = %s
        """, (simulation_id, user_id))
        
        sim = cursor.fetchone()
        if not sim:
            conn.close()
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        if sim['status'] not in ['APPROVED', 'EXECUTED']:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Simulation must be APPROVED or EXECUTED (current: {sim['status']})")
        
        from services.execution_engine_c1 import execute_next_step, is_execution_complete
        step_result = execute_next_step(simulation_id, conn=conn)
        is_complete = is_execution_complete(simulation_id, conn=conn)
        conn.close()
        
        if not step_result:
            return {'message': 'No pending steps', 'is_complete': is_complete}
        
        return {
            'step': step_result,
            'is_complete': is_complete,
            'simulation_id': simulation_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing step: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/executions/steps/{step_id}/reset")
async def reset_failed_step_endpoint(
    step_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Reset a failed step to PENDING so it can be retried (Phase C1)"""
    logger.info(f"Resetting failed step {step_id} for user {user_id}")
    
    try:
        # Verify step belongs to user's simulation
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT es.id, es.simulation_id, so.user_id
            FROM execution_steps es
            JOIN simulated_orders so ON es.simulation_id = so.id
            WHERE es.id = %s AND so.user_id = %s
        """, (step_id, user_id))
        
        step_check = cursor.fetchone()
        if not step_check:
            conn.close()
            raise HTTPException(status_code=404, detail="Step not found or not accessible")
        
        from services.execution_engine_c1 import reset_failed_step
        reset_step = reset_failed_step(step_id, conn=conn)
        conn.close()
        
        if not reset_step:
            raise HTTPException(status_code=400, detail="Step is not in FAILED status or does not exist")
        
        return {
            'step': reset_step,
            'message': 'Step reset to PENDING and ready for retry'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting step: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase C2: Compliance Reasoning Endpoints
@app.get("/api/compliance/{simulation_id}/evaluation")
async def get_compliance_evaluation_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get compliance evaluation for a simulation (Phase C2)"""
    try:
        conn = get_db_connection()
        from services.compliance_reasoning_c2 import get_compliance_evaluation
        
        # Verify simulation belongs to user
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id FROM simulated_orders
            WHERE id = %s AND user_id = %s
        """, (simulation_id, user_id))
        sim_check = cursor.fetchone()
        cursor.close()
        
        if not sim_check:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        evaluation = get_compliance_evaluation(simulation_id, conn=conn)
        conn.close()
        
        if not evaluation:
            raise HTTPException(
                status_code=404, 
                detail="Compliance evaluation not found. It will be created when the simulation is approved."
            )
        
        return evaluation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching compliance evaluation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase C3: Counterfactual Endpoints
@app.get("/api/counterfactual/{simulation_id}")
async def get_counterfactual_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get counterfactual outcome for a simulation (Phase C3)"""
    try:
        conn = get_db_connection()
        from services.counterfactual_c3 import get_counterfactual
        
        # Verify simulation belongs to user
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, status FROM simulated_orders
            WHERE id = %s AND user_id = %s
        """, (simulation_id, user_id))
        sim_check = cursor.fetchone()
        cursor.close()
        
        if not sim_check:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        counterfactual = get_counterfactual(simulation_id, conn=conn)
        conn.close()
        
        if not counterfactual:
            raise HTTPException(
                status_code=404,
                detail="Counterfactual outcome not found. It will be computed when the simulation outcome is realized."
            )
        
        return counterfactual
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching counterfactual: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase C5: Execution Gates Endpoints
@app.get("/api/executions/{simulation_id}/gates")
async def get_execution_gates_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get execution gate evaluations for a simulation (Phase C5)"""
    try:
        conn = get_db_connection()
        from services.execution_gating_c5 import get_execution_gates
        gates = get_execution_gates(simulation_id, conn=conn)
        conn.close()
        
        return {'gates': gates, 'simulation_id': simulation_id}
    except Exception as e:
        logger.error(f"Error fetching execution gates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Phase C4: Logistics Tracking Endpoints
@app.get("/api/logistics/{simulation_id}/timeline")
async def get_shipment_timeline_endpoint(
    simulation_id: str,
    user_id: str = Depends(get_authenticated_user)
):
    """Get shipment timeline with condition snapshots for a simulation (Phase C4)"""
    try:
        conn = get_db_connection()
        from services.logistics_tracking_c4 import get_shipment_timeline
        timeline = get_shipment_timeline(simulation_id, conn=conn)
        conn.close()
        
        return {'timeline': timeline, 'simulation_id': simulation_id}
    except Exception as e:
        logger.error(f"Error fetching shipment timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)

