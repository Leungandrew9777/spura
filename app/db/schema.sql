-- spura-engine/db/schema.sql
CREATE TABLE competitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    season_format VARCHAR(20),
    is_european BOOLEAN DEFAULT FALSE
);

CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER REFERENCES competitions(id),
    year VARCHAR(10),
    start_date DATE,
    end_date DATE
);

CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER REFERENCES competitions(id),
    name VARCHAR(100),
    short_name VARCHAR(50),
    external_id VARCHAR(100),
    understat_id VARCHAR(100),
    fbref_id VARCHAR(100)
);

CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    name VARCHAR(100),
    position VARCHAR(10),
    is_penalty_taker BOOLEAN DEFAULT FALSE,
    external_id VARCHAR(100),
    understat_id VARCHAR(100),
    fbref_id VARCHAR(100)
);

CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    season_id INTEGER REFERENCES seasons(id),
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    match_date TIMESTAMP,
    status VARCHAR(20),
    home_goals INTEGER,
    away_goals INTEGER,
    referee VARCHAR(100),
    stadium VARCHAR(100)
);

CREATE TABLE player_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    match_id INTEGER REFERENCES matches(id),
    minutes INTEGER,
    goals INTEGER,
    shots INTEGER,
    shots_on_target INTEGER,
    xg DECIMAL,
    xa DECIMAL,
    key_passes INTEGER
);

CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    match_id INTEGER REFERENCES matches(id),
    model_version VARCHAR(20),
    predicted_probability DECIMAL,
    fair_odds DECIMAL,
    market_odds DECIMAL,
    ev_margin DECIMAL,
    created_at TIMESTAMP
);