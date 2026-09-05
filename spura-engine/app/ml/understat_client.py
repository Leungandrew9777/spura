"""Client for fetching season-level player stats from Understat.

Understat does not provide an official API. League data is served by an
internal AJAX endpoint (`/getLeagueData/{league}/{season}`) which requires a
session cookie obtained by first visiting the corresponding league page.
"""

import logging

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

UNDERSTAT_BASE = settings.UNDERSTAT_API_URL

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def season_start_year(season: str) -> str:
    """Convert '2023-24'/'2023/2024' to Understat season year '2023'."""
    season = str(season)
    if "-" in season:
        return season.split("-")[0]
    if "/" in season:
        return season.split("/")[0]
    return season[-4:]


class UnderstatClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_league_players(self, league: str, season: str) -> list:
        """Return season player stats for a league.

        league: Understat league slug (e.g. 'EPL', 'La_Liga', 'Bundesliga').
        season: season string ('2023-24' or '2023').
        """
        year = season_start_year(season)
        page_url = f"{UNDERSTAT_BASE}/league/{league}/{year}"
        data_url = f"{UNDERSTAT_BASE}/getLeagueData/{league}/{year}"

        # First visit the page to obtain required session cookies.
        self.session.get(page_url, timeout=30)

        resp = self.session.get(data_url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("players", [])

    def close(self):
        self.session.close()
