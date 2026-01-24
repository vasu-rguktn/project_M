# ChronoShift Agent Service

Production-ready LangGraph + LangChain agentic system for wine trading intelligence.

## Overview

This service provides advisory-only agent capabilities for the ChronoShift wine trading platform. Agents analyze portfolio data, predict prices, identify arbitrage opportunities, and generate trading recommendations.

**Key Features:**
- ✅ Advisory-only (no autonomous execution)
- ✅ LangGraph for orchestration
- ✅ LangChain for LLM abstraction
- ✅ HTTP-only backend integration (no direct database access)
- ✅ Deterministic and debuggable
- ✅ Future-proof architecture

## Architecture

```
apps/agents/
├── __init__.py
├── main.py              # Entry point
├── config.py            # Configuration
├── schemas.py           # Pydantic models
├── graphs/
│   └── advisor_graph.py # LangGraph StateGraph
├── nodes/               # Individual workflow nodes
│   ├── fetch_data.py
│   ├── predict_price.py
│   ├── arbitrage_analysis.py
│   ├── recommend_action.py
│   ├── compliance_check.py
│   └── explain_decision.py
└── tools/
    └── backend_api.py   # HTTP client for backend
```

## Workflow

The advisor graph executes the following nodes in sequence:

1. **fetch_data** - Fetches portfolio, holdings, market pulse, and arbitrage data
2. **predict_price** - Predicts future prices using LLM
3. **arbitrage_analysis** - Analyzes arbitrage opportunities
4. **recommend_action** - Generates BUY/SELL/HOLD recommendations
5. **compliance_check** - Validates recommendations against risk rules
6. **explain_decision** - Generates human-readable explanations

## Setup

### 1. Install Dependencies

```bash
cd apps/agents
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `BACKEND_BASE_URL` - FastAPI backend URL (default: http://localhost:4000)
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - LLM provider API key
- `LLM_PROVIDER` - "openai" or "anthropic"
- `LLM_MODEL` - Model name (e.g., "gpt-4o-mini")

### 3. Verify Backend is Running

Ensure the FastAPI backend is running on port 4000:

```bash
cd apps/backend
python start.py
```

## Usage

### CLI Mode

Run agent workflow from command line:

```bash
python main.py <user_id> [asset_id]
```

Example:
```bash
python main.py user_123
python main.py user_123 asset_456
```

### Programmatic Usage

```python
from agents.main import run_advisor_workflow

output = await run_advisor_workflow(
    user_id="user_123",
    asset_id="asset_456"  # optional
)

print(f"Recommendation: {output.recommendation}")
print(f"Explanation: {output.explanation}")
```

## Configuration

### LLM Providers

**OpenAI:**
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

**Anthropic:**
```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=sk-ant-...
```

### Timeouts and Retries

```env
TIMEOUT_SECONDS=300  # HTTP timeout
MAX_RETRIES=3        # Retry attempts
```

## Integration with Backend

The agent service communicates with the FastAPI backend via HTTP only:

- `GET /api/portfolio/summary` - Portfolio summary
- `GET /api/portfolio/holdings` - User holdings
- `GET /api/market/pulse` - Market pulse
- `GET /api/arbitrage` - Arbitrage opportunities

**No direct database access** - All data flows through the backend API.

## Error Handling

- If any node fails, the graph stops and returns partial state
- Errors are collected in `state.errors`
- No automatic retries (configurable per node if needed)

## Testing

Test individual nodes:
```python
from agents.nodes.fetch_data import fetch_data_node

state = {"user_id": "test_user", "errors": []}
result = await fetch_data_node(state)
```

Test full workflow:
```bash
python main.py test_user
```

## Future Extensions

- **Phase 10**: Asynchronous/autonomous execution
- **Phase 11**: Multi-agent collaboration
- **Phase 12**: Advanced ML model integration
- **Phase 13**: Real-time streaming recommendations

## Constraints

- ✅ Agents are advisory-only (no trading execution)
- ✅ No database writes from agents
- ✅ No frontend modifications required
- ✅ No authentication changes needed
- ✅ Backend remains source of truth

## Troubleshooting

**Backend connection failed:**
- Verify backend is running: `curl http://localhost:4000/api/health`
- Check `BACKEND_BASE_URL` in `.env`

**LLM API errors:**
- Verify API key is set correctly
- Check API quota/limits
- Verify model name is correct

**Import errors:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version >= 3.10

## License

Part of the ChronoShift wine trading platform.
