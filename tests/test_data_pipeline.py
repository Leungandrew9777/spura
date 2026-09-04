# spura-engine/tests/test_data_pipeline.py
import pytest
from unittest.mock import patch, MagicMock
from ml.data_pipeline import LeagueDataPipeline

@pytest.fixture
def mock_db():
    return MagicMock()

def test_csv_parsing(mock_db):
    """Test CSV parsing functionality"""
    pipeline = LeagueDataPipeline(mock_db, 'EPL')
    
    # Mock CSV data
    mock_csv_data = [{
        'Date': '2023-08-12',
        'HomeTeam': 'Arsenal',
        'AwayTeam': 'Chelsea',
        'FTHG': 2,
        'FTAG': 1,
        'Referee': 'Michael Oliver',
        'Stadium': 'Emirates Stadium'
    }]
    
    with patch('pandas.read_csv') as mock_read_csv:
        mock_read_csv.return_value = mock_csv_data
        result = pipeline._parse_match_row(mock_csv_data[0])
        
        assert result['home_team'] == 'Arsenal'
        assert result['away_team'] == 'Chelsea'
        assert result['home_goals'] == 2
        assert result['away_goals'] == 1

def test_fuzzy_matching():
    """Test fuzzy team matching"""
    from ml.fuzzy_matching import TeamMatcher
    
    matcher = TeamMatcher()
    
    # Test exact match
    team_id, score = matcher.match_team('Arsenal', 'EPL')
    assert team_id is not None
    assert score > 0.9
    
    # Test partial match
    team_id, score = matcher.match_team('Man Utd', 'EPL')
    assert team_id is not None
    assert score > 0.7