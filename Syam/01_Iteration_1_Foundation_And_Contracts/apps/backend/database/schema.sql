-- PostgreSQL schema for ChronoShift Wine Trading Dashboard

CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    producer TEXT,
    region TEXT NOT NULL,
    vintage INTEGER,
    wine_type TEXT,
    base_price REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    asset_id TEXT NOT NULL,
    region TEXT NOT NULL,
    date TEXT NOT NULL,
    price REAL NOT NULL,
    confidence REAL DEFAULT 0.75,
    trend TEXT DEFAULT 'stable',
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id),
    UNIQUE(asset_id, region, date)
);

CREATE TABLE IF NOT EXISTS portfolio (
    user_id TEXT PRIMARY KEY,
    total_value REAL DEFAULT 0,
    today_change REAL DEFAULT 0,
    change_percent REAL DEFAULT 0,
    bottles INTEGER DEFAULT 0,
    regions TEXT,
    avg_roi REAL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    date TEXT NOT NULL,
    total_value REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
    UNIQUE(user_id, asset_id)
);

CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    buy_price REAL NOT NULL,
    current_value REAL NOT NULL,
    source TEXT NOT NULL DEFAULT 'MANUAL_BUY',
    status TEXT NOT NULL DEFAULT 'OPEN',
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id),
    CHECK (status IN ('OPEN', 'PARTIALLY_SOLD', 'SOLD', 'CANCELLED')),
    CHECK (source IN ('MANUAL_BUY', 'ARBITRAGE_SIMULATION', 'TRANSFER')),
    CHECK (quantity >= 0)
);

CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    id SERIAL PRIMARY KEY,
    asset_id TEXT NOT NULL,
    buy_region TEXT NOT NULL,
    sell_region TEXT NOT NULL,
    buy_price REAL NOT NULL,
    sell_price REAL NOT NULL,
    expected_profit REAL NOT NULL,
    confidence REAL DEFAULT 0.75,
    volume_available INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL,
    asset_id TEXT,
    value REAL,
    threshold REAL,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS holdings_events (
    id SERIAL PRIMARY KEY,
    holding_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    before_state TEXT,
    after_state TEXT,
    quantity_change INTEGER DEFAULT 0,
    price REAL,
    triggered_by TEXT NOT NULL DEFAULT 'USER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (holding_id) REFERENCES holdings(id) ON DELETE CASCADE,
    CHECK (event_type IN ('BUY', 'SELL', 'CLOSE', 'PARTIAL_SELL')),
    CHECK (triggered_by IN ('USER', 'SYSTEM'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_price_history_asset_date ON price_history(asset_id, date);
CREATE INDEX IF NOT EXISTS idx_price_history_region ON price_history(region);
CREATE INDEX IF NOT EXISTS idx_holdings_user ON holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_status ON holdings(status);
CREATE INDEX IF NOT EXISTS idx_holdings_user_status ON holdings(user_id, status);
CREATE INDEX IF NOT EXISTS idx_holdings_events_holding ON holdings_events(holding_id);
CREATE INDEX IF NOT EXISTS idx_holdings_events_user ON holdings_events(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_events_type ON holdings_events(event_type);
CREATE INDEX IF NOT EXISTS idx_arbitrage_asset ON arbitrage_opportunities(asset_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity, read);
CREATE INDEX IF NOT EXISTS idx_assets_region ON assets(region);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_date ON portfolio_snapshots(user_id, date);
CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlists_asset ON watchlists(asset_id);

