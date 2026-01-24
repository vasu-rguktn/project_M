import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
import os
from datetime import datetime, timedelta
import random
import uuid

# Optional dotenv support. If python-dotenv is not installed, you can set
# DATABASE_URL via system environment or PowerShell before running.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return None

DATABASE_URL = os.getenv('DATABASE_URL')
MOCK_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'mock_data.json')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required. Please set it in your .env file")

def init_database():
    """Initialize PostgreSQL database with schema"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Drop existing tables if they exist (to avoid schema conflicts)
        print("🔄 Dropping existing tables if they exist...")
        drop_tables = [
            "DROP TABLE IF EXISTS holdings_events CASCADE",
            "DROP TABLE IF EXISTS alerts CASCADE",
            "DROP TABLE IF EXISTS arbitrage_opportunities CASCADE",
            "DROP TABLE IF EXISTS holdings CASCADE",
            "DROP TABLE IF EXISTS portfolio_snapshots CASCADE",
            "DROP TABLE IF EXISTS portfolio CASCADE",
            "DROP TABLE IF EXISTS price_history CASCADE",
            "DROP TABLE IF EXISTS watchlists CASCADE",
            "DROP TABLE IF EXISTS assets CASCADE",
            "DROP TABLE IF EXISTS orders CASCADE",
            "DROP TABLE IF EXISTS wines CASCADE",
            "DROP TABLE IF EXISTS users CASCADE"
        ]
        
        for drop_stmt in drop_tables:
            try:
                cursor.execute(drop_stmt)
            except Exception as e:
                pass  # Ignore errors if tables don't exist
        
        # Use PostgreSQL schema file
        schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if not os.path.exists(schema_file):
            schema_file = os.path.join(os.path.dirname(__file__), 'schema_postgresql.sql')
        
        with open(schema_file, 'r') as f:
            schema = f.read()
        
        # Remove comments and split by semicolon, but keep multi-line statements together
        # Filter out empty lines and comments
        lines = []
        for line in schema.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        # Join and split by semicolon
        full_schema = ' '.join(lines)
        statements = [s.strip() + ';' for s in full_schema.split(';') if s.strip()]
        
        print("🔄 Creating tables and indexes...")
        for statement in statements:
            if statement and statement != ';':
                try:
                    cursor.execute(statement)
                except Exception as e:
                    error_msg = str(e).lower()
                    # Ignore "already exists" and "duplicate" errors
                    if 'already exists' not in error_msg and 'duplicate' not in error_msg:
                        # For indexes, ignore if table doesn't exist yet (will be created)
                        if 'does not exist' in error_msg and 'index' in statement.lower():
                            continue
                        print(f"Warning: {e}")
        
        cursor.close()
        conn.close()
        print(f"✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

def generate_mock_data():
    """Generate comprehensive mock data for the dashboard"""
    
    regions = ['Bordeaux', 'Burgundy', 'Champagne', 'Tuscany', 'Napa Valley', 'Rioja', 'Barossa Valley', 'Mendoza']
    wine_types = ['Red', 'White', 'Rosé', 'Sparkling']
    
    producers = {
        'Bordeaux': ['Château Margaux', 'Château Lafite Rothschild', 'Château Latour', 'Château Mouton Rothschild', 'Château Haut-Brion', 'Château Pétrus', 'Château Cheval Blanc', 'Château Ausone'],
        'Burgundy': ['Domaine de la Romanée-Conti', 'Domaine Leroy', 'Domaine Armand Rousseau', 'Domaine Comte de Vogüé', 'Domaine Leflaive', 'Domaine Coche-Dury'],
        'Champagne': ['Dom Pérignon', 'Krug', 'Cristal', 'Salon', 'Bollinger', 'Veuve Clicquot'],
        'Tuscany': ['Sassicaia', 'Ornellaia', 'Tignanello', 'Masseto', 'Solaia'],
        'Napa Valley': ['Screaming Eagle', 'Harlan Estate', 'Opus One', 'Caymus', 'Stag\'s Leap'],
        'Rioja': ['Vega Sicilia', 'Marqués de Riscal', 'La Rioja Alta', 'Muga'],
        'Barossa Valley': ['Penfolds Grange', 'Henschke Hill of Grace', 'Torbreck'],
        'Mendoza': ['Catena Zapata', 'Achaval-Ferrer', 'Nicolás Catena']
    }
    
    assets = []
    price_history = []
    arbitrage_opportunities = []
    alerts = []
    
    base_date = datetime.now()
    
    # Generate 150+ assets
    asset_id_counter = 1
    for region in regions:
        region_producers = producers.get(region, ['Premium Producer'])
        for producer in region_producers[:3]:  # Limit producers per region
            for vintage in range(2010, 2020):
                asset_id = f"asset_{asset_id_counter:04d}"
                wine_type = random.choice(wine_types) if region != 'Champagne' else 'Sparkling'
                # Generate base price in INR (converted from USD range 200-5000)
                base_price = random.uniform(16600, 415000)  # INR (200*83 to 5000*83)
                
                assets.append({
                    'asset_id': asset_id,
                    'name': f"{producer} {vintage}",
                    'producer': producer,
                    'region': region,
                    'vintage': vintage,
                    'wine_type': wine_type,
                    'base_price': round(base_price, 2)
                })
                
                # Generate price history for last 30 days
                current_price = base_price
                for day_offset in range(30, -1, -1):
                    date = (base_date - timedelta(days=day_offset)).strftime('%Y-%m-%d')
                    # Price variation
                    change_factor = random.uniform(0.95, 1.05)
                    current_price = max(8300, current_price * change_factor)  # Minimum 100 USD = 8300 INR
                    
                    trend = 'stable'
                    if change_factor > 1.02:
                        trend = 'up'
                    elif change_factor < 0.98:
                        trend = 'down'
                    
                    confidence = random.uniform(0.65, 0.95)
                    
                    price_history.append({
                        'asset_id': asset_id,
                        'region': region,
                        'date': date,
                        'price': round(current_price, 2),
                        'confidence': round(confidence, 2),
                        'trend': trend
                    })
                
                asset_id_counter += 1
                if asset_id_counter > 150:
                    break
            if asset_id_counter > 150:
                break
        if asset_id_counter > 150:
            break
    
    # Generate arbitrage opportunities
    for i in range(20):
        asset = random.choice(assets)
        buy_region = asset['region']
        sell_regions = [r for r in regions if r != buy_region]
        sell_region = random.choice(sell_regions)
        
        buy_price = asset['base_price'] * random.uniform(0.9, 1.0)
        sell_price = buy_price * random.uniform(1.1, 1.35)
        expected_profit = round(sell_price - buy_price, 2)
        confidence = random.uniform(0.7, 0.95)
        
        arbitrage_opportunities.append({
            'asset_id': asset['asset_id'],
            'buy_region': buy_region,
            'sell_region': sell_region,
            'buy_price': round(buy_price, 2),
            'sell_price': round(sell_price, 2),
            'expected_profit': expected_profit,
            'confidence': round(confidence, 2),
            'volume_available': random.randint(1, 5)
        })
    
    # Generate alerts
    alert_types = ['price_drop', 'price_spike', 'arbitrage', 'portfolio_alert', 'market_alert']
    severities = ['low', 'medium', 'high', 'critical']
    
    for i in range(15):
        alert_type = random.choice(alert_types)
        severity = random.choice(severities)
        asset = random.choice(assets)
        
        messages = {
            'price_drop': f"{asset['name']} dropped {random.randint(5, 20)}% in the last 24 hours",
            'price_spike': f"{asset['name']} surged {random.randint(10, 30)}% in the last 24 hours",
            'arbitrage': f"New arbitrage opportunity: {asset['name']}",
            'portfolio_alert': f"Your holding {asset['name']} has significant movement",
            'market_alert': f"Market alert: {asset['region']} region showing unusual activity"
        }
        
        alerts.append({
            'type': alert_type,
            'message': messages[alert_type],
            'severity': severity,
            'asset_id': asset['asset_id'],
            'value': round(asset['base_price'] * random.uniform(0.8, 1.2), 2),
            'threshold': round(asset['base_price'], 2),
            'read': False
        })
    
    mock_data = {
        'assets': assets,
        'price_history': price_history,
        'arbitrage_opportunities': arbitrage_opportunities,
        'alerts': alerts
    }
    
    with open(MOCK_DATA_PATH, 'w') as f:
        json.dump(mock_data, f, indent=2)
    
    print(f"✅ Generated mock data: {len(assets)} assets, {len(price_history)} price records, {len(arbitrage_opportunities)} arbitrage opportunities, {len(alerts)} alerts")
    return mock_data

def load_mock_data_to_db(mock_data):
    """Load mock data into PostgreSQL database"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM arbitrage_opportunities")
    cursor.execute("DELETE FROM holdings")
    cursor.execute("DELETE FROM price_history")
    cursor.execute("DELETE FROM assets")
    cursor.execute("DELETE FROM portfolio")
    
    # Insert assets
    for asset in mock_data['assets']:
        cursor.execute("""
            INSERT INTO assets (asset_id, name, producer, region, vintage, wine_type, base_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            asset['asset_id'],
            asset['name'],
            asset.get('producer', ''),
            asset['region'],
            asset.get('vintage'),
            asset.get('wine_type', 'Red'),
            asset['base_price']
        ))
    
    # Insert price history
    for ph in mock_data['price_history']:
        cursor.execute("""
            INSERT INTO price_history (asset_id, region, date, price, confidence, trend)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (asset_id, region, date) DO UPDATE SET
                price = EXCLUDED.price,
                confidence = EXCLUDED.confidence,
                trend = EXCLUDED.trend
        """, (
            ph['asset_id'],
            ph['region'],
            ph['date'],
            ph['price'],
            ph.get('confidence', 0.75),
            ph.get('trend', 'stable')
        ))
    
    # Insert arbitrage opportunities
    for arb in mock_data['arbitrage_opportunities']:
        cursor.execute("""
            INSERT INTO arbitrage_opportunities 
            (asset_id, buy_region, sell_region, buy_price, sell_price, expected_profit, confidence, volume_available)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            arb['asset_id'],
            arb['buy_region'],
            arb['sell_region'],
            arb['buy_price'],
            arb['sell_price'],
            arb['expected_profit'],
            arb.get('confidence', 0.75),
            arb.get('volume_available', 1)
        ))
    
    # Insert alerts
    for alert in mock_data['alerts']:
        cursor.execute("""
            INSERT INTO alerts (type, message, severity, asset_id, value, threshold, read)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            alert['type'],
            alert['message'],
            alert['severity'],
            alert.get('asset_id'),
            alert.get('value'),
            alert.get('threshold'),
            alert.get('read', False)
        ))
    
    # Create demo portfolio
    demo_user_id = 'demo-user'
    demo_holdings = random.sample(mock_data['assets'], min(8, len(mock_data['assets'])))
    
    total_value = 0
    total_cost = 0
    
    for asset in demo_holdings:
        quantity = random.randint(1, 3)
        buy_price = asset['base_price'] * random.uniform(0.85, 1.0)
        current_price = asset['base_price'] * random.uniform(0.9, 1.15)
        
        cursor.execute("""
            INSERT INTO holdings (user_id, asset_id, quantity, buy_price, current_value)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            demo_user_id,
            asset['asset_id'],
            quantity,
            buy_price,
            current_price
        ))
        
        total_value += current_price * quantity
        total_cost += buy_price * quantity
    
    today_change = total_value - total_cost
    change_percent = (today_change / total_cost * 100) if total_cost > 0 else 0
    avg_roi = change_percent
    
    # Calculate total bottles from holdings
    cursor.execute("SELECT SUM(quantity) as total FROM holdings WHERE user_id = %s", (demo_user_id,))
    bottles_row = cursor.fetchone()
    bottles = bottles_row[0] if bottles_row and bottles_row[0] else 0
    
    regions_str = ','.join(set(a['region'] for a in demo_holdings))
    
    cursor.execute("""
        INSERT INTO portfolio (user_id, total_value, today_change, change_percent, bottles, regions, avg_roi)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            total_value = EXCLUDED.total_value,
            today_change = EXCLUDED.today_change,
            change_percent = EXCLUDED.change_percent,
            bottles = EXCLUDED.bottles,
            regions = EXCLUDED.regions,
            avg_roi = EXCLUDED.avg_roi,
            updated_at = CURRENT_TIMESTAMP
    """, (
        demo_user_id,
        round(total_value, 2),
        round(today_change, 2),
        round(change_percent, 2),
        bottles,
        regions_str,
        round(avg_roi, 2)
    ))
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Loaded mock data into database")

if __name__ == '__main__':
    print("🚀 Initializing ChronoShift database...")
    init_database()
    mock_data = generate_mock_data()
    load_mock_data_to_db(mock_data)
    print("✅ Database setup complete!")

