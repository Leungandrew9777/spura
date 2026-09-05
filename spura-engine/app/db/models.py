from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Competition(Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    country = Column(String)
    is_european = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    matches = relationship("Match", back_populates="competition")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    country = Column(String)
    league_code = Column(String, index=True)
    understat_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), index=True)
    season = Column(String, index=True)
    match_date = Column(DateTime, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    result = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    competition = relationship("Competition", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    position = Column(String)
    understat_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    team = relationship("Team")


class PlayerStats(Base):
    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), index=True)
    player_id = Column(Integer, ForeignKey("players.id"), index=True)
    minutes = Column(Integer)
    goals = Column(Integer)
    shots = Column(Integer)
    shots_on_target = Column(Integer)
    xg = Column(Float)
    xa = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class PlayerSeasonStats(Base):
    __tablename__ = "player_season_stats"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), index=True)
    league_code = Column(String, index=True)
    season = Column(String, index=True)
    games = Column(Integer)
    minutes = Column(Integer)
    goals = Column(Integer)
    assists = Column(Integer)
    xg = Column(Float)
    xa = Column(Float)
    shots = Column(Integer)
    key_passes = Column(Integer)
    position = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    player = relationship("Player")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), index=True)
    player_id = Column(Integer, ForeignKey("players.id"), index=True)
    probability = Column(Float)
    fair_odds = Column(Float)
    market_odds = Column(Float)
    ev = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class ModelMetrics(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True)
    league = Column(String, index=True)
    brier_score = Column(Float)
    log_loss = Column(Float)
    sample_size = Column(Integer)
    timestamp = Column(DateTime, server_default=func.now())
