import pytest
from core.modules.engine import ModuleEngine


def test_module_discovery():
    engine = ModuleEngine(options={"log_level": "DEBUG"})
    engine.start()
    assert len(engine.use_case.modules) > 0  # Ensure modules are discovered
