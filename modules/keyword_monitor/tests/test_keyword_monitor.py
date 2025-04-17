import pytest
import asyncio
from unittest.mock import Mock

from core.modules.util import LogUtil
from modules.keyword_monitor.main import KeywordMonitor


@pytest.fixture
def keyword_monitor():
    # Create a mock logger
    mock_logger = Mock(spec=LogUtil)
    return KeywordMonitor(logger=mock_logger)


def test_keyword_monitor_initialization(keyword_monitor):
    assert keyword_monitor is not None
    assert isinstance(keyword_monitor, KeywordMonitor)
