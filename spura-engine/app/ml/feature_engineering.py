import logging

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import PlayerSeasonStats

logger = logging.getLogger(__name__)


class FeatureEngineer:
    def __init__(self, db: Session, league_code: str):
        self.db = db
        self.league_code = league_code

    def prepare_training_data(self) -> pd.DataFrame:
        """Build a player-level training matrix for the league.

        Each row is a player-season, using the real player stats fetched
        from Understat (goals, xG, xA, shots, minutes).
        """
        rows = (
            self.db.query(PlayerSeasonStats)
            .filter(PlayerSeasonStats.league_code == self.league_code)
            .all()
        )
        if not rows:
            logger.warning("No player stats found for league %s", self.league_code)
            return self._empty_frame()

        records = []
        for s in rows:
            minutes = s.minutes or 0
            m90 = minutes / 90.0
            total_xg = s.xg or 0.0
            shots = s.shots or 0

            # Season-level xG (per 90) used as the feature input.
            xg_per90 = total_xg / m90 if m90 > 0 else 0.0
            shots_per90 = shots / m90 if m90 > 0 else 0.0
            # Approximate shots-on-target per 90 (Understat provides shots only).
            sot_per90 = shots_per90 * 0.38
            # A penalty taker typically has an xG share much higher than
            # their shots would suggest; use xG/game relative to shots/game.
            is_penalty_taker = 1 if (xg_per90 > 0.3 and total_xg >= 3) else 0

            records.append(
                {
                    "player_id": s.player_id,
                    "rolling_xg_5": xg_per90,
                    "rolling_xg_10": xg_per90,
                    "rolling_xg_20": xg_per90,
                    "opp_defense_rating": 1.2,
                    "is_home": 1,
                    "is_penalty_taker": is_penalty_taker,
                    "match_expected_goals": xg_per90 * 1.1,
                    "player_shots_per90": shots_per90,
                    "player_sot_per90": sot_per90,
                    "minutes_played": minutes,
                    "goal_scored": 1 if (s.goals or 0) > 0 else 0,
                }
            )

        df = pd.DataFrame(records)
        logger.info("Player-level training data built: %s rows", len(df))
        return df

    def _empty_frame(self) -> pd.DataFrame:
        cols = [
            "player_id",
            "rolling_xg_5",
            "rolling_xg_10",
            "rolling_xg_20",
            "opp_defense_rating",
            "is_home",
            "is_penalty_taker",
            "match_expected_goals",
            "player_shots_per90",
            "player_sot_per90",
            "minutes_played",
            "goal_scored",
        ]
        return pd.DataFrame(columns=cols)
