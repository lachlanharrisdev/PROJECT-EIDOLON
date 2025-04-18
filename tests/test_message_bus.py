import pytest
from unittest.mock import Mock, patch

from core.modules.util.messagebus import MessageBus
from core.modules.models import ModuleInput, ModuleOutput
from core.modules.engine.engine_contract import ModuleCore


def test_message_bus_unsubscribed_topic():
    bus = MessageBus()

    # Now MessageBus logs a warning instead of raising an exception for unsubscribed topics
    with patch.object(bus._logger, "warning") as mock_warning:
        bus.publish("unsubscribed_topic", "No subscribers here")
        mock_warning.assert_called_once()
        # Verify the warning message contains the topic name
        assert "unsubscribed_topic" in mock_warning.call_args[0][0]


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


def test_message_bus_type_validation():
    bus = MessageBus()

    # Mock subscribers
    results = []

    def subscriber(data):
        results.append(data)

    # Subscribe with type validation
    bus.subscribe("typed_topic", subscriber, expected_type=str)

    # Test valid type
    bus.publish("typed_topic", "Valid string")

    # Test invalid type with patched logger to capture error
    with patch.object(bus._logger, "error") as mock_error:
        bus.publish("typed_topic", 123)  # Should log error and not call subscriber
        mock_error.assert_called_once()

    # Only the valid message should be in results
    assert results == ["Valid string"]


def test_message_bus_register_input_output():
    bus = MessageBus()

    # Create ModuleOutput and register it - use a type that won't be lowercased to 'int'
    output_def = ModuleOutput(
        name="test_output", type_name="dict", description="Test output"
    )
    bus.register_output("test_output", output_def, "source_module")

    # Create ModuleInput and register it (with matching type)
    input_def = ModuleInput(
        name="test_input", type_name="dict", description="Test input"
    )
    bus.register_input("test_output", input_def, "target_module")

    # Verify type registration
    assert "test_output" in bus.output_types
    assert bus.topic_sources["test_output"] == "source_module"

    # Test type mismatch warning - ensure we use a type that remains distinct after lowercasing
    mismatched_input = ModuleInput(
        name="mismatched", type_name="int", description="Test mismatch"
    )
    with patch.object(bus._logger, "warning") as mock_warning:
        bus.register_input("test_output", mismatched_input, "another_module")
        mock_warning.assert_called_once()
        # Verify warning message contains type mismatch info
        warning_msg = mock_warning.call_args[0][0]
        assert "Type mismatch" in warning_msg


# Move ModuleUseCase tests to a separate test file to avoid circular imports
class MockModule(ModuleCore):
    def __init__(self, logger):
        super().__init__(logger)

    def run(self, message_bus):
        pass


def test_module_core():
    """Test basic ModuleCore functionality"""
    logger = Mock()
    module = MockModule(logger)

    # Test that the module can be initialized
    assert isinstance(module, ModuleCore)
