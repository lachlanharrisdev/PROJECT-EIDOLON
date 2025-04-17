import os
import pytest
from unittest.mock import patch, mock_open
from core.modules.engine import ModuleEngine
import json


def test_verified_modules_structure():
    """Ensure verified_modules.json has the correct structure."""
    mock_verified_modules = {
        "modules": {
            "hello_world": {
                "version": "1.0.0",
                "hash": "f1c2eae8b85a...",
                "signature": "3a7e6c...",
                "repo": "https://github.com/eidolon-mods/hello_world",
            }
        }
    }

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_verified_modules))):
        with open("verified_modules.json", "r") as f:
            data = json.load(f)

        assert "modules" in data, "verified_modules.json is missing the 'modules' key"
        assert "hello_world" in data["modules"], "Module 'hello_world' is missing"
        module_data = data["modules"]["hello_world"]
        assert "version" in module_data, "Module is missing 'version'"
        assert "hash" in module_data, "Module is missing 'hash'"
        assert "signature" in module_data, "Module is missing 'signature'"
        assert "repo" in module_data, "Module is missing 'repo'"


def test_module_discovery():
    engine = ModuleEngine(options={"log_level": "DEBUG"})
    engine.start()
    assert len(engine.use_case.modules) > 0  # Ensure modules are discovered
