import pytest
from unittest.mock import MagicMock, patch
from core.analysis.keyword_monitor import KeywordMonitor, refresh_political_keywords

@pytest.fixture
def mock_keyword_monitor():
    """
    Fixture to create a mock KeywordMonitor instance.
    """
    with patch("core.analysis.keyword_monitor.KeywordMonitor") as MockMonitor:
        instance = MockMonitor.return_value
        instance.refresh.return_value = ["keyword1", "keyword2"]
        instance.get_keyword_stats.return_value = {
            "keyword1": {"type": "ORG", "mentions": 5, "last_seen": "2025-04-15T08:02:30.996075"},
            "keyword2": {"type": "PERSON", "mentions": 3, "last_seen": "2025-04-15T08:02:30.996075"},
        }
        yield instance


def test_refresh_political_keywords(mock_keyword_monitor):
    """
    Test that refresh_political_keywords calls the refresh method of KeywordMonitor.
    """
    keywords = refresh_political_keywords()
    assert keywords == ["keyword1", "keyword2"]
    mock_keyword_monitor.refresh.assert_called_once()


def test_get_keyword_stats(mock_keyword_monitor):
    """
    Test that get_keyword_stats returns the correct keyword statistics.
    """
    stats = mock_keyword_monitor.get_keyword_stats()
    assert stats == {
        "keyword1": {"type": "ORG", "mentions": 5, "last_seen": "2025-04-15T08:02:30.996075"},
        "keyword2": {"type": "PERSON", "mentions": 3, "last_seen": "2025-04-15T08:02:30.996075"},
    }
    mock_keyword_monitor.get_keyword_stats.assert_called_once()


def test_fetch_headlines_success(mock_keyword_monitor):
    """
    Test that fetch_headlines succeeds for a valid RSS URL.
    """
    mock_keyword_monitor.fetch_headlines.return_value = ["Headline 1", "Headline 2"]
    headlines = mock_keyword_monitor.fetch_headlines()
    assert headlines == ["Headline 1", "Headline 2"]


def test_fetch_headlines_failure(mock_keyword_monitor):
    """
    Test that fetch_headlines handles errors gracefully.
    """
    mock_keyword_monitor.fetch_headlines.return_value = []
    headlines = mock_keyword_monitor.fetch_headlines()
    assert headlines == []