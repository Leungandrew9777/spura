# spura-engine/scripts/initial_sync.py
"""
Initial data sync for all supported leagues.
Run this once to populate the database with historical data.
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import get_db_session
from app.ml.data_pipeline import LeagueDataPipeline
from loguru import logger

async def sync_all_leagues():
    """Sync data for all configured leagues"""
    
    leagues = [
        {"code": "EPL", "season": "2023-24"},
        {"code": "SP1", "season": "2023-24"},
        {"code": "I1", "season": "2023-24"},
        {"code": "D1", "season": "2023-24"},
        {"code": "F1", "season": "2023-24"},
    ]
    
    db: Session = next(get_db_session())
    
    for league in leagues:
        logger.info(f"Starting sync for {league['code']} {league['season']}")
        
        try:
            pipeline = LeagueDataPipeline(db, league["code"])
            result = await pipeline.sync_league_data(league["season"])
            
            logger.success(
                f"✅ {league['code']} sync complete: "
                f"{result['matches_synced']} matches, "
                f"{result['player_stats_synced']} player stats"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to sync {league['code']}: {str(e)}")
            continue
    
    db.close()
    logger.info("🎉 Initial data sync complete!")

if __name__ == "__main__":
    asyncio.run(sync_all_leagues())