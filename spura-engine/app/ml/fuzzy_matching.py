from typing import List, Optional, Tuple

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.db.models import Player, Team


def parse_float(value) -> float | None:
    """Coerce a value (possibly a numeric string) to float, or None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class TeamMatcher:
    def __init__(self, db: Session, league_code: str):
        self.db = db
        self.league_code = league_code
        self.team_cache = {}
        self.player_cache = {}

    def _teams_for_league(self) -> List[Team]:
        return (
            self.db.query(Team)
            .filter(Team.league_code == self.league_code)
            .all()
        )

    def match_team(self, external_name: str) -> Tuple[Optional[int], float]:
        """Match external team name to database team."""
        if external_name in self.team_cache:
            return self.team_cache[external_name]

        teams = self._teams_for_league()
        if not teams:
            return None, 0.0

        names = [t.name for t in teams]
        best = process.extractOne(
            external_name, names, scorer=fuzz.token_sort_ratio
        )

        result = (None, 0.0)
        if best is not None:
            best_name, score = best[0], best[1]
            if score >= 65:
                team = next(t for t in teams if t.name == best_name)
                result = (team.id, float(score))

        self.team_cache[external_name] = result
        return result

    def match_player(self, player_name: str, team_id: int) -> Tuple[Optional[int], float]:
        """Match player name to database player within a team."""
        if player_name in self.player_cache:
            return self.player_cache[player_name]

        players = (
            self.db.query(Player).filter(Player.team_id == team_id).all()
        )
        result = (None, 0.0)
        if players:
            names = [p.name for p in players]
            best = process.extractOne(
                player_name, names, scorer=fuzz.token_sort_ratio
            )
            if best is not None and best[1] >= 65:
                player = next(p for p in players if p.name == best[0])
                result = (player.id, float(best[1]))

        self.player_cache[player_name] = result
        return result
