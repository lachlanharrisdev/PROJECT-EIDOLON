import pytest
from unittest.mock import Mock, patch

from core.modules.util.messagebus import MessageBus
from core.modules.models import ModuleInput, ModuleOutput, CourierEnvelope
from core.modules.engine.engine_contract import ModuleCore


@pytest.mark.asyncio
async def test_message_bus_duplicate_subscriptions():
    bus = MessageBus()

    # Mock subscribers
    results = []

    def subscriber(envelope):
        # Extract data from the envelope
        results.append(envelope.data)

    # Subscribe the same subscriber multiple times
    bus.subscribe("test_topic", subscriber, expected_type=str)
    bus.subscribe("test_topic", subscriber, expected_type=str)

    await bus.publish("test_topic", "Hello, World!")

    # Ensure the subscriber is called twice
    assert results == ["Hello, World!", "Hello, World!"]


@pytest.mark.asyncio
async def test_message_bus_no_expected_type():
    bus = MessageBus()

    # Mock subscribers
    results = []

    def subscriber(envelope):
        # Extract data from the envelope
        results.append(envelope.data)

    # Subscribe without specifying an expected type
    bus.subscribe("test_topic", subscriber)

    # Publish data of any type
    await bus.publish("test_topic", 123)
    await bus.publish("test_topic", "Hello")

    assert results == [123, "Hello"]


# Create a simplified MockModule for testing that works with the enhanced ModuleCore
class MockModule(ModuleCore):
    def __init__(self, logger, thread_pool):
        super().__init__(logger, thread_pool)

    async def execute(self, message_bus):
        pass


def test_module_core():
    """Test basic ModuleCore functionality"""
    thread_pool = None
    logger = Mock()
    module = MockModule(logger, thread_pool)

    # Test that the module can be initialized
    assert isinstance(module, ModuleCore)
    assert hasattr(module, "meta")
    assert hasattr(module, "_shutdown_event")
