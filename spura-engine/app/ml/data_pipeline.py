import json
import logging
import os

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Competition, Match, Player, PlayerSeasonStats, Team
from app.ml.fuzzy_matching import TeamMatcher, parse_float
from app.ml.understat_client import UnderstatClient

logger = logging.getLogger(__name__)

FOOTBALL_DATA_BASE_URL = settings.FOOTBALL_DATA_BASE_URL


def season_to_fd_code(season: str) -> str:
    """Convert '2023-24' format to football-data.co.uk '2324' format."""
    season = str(season)
    if "-" in season:
        start, end = season.split("-")
        return f"{start[-2:]}{end[-2:]}"
    if "/" in season:
        start, end = season.split("/")
        return f"{start[-2:]}{end[-2:]}"
    return season[-4:]


class LeagueDataPipeline:
    def __init__(self, db: Session, league_code: str):
        self.db = db
        self.league_code = league_code
        self.config = self._load_league_config()
        self.team_matcher = TeamMatcher(db, league_code)

    def _load_league_config(self) -> dict:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "leagues_config.json",
        )
        with open(config_path) as f:
            config = json.load(f)
        return config["leagues"][self.league_code]

    def _get_or_create_competition(self) -> Competition:
        competition = (
            self.db.query(Competition)
            .filter(Competition.code == self.league_code)
            .first()
        )
        if competition is None:
            competition = Competition(
                code=self.league_code,
                name=self.config["name"],
                country=None,
                is_european=False,
            )
            self.db.add(competition)
            self.db.flush()
        return competition

    async def sync_league_data(self, season: str) -> dict:
        """Sync all data for a specific league season."""
        results = {"matches_synced": 0, "player_stats_synced": 0, "errors": []}

        competition = self._get_or_create_competition()
        fd_season = season_to_fd_code(season)
        csv_url = self.config["csv_template"].format(
            season=fd_season, division=self.config["division"]
        )

        try:
            df = pd.read_csv(csv_url)
        except Exception as e:
            logger.exception("Failed to download CSV from %s", csv_url)
            results["errors"].append(f"Download failed: {e}")
            # Continue to player stats even if match CSV is unavailable.
        else:
            for _, row in df.iterrows():
                try:
                    self._save_match(row, competition, season)
                    results["matches_synced"] += 1
                except Exception as e:
                    logger.exception("Failed to sync match %s", row.to_dict())
                    results["errors"].append(f"Match sync failed: {e}")

        try:
            results["player_stats_synced"] = self._sync_player_stats(season, competition)
        except Exception as e:
            logger.exception("Failed to sync player stats")
            results["errors"].append(f"Player stats sync failed: {e}")

        self.db.commit()
        return results

    def _parse_match_row(self, row: pd.Series) -> dict:
        return {
            "date": pd.to_datetime(row["Date"]),
            "home_team": row["HomeTeam"],
            "away_team": row["AwayTeam"],
            "home_goals": row["FTHG"],
            "away_goals": row["FTAG"],
        }

    def _get_or_create_team(self, name: str, competition: Competition) -> Team:
        team = self.db.query(Team).filter(Team.name == name).first()
        if team is None:
            team = Team(
                name=name, league_code=self.league_code, country=competition.country
            )
            self.db.add(team)
            self.db.flush()
        return team

    def _save_match(self, row: pd.Series, competition: Competition, season: str) -> Match:
        data = self._parse_match_row(row)
        home_team = self._get_or_create_team(data["home_team"], competition)
        away_team = self._get_or_create_team(data["away_team"], competition)

        home_goals = int(data["home_goals"])
        away_goals = int(data["away_goals"])
        if home_goals > away_goals:
            result = "H"
        elif away_goals > home_goals:
            result = "A"
        else:
            result = "D"

        match = Match(
            competition_id=competition.id,
            season=season,
            match_date=data["date"],
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_goals=home_goals,
            away_goals=away_goals,
            result=result,
        )
        self.db.add(match)
        self.db.flush()
        return match

    def _sync_player_stats(self, season: str, competition: Competition) -> int:
        """Fetch player season stats from Understat and persist them."""
        understat_league = self.config.get("understat_league")
        if not understat_league:
            return 0

        client = UnderstatClient()
        try:
            players = client.get_league_players(understat_league, season)
        finally:
            client.close()

        count = 0
        for p in players:
            team_title = p.get("team_title")
            team = self._match_team_by_title(team_title)
            if team is None:
                continue

            player = self._upsert_player(p, team)
            self._upsert_season_stats(player, p, season)
            count += 1

        return count

    def _match_team_by_title(self, team_title: str) -> Team | None:
        if not team_title:
            return None
        team = self.db.query(Team).filter(Team.name == team_title).first()
        if team is not None:
            return team
        team_id, score = self.team_matcher.match_team(team_title)
        if team_id is not None:
            return self.db.query(Team).filter(Team.id == team_id).first()
        # Create the team if it is not present locally from the CSV data.
        team = Team(name=team_title, league_code=self.league_code)
        self.db.add(team)
        self.db.flush()
        return team

    def _upsert_player(self, p: dict, team: Team) -> Player:
        understat_id = parse_float(p.get("id"))
        player = None
        if understat_id is not None:
            player = (
                self.db.query(Player).filter(Player.understat_id == int(understat_id)).first()
            )
        if player is None:
            player = self.db.query(Player).filter(Player.name == p.get("player_name")).first()
        if player is None:
            player = Player(
                name=p.get("player_name"),
                team_id=team.id,
                position=p.get("position"),
                understat_id=int(understat_id) if understat_id is not None else None,
            )
            self.db.add(player)
        else:
            player.team_id = team.id
            player.position = p.get("position")
            player.understat_id = (
                int(understat_id) if understat_id is not None else player.understat_id
            )
        self.db.flush()
        return player

    def _upsert_season_stats(self, player: Player, p: dict, season: str) -> None:
        stats = (
            self.db.query(PlayerSeasonStats)
            .filter(
                PlayerSeasonStats.player_id == player.id,
                PlayerSeasonStats.league_code == self.league_code,
                PlayerSeasonStats.season == season,
            )
            .first()
        )
        if stats is None:
            stats = PlayerSeasonStats(
                player_id=player.id,
                league_code=self.league_code,
                season=season,
            )
            self.db.add(stats)
        stats.games = int(parse_float(p.get("games")) or 0)
        stats.minutes = int(parse_float(p.get("time")) or 0)
        stats.goals = int(parse_float(p.get("goals")) or 0)
        stats.assists = int(parse_float(p.get("assists")) or 0)
        stats.xg = parse_float(p.get("xG"))
        stats.xa = parse_float(p.get("xA"))
        stats.shots = int(parse_float(p.get("shots")) or 0)
        stats.key_passes = int(parse_float(p.get("key_passes")) or 0)
        stats.position = p.get("position")
        self.db.flush()
