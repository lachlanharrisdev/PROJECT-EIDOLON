import pytest
from unittest.mock import Mock

from core.modules.engine.engine_core import MessageBus
from core.modules.usecase.interactors import ModuleUseCase
from core.modules.engine.engine_contract import ModuleCore


def test_message_bus_unsubscribed_topic():
    bus = MessageBus()

    # Attempt to publish to an unsubscribed topic
    with pytest.raises(ValueError):
        bus.publish("unsubscribed_topic", "No subscribers here")


def test_message_bus_duplicate_subscriptions():
    bus = MessageBus()

    # Mock subscribers
    results = []

    def subscriber(data):
        results.append(data)

    # Subscribe the same subscriber multiple times
    bus.subscribe("test_topic", subscriber, expected_type=str)
    bus.subscribe("test_topic", subscriber, expected_type=str)

    bus.publish("test_topic", "Hello, World!")

    # Ensure the subscriber is called twice
    assert results == ["Hello, World!", "Hello, World!"]


def test_message_bus_no_expected_type():
    bus = MessageBus()

    # Mock subscribers
    results = []

    def subscriber(data):
        results.append(data)

    # Subscribe without specifying an expected type
    bus.subscribe("test_topic", subscriber)

    # Publish data of any type
    bus.publish("test_topic", 123)
    bus.publish("test_topic", "Hello")

    assert results == [123, "Hello"]


def test_module_usecase_discover_modules_empty_directory(mocker):
    # Mock the FileSystem and os.listdir to simulate an empty directory
    mocker.patch(
        "core.modules.util.FileSystem.get_modules_directory",
        return_value="mock_directory",
    )
    mocker.patch("os.listdir", return_value=[])

    use_case = ModuleUseCase({"log_level": "DEBUG", "directory": "mock_directory"})
    use_case.discover_modules(reload=True)

    # Ensure no modules are discovered
    assert len(use_case.modules) == 0


def test_module_usecase_discover_modules_invalid_module(mocker):
    # Mock the FileSystem and os.listdir to simulate a directory with invalid modules
    mocker.patch(
        "core.modules.util.FileSystem.get_modules_directory",
        return_value="mock_directory",
    )
    mocker.patch("os.listdir", return_value=["invalid_module"])

    use_case = ModuleUseCase({"log_level": "DEBUG", "directory": "mock_directory"})
    use_case.discover_modules(reload=True)

    # Ensure no modules are added due to invalid module
    assert len(use_case.modules) == 0


def test_module_usecase_register_module():
    class MockModule(ModuleCore):
        def __init__(self, logger):
            super().__init__(logger)

    logger = Mock()
    module = ModuleUseCase.register_module(MockModule, logger)

    # Ensure the module is registered correctly
    assert isinstance(module, MockModule)
