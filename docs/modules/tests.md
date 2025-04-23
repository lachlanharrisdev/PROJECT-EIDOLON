# Testing Modules

This document provides guidelines and best practices for testing modules in Project Eidolon, including examples of different testing approaches and common test scenarios.

## Testing Philosophy

Effective testing is crucial for maintaining a reliable modular system. In Project Eidolon:

- Each module should have its own suite of tests
- Tests should verify both individual functions and integration with the message bus
- Mocks should be used to isolate modules during testing
- Coverage should focus on core module functionality

## Test Directory Structure

Tests for a module should be organized in the `tests` directory within the module:

```
your_module/
├── __init__.py
├── main.py
├── module.yaml
└── tests/
    ├── __init__.py
    ├── test_basic.py      
    ├── test_integration.py
    └── test_edge_cases.py
```

## Test Types

### Unit Tests

Unit tests verify that individual functions or methods work correctly in isolation.

```python
# test_basic.py
import pytest
from unittest.mock import Mock
from ..main import YourModule

def test_process_data():
    logger = Mock()
    module = YourModule(logger)
    
    test_input = {"key1": "value1", "key2": "value2"}
    module.input_data = test_input
    
    results = module._process_data()
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert "processed_key1" in results[0]
```

### Integration Tests

Integration tests verify that the module works correctly with the message bus and other components.

```python
# test_integration.py
import pytest
from unittest.mock import Mock, patch
from core.modules.util.messagebus import MessageBus, CourierEnvelope
from ..main import YourModule

@pytest.mark.asyncio
async def test_message_bus_publishing():
    logger = Mock()
    module = YourModule(logger)
    messagebus = Mock(spec=MessageBus)
    messagebus.publish = Mock() # Mock the publish method directly for async check

    module.input_data = {"test": "data"} # Assuming _process_data uses this
    await module.execute(messagebus) # Use execute for async operation

    messagebus.publish.assert_called_once()
    args = messagebus.publish.call_args[0]
    assert args[0] == "processed_results" # Assuming this is the output topic
    assert isinstance(args[1], list)
```

### Behavioral Tests

Behavioral tests verify that the module behaves correctly in response to different inputs and situations.

```python
# test_edge_cases.py
import pytest
from unittest.mock import Mock
from core.modules.util.messagebus import CourierEnvelope
from ..main import YourModule

def test_empty_input_handling():
    logger = Mock()
    module = YourModule(logger)
    envelope = CourierEnvelope(data={}, topic="input_topic")

    module.process(envelope) # Pass envelope to process
    assert module.input_data == {} # Check internal state

def test_invalid_input_handling():
    logger = Mock()
    module = YourModule(logger)
    envelope = CourierEnvelope(data="not_a_dict", topic="input_topic")

    module.process(envelope) # Pass envelope to process
    logger.warning.assert_called_once()
```

## Using pytest Fixtures

Pytest fixtures can help set up common test environments:

```python
# conftest.py (in tests directory)
import pytest
from unittest.mock import Mock
from ..main import YourModule
from core.modules.util.messagebus import MessageBus, CourierEnvelope # Import CourierEnvelope

@pytest.fixture
def mock_logger():
    return Mock()

@pytest.fixture
def test_module(mock_logger):
    module = YourModule(mock_logger)
    # Perform any necessary initialization based on _initialize_module
    module._initialize_module()
    return module

@pytest.fixture
def mock_messagebus():
    # Mock the async publish method if needed
    bus = Mock(spec=MessageBus)
    bus.publish = Mock()
    return bus

@pytest.fixture
def sample_data():
    return {
        "text": "Sample political article about democracy",
        "source": "test_source",
        "timestamp": "2025-01-01T12:00:00Z"
    }

@pytest.fixture
def sample_envelope(sample_data):
    # Fixture for creating a sample envelope
    return CourierEnvelope(
        data=sample_data,
        topic="input_topic",
        source_module="test_source_module"
    )
```

Using these fixtures in tests:

```python
@pytest.mark.asyncio
async def test_message_publishing(test_module, mock_messagebus, sample_envelope):
    # Use process to set input data via envelope
    test_module.process(sample_envelope)

    # Call execute to trigger processing and publishing
    await test_module.execute(mock_messagebus)

    mock_messagebus.publish.assert_called_once()
    # Add more specific assertions about the published data if needed
    args = mock_messagebus.publish.call_args[0]
    assert args[0] == test_module.default_output_topic() # Check against default topic
    # assert args[1] == expected_output_data
```

## Mocking External Dependencies

For modules that interact with external services, mock the external dependencies:

```python
def test_api_client(test_module):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": ["keyword1", "keyword2"]}
    
    with patch("requests.get", return_value=mock_response):
        results = test_module._fetch_api_data("test-endpoint")
        
        assert len(results) == 2
        assert "keyword1" in results
```

## Testing Input/Output Types

Test that the module correctly handles its defined input and output types via the `process` method.

```python
def test_type_handling(test_module):
    # Test handling list input via envelope
    list_envelope = CourierEnvelope(data=["keyword1", "keyword2"], topic="input_topic")
    test_module.process(list_envelope)
    # Assert based on how your process method handles list data
    # Example: assert test_module.keywords == ["keyword1", "keyword2"]

    # Test handling tuple input (should likely be rejected or handled specifically)
    tuple_envelope = CourierEnvelope(data=("keyword3", "keyword4"), topic="input_topic")
    test_module.process(tuple_envelope)
    # Assert based on expected behavior for non-list sequence
    # Example: assert test_module.keywords == ["keyword1", "keyword2"] # Assuming it ignores tuple
    # Or assert logger.warning.called if it logs a warning
```

## Testing Error Conditions

Test how your module handles errors and edge cases within its processing logic, often triggered via `execute`.

```python
@pytest.mark.asyncio
async def test_error_handling(test_module, mock_logger, mock_messagebus, sample_envelope):
    test_module.process(sample_envelope) # Set up input data

    # Patch the internal processing method to raise an error
    with patch.object(test_module, '_process_data', side_effect=ValueError("Test error")):
        await test_module.execute(mock_messagebus) # Run the execute cycle

        mock_logger.error.assert_called_once()
        # Check that publish was NOT called, or an error topic was published to
        mock_messagebus.publish.assert_not_called()
```

## Testing Module Commands

Test the `invoke` method with different command characters:

```python
def test_module_commands(test_module):
    device = test_module.invoke("S")
    assert device.name == test_module.meta.name
    assert device.errors == []
    
    test_module.input_data = {"test": "data"}
    device = test_module.invoke("R")
    assert test_module.input_data == {}
```

## Testing Shutdown Logic

Test that the module's `cleanup` method (or `_after_run`) works correctly.

```python
@pytest.mark.asyncio
async def test_shutdown_cleanup(test_module):
    # Setup any resources that cleanup should handle
    test_module.connection = Mock()
    test_module.connection.close = Mock(return_value=None) # Mock async close if needed

    # Call the cleanup method directly
    await test_module.cleanup()

    test_module.connection.close.assert_called_once()
```

## Integration Testing with Pipeline

Test the module as part of a pipeline:

```python
def test_module_in_pipeline():
    from core.modules.engine.engine_core import ModuleEngine
    
    engine = ModuleEngine(options={"log_level": "DEBUG"}, pipeline="test_pipeline")
    engine.start()
    
    your_module = next(
        (m for m in engine.use_case.modules if m.meta.name == "your_module"), 
        None
    )
    
    assert your_module is not None
    assert "input_data" in [topic for topic in engine.message_bus.subscribers.keys()]
```

## Running Tests

Run your module's tests with pytest:

```bash
# Run all tests for your module
pytest src/modules/your_module/tests/

# Run specific test file
pytest src/modules/your_module/tests/test_basic.py

# Run with coverage report
pytest --cov=src.modules.your_module src/modules/your_module/tests/
```

## Continuous Integration

To integrate your tests with a CI pipeline:

1. Add your tests to the module's test directory
2. Make sure the tests are listed in `module.yaml` under `runtime.tests`
3. The test runner will automatically find and execute your tests

```yaml
# module.yaml
runtime:
  main: 'main.py'
  tests:
    - 'tests/test_basic.py'
    - 'tests/test_integration.py'
    - 'tests/test_edge_cases.py'
```

## Test Doubles

Use different types of test doubles for different testing scenarios:

1. **Stubs**: Simple replacements with canned answers
2. **Spies**: Record calls, but don't change behavior
3. **Mocks**: Pre-programmed replacements with expectations
4. **Fake**: Working implementations with shortcuts

```python
# Using a stub
stub_data_provider = Mock()
stub_data_provider.get_data.return_value = ["test1", "test2"]

# Using a spy
spy_logger = Mock()
module._logger = spy_logger
module.process_data()
assert spy_logger.info.called

# Using a mock with expectations
mock_validator = Mock()
mock_validator.validate.return_value = True
module.validator = mock_validator
module.process_data()
mock_validator.validate.assert_called_once()

# Using a fake
class FakeMessageBus:
    def __init__(self):
        self.messages = {}
        self.subscribers = {} # Add subscribers dict

    async def publish(self, topic, data): # Make publish async
        # Wrap data in an envelope like the real bus
        envelope = CourierEnvelope(
            data=data,
            topic=topic,
            source_module="fake_publisher" # Simulate source
        )
        self.messages[topic] = envelope
        # Simulate delivery to subscribers
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                callback(envelope) # Call subscriber callback

    def subscribe(self, topic, callback, expected_type):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)

@pytest.mark.asyncio
async def test_with_fake_bus(test_module):
    fake_bus = FakeMessageBus()
    test_module.process(CourierEnvelope(data={"key": "value"}, topic="input")) # Provide input

    await test_module.execute(fake_bus) # Run execute

    assert test_module.default_output_topic() in fake_bus.messages
    # assert fake_bus.messages[test_module.default_output_topic()].data == expected_output
```

## Best Practices

1. **Isolate tests**: Each test should run independently
2. **Clear naming**: Test names should describe what they're testing
3. **Arrange-Act-Assert**: Structure tests with setup, action, and verification phases
4. **Test one thing**: Each test should verify a single aspect of behavior
5. **Test edge cases**: Include tests for boundary conditions and error scenarios
6. **Keep tests fast**: Avoid slow operations in unit tests
7. **Don't test private methods directly**: Test through public interfaces
8. **Mock external dependencies**: Don't rely on external systems in unit tests

## Example Test Scenarios for OSINT Modules

Here are some common test scenarios for OSINT modules:

### Data Collection Module

```python
def test_url_parser():
    """Test URL parsing functionality"""
    parser = URLParser()
    valid_url = "https://example.com/news/article.html?id=123"
    result = parser.parse(valid_url)
    
    assert result.domain == "example.com"
    assert result.path == "/news/article.html"
    assert result.query == {"id": "123"}

def test_rate_limiting():
    """Test that the crawler respects rate limiting"""
    crawler = WebCrawler(rate_limit=2)  # 2 requests per second
    start_time = time.time()
    
    crawler.fetch("https://example.com/page1")
    crawler.fetch("https://example.com/page2")
    crawler.fetch("https://example.com/page3")
    
    elapsed = time.time() - start_time
    assert elapsed >= 1.0  # Should take at least 1 second for 3 requests
```

### Data Analysis Module

```python
def test_entity_extraction():
    """Test extraction of entities from text"""
    analyzer = EntityAnalyzer()
    text = "John Smith works at Acme Corporation in New York City."
    
    entities = analyzer.extract_entities(text)
    
    assert {"text": "John Smith", "type": "PERSON"} in entities
    assert {"text": "Acme Corporation", "type": "ORG"} in entities
    assert {"text": "New York City", "type": "LOC"} in entities

def test_language_detection():
    """Test language detection functionality"""
    detector = LanguageDetector()
    
    assert detector.detect("Hello world") == "en"
    assert detector.detect("Hola mundo") == "es"
    assert detector.detect("Bonjour le monde") == "fr"
```

### Visualization Module

```python
def test_chart_generation():
    """Test chart data generation"""
    visualizer = DataVisualizer()
    data = [
        {"date": "2025-01-01", "value": 10},
        {"date": "2025-01-02", "value": 15},
        {"date": "2025-01-03", "value": 7}
    ]
    
    chart_data = visualizer.generate_chart(data, "line")
    
    assert "datasets" in chart_data
    assert len(chart_data["labels"]) == 3
    assert chart_data["type"] == "line"

def test_geospatial_mapping():
    """Test geospatial data mapping"""
    mapper = GeoMapper()
    locations = [
        {"name": "New York", "lat": 40.7128, "lon": -74.0060},
        {"name": "London", "lat": 51.5074, "lon": -0.1278}
    ]
    
    map_data = mapper.generate_map(locations)
    
    assert len(map_data["features"]) == 2
    assert map_data["features"][0]["properties"]["name"] == "New York"
```

### Communication Module

```python
def test_alert_formatting():
    """Test alert message formatting"""
    alerter = AlertManager()
    alert_data = {
        "severity": "high",
        "source": "web_monitor",
        "message": "Security incident detected",
        "timestamp": "2025-04-21T16:35:40"
    }
    
    formatted = alerter.format_alert(alert_data)
    
    assert "[HIGH]" in formatted
    assert "2025-04-21" in formatted
    assert "Security incident detected" in formatted

def test_throttling():
    """Test alert throttling functionality"""
    alerter = AlertManager(throttle_period=60)  # 60 second throttle
    
    # First alert should go through
    assert alerter.should_send("test_alert") == True
    
    # Second alert should be throttled
    assert alerter.should_send("test_alert") == False
```

These examples demonstrate how to test specific OSINT module functionalities in isolation, ensuring each component performs as expected.

---

For more information on module methods to test, see the [module methods documentation](methods.md).

For verifying module security and validation, see the [verification documentation](verification.md).