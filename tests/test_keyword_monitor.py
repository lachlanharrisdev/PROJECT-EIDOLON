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
    monitor = KeywordMonitor()
    stats = monitor.get_keyword_stats()
    assert stats == {
        "keyword1": {"type": "ORG", "mentions": 5, "last_seen": "2025-04-15T08:02:30.996075"},
        "keyword2": {"type": "PERSON", "mentions": 3, "last_seen": "2025-04-15T08:02:30.996075"},
    }
    mock_keyword_monitor.get_keyword_stats.assert_called_once()


def test_rss_connection_success():
    """
    Test that test_rss_connection succeeds for a valid RSS URL.
    """
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        from tests.test_keyword_monitor import test_rss_connection
        assert test_rss_connection("https://news.google.com/rss/search?q=politics") is True


def test_rss_connection_failure():
    """
    Test that test_rss_connection fails for an invalid RSS URL.
    """
    with patch("requests.get", side_effect=Exception("Connection error")):
        from tests.test_keyword_monitor import test_rss_connection
        assert test_rss_connection("https://invalid-url.com/rss") is False