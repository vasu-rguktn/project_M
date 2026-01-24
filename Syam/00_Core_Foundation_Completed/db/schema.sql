-- PostgreSQL schema for Wine Investment Platform

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_id TEXT UNIQUE,
  email TEXT UNIQUE,
  full_name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE wines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lwin TEXT, -- optional wine identifier
  producer TEXT,
  name TEXT,
  vintage INT,
  region TEXT,
  critic_score INT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE holdings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
  wine_id UUID REFERENCES wines(id) ON DELETE SET NULL,
  qty INT DEFAULT 1,
  purchase_price NUMERIC(12,2),
  current_value NUMERIC(12,2),
  added_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID REFERENCES users(id),
  wine_id UUID REFERENCES wines(id),
  type TEXT, -- buy/sell
  amount NUMERIC(12,2),
  status TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

