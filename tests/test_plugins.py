import pytest
from core.plugins.engine import PluginEngine


def test_plugin_discovery():
    engine = PluginEngine(options={"log_level": "DEBUG"})
    engine.start()
    assert len(engine.use_case.modules) > 0  # Ensure plugins are discovered
