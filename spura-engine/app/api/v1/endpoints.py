import asyncio
import math
import uuid
from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket
from redis import asyncio as aioredis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Match, PlayerSeasonStats
from app.db.session import get_db
from app.ml.data_pipeline import LeagueDataPipeline, season_to_fd_code
from app.ml.feature_engineering import FeatureEngineer
from app.ml.spura_model import SpuraPredictionModel

router = APIRouter()


async def get_redis():
    redis_client = aioredis.from_url(settings.REDIS_URL)
    return redis_client


LEAGUES = [
    {"code": "E0", "name": "Premier League", "country": "ENG"},
    {"code": "E1", "name": "Championship", "country": "ENG"},
    {"code": "E2", "name": "League One", "country": "ENG"},
    {"code": "E3", "name": "League Two", "country": "ENG"},
    {"code": "EC", "name": "National League", "country": "ENG"},
    {"code": "SC0", "name": "Premiership", "country": "SCO"},
    {"code": "SC1", "name": "Division 1", "country": "SCO"},
    {"code": "SC2", "name": "Division 2", "country": "SCO"},
    {"code": "SC3", "name": "Division 3", "country": "SCO"},
    {"code": "D1", "name": "Bundesliga 1", "country": "GER"},
    {"code": "D2", "name": "Bundesliga 2", "country": "GER"},
    {"code": "SP1", "name": "La Liga", "country": "ESP"},
    {"code": "SP2", "name": "La Liga 2", "country": "ESP"},
    {"code": "I1", "name": "Serie A", "country": "ITA"},
    {"code": "I2", "name": "Serie B", "country": "ITA"},
    {"code": "F1", "name": "Ligue 1", "country": "FRA"},
    {"code": "F2", "name": "Ligue 2", "country": "FRA"},
    {"code": "N1", "name": "Eredivisie", "country": "NED"},
    {"code": "B1", "name": "Pro League", "country": "BEL"},
    {"code": "P1", "name": "Primeira Liga", "country": "POR"},
    {"code": "T1", "name": "Super Lig", "country": "TUR"},
    {"code": "G1", "name": "Super League", "country": "GRE"},
]


@router.get("/leagues")
async def list_leagues():
    return {"leagues": LEAGUES}


@router.get("/leagues/{code}")
async def get_league(code: str):
    league = next((l for l in LEAGUES if l["code"] == code.upper()), None)
    if league is None:
        raise HTTPException(status_code=404, detail="League not found")
    return league


def generate_task_id() -> str:
    return uuid.uuid4().hex


@router.post("/data/sync")
async def sync_data(
    league: str,
    season: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger data synchronization for a league."""
    task_id = generate_task_id()

    def run_sync():
        pipeline = LeagueDataPipeline(db, league)
        pipeline.sync_league_data(season)

    background_tasks.add_task(run_sync)

    return {
        "message": f"Data sync initiated for {league} {season}",
        "status": "processing",
        "task_id": task_id,
    }


@router.get("/ws/tasks/{task_id}")
async def task_status(
    task_id: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    progress = await redis.get(f"task:{task_id}:progress")
    complete = await redis.exists(f"task:{task_id}:complete")
    return {
        "task_id": task_id,
        "progress": progress.decode() if progress else None,
        "complete": bool(complete),
    }


@router.websocket("/ws/tasks/{task_id}")
async def task_websocket(
    websocket: WebSocket,
    task_id: str,
):
    await websocket.accept()
    redis = await get_redis()
    try:
        while True:
            progress = await redis.get(f"task:{task_id}:progress")
            if progress:
                await websocket.send_text(progress.decode())
            if await redis.exists(f"task:{task_id}:complete"):
                await websocket.close()
                break
            await asyncio.sleep(1)
    finally:
        await redis.aclose()


@router.post("/model/recalibrate")
async def recalibrate_model(
    league: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Retrain model for a specific league."""
    task_id = generate_task_id()

    def run_train():
        fe = FeatureEngineer(db, league)
        training_data = fe.prepare_training_data()
        if training_data.empty:
            raise ValueError(f"No training data for league {league}")
        model = SpuraPredictionModel(league)
        model.train(training_data)
        model.save_model()

    background_tasks.add_task(run_train)

    return {
        "message": f"Model recalibration initiated for {league}",
        "status": "training",
        "task_id": task_id,
    }


@router.get("/predictions/upcoming")
async def get_upcoming_predictions(
    league: str,
    days_ahead: int = 7,
    min_ev: float = 0.0,
    db: Session = Depends(get_db),
):
    """Get upcoming predictions for a league."""
    model = SpuraPredictionModel(league)
    if not model.load_model():
        raise HTTPException(status_code=404, detail="Model not found for league")

    rows = (
        db.query(PlayerSeasonStats)
        .filter(PlayerSeasonStats.league_code == league)
        .all()
    )
    if not rows:
        return {"predictions": []}

    from app.db.models import Player

    features = pd.DataFrame(
        [
            {
                "rolling_xg_5": s.xg or 0,
                "rolling_xg_10": s.xg or 0,
                "rolling_xg_20": s.xg or 0,
                "opp_defense_rating": 1.2,
                "is_home": 1,
                "is_penalty_taker": 0,
                "match_expected_goals": (s.xg or 0) * 1.1,
                "player_shots_per90": (s.shots or 0) / max((s.minutes or 0) / 90, 1),
                "player_sot_per90": (s.shots or 0) * 0.4 / max((s.minutes or 0) / 90, 1),
                "minutes_played": s.minutes or 0,
            }
            for s in rows
        ]
    )

    preds = model.predict(features)

    predictions = []
    for s, pred in zip(rows, preds):
        probability = pred["probability"]
        market_odds = 2.0
        fair_odds = pred["fair_odds"]
        if probability <= 0 or not math.isfinite(fair_odds):
            continue
        ev = (probability * market_odds) - 1
        if ev >= min_ev:
            predictions.append(
                {
                    "player": s.player_id,
                    "player_name": (
                        db.query(Player).get(s.player_id).name
                        if db.query(Player).get(s.player_id)
                        else None
                    ),
                    "probability": round(pred["probability"], 4),
                    "fair_odds": round(fair_odds, 4),
                    "market_odds": market_odds,
                    "ev": round(ev, 4),
                }
            )

    return {"predictions": predictions}
