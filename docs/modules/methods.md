# Message Bus and Module Methods

This document explains the message bus system in Project Eidolon and the key methods that modules can implement to communicate effectively with each other.

## Message Bus Overview

The Eidolon message bus is a publish-subscribe system that enables modules to exchange data without directly referencing each other, creating a loosely coupled architecture.

### Key Concepts

1. **Topics**: Named channels for specific types of data
2. **Publishers**: Modules that send data to topics
3. **Subscribers**: Modules that receive data from topics
4. **Type Safety**: Automatic validation of data types during communication

### How It Works

```
┌────────────┐          ┌──────────────┐          ┌────────────┐
│  Module A  │          │ Message Bus  │          │  Module B  │
│            │ publish  │              │ deliver  │            │
│ (Publisher)├─────────►│   "topic"    ├─────────►│(Subscriber)│
│            │          │              │          │            │
└────────────┘          └──────────────┘          └────────────┘
```

1. Module A publishes data to a named topic
2. The message bus validates the data matches the expected type
3. The message bus delivers the data to all modules subscribed to that topic
4. Each subscriber processes the data according to its own logic

## ModuleCore Architecture

The ModuleCore class provides common functionality for all modules, greatly reducing the amount of boilerplate code needed when creating a new module:

- **Automatic Meta Initialization**: Loads metadata from module.yaml
- **Standard Lifecycle Management**: Handles loop management, errors, and graceful cancellation
- **Error Handling**: Built-in error boundaries and recovery
- **Input Processing**: Standard input handling with validation
- **Command Processing**: Standard command handlers with extensibility
- **Shutdown Coordination**: Proper resource cleanup

## Module Hook Methods

When implementing a module, you typically only need to override a handful of hook methods to customize behavior. Here are the key hook methods you can override:

### `_initialize_module(self) -> None`

Override this method to initialize module-specific state. This is called after the base ModuleCore initialization.

```python
def _initialize_module(self) -> None:
    self.keywords = []
    self.processed_results = {}
    self.custom_settings = {}
```

### `process(self, data: Any) -> None`

Override this method to handle data delivered to your module from subscribed topics.

```python
def process(self, data: Any) -> None:
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        self.keywords = data
        self._logger.info(f"Received {len(data)} keywords")
    elif isinstance(data, dict) and "config" in data:
        self.custom_settings.update(data["config"])
    else:
        self._logger.warning(f"Received unrecognized data: {type(data)}")
```

### `async execute(self, message_bus: MessageBus) -> None`

Override this method to define the main logic that runs in each execution cycle.

```python
async def execute(self, message_bus: MessageBus) -> None:
    if self.keywords:
        results = self._process_keywords()
        if results:
            await message_bus.publish("processed_keywords", results)
```

### `_process_data(self) -> Any`

Override this method to define how your module processes its current input data.

```python
def _process_data(self) -> Dict[str, Any]:
    results = {}
    for keyword in self.keywords:
        # Process each keyword
        score = self._calculate_score(keyword)
        results[keyword] = score
    return results
```

### `cycle_time(self) -> float`

Override this method to customize how frequently your module's run iteration executes.

```python
def cycle_time(self) -> float:
    return 30.0  # Run every 30 seconds
```

### `default_output_topic(self) -> Optional[str]`

Override this method to specify the default output topic for your module.

```python
def default_output_topic(self) -> str:
    return "processed_results"
```

### Asynchronous Lifecycle Hooks

ModuleCore provides additional asynchronous lifecycle hooks:

```python
async def _before_run(self, message_bus: MessageBus) -> None:
    """Setup code that runs once before the main module loop"""
    await self._connect_to_database()

async def _after_run(self, message_bus: MessageBus) -> None:
    """Cleanup code that runs once after the main module loop"""
    await self._close_connections()

async def cleanup(self):
    """Custom resource cleanup during shutdown"""
    await self._release_resources()
```

## Standard Module Commands

ModuleCore implements standard command handling with the following commands:

| Command | Description | Implementation |
|---------|-------------|----------------|
| `S` | Status | Returns the module's current status |
| `R` | Reset | Resets the module's state |
| `P` | Process | Process any pending data |

You can add custom commands by overriding `_handle_custom_command()`.

## Publishing Data

To publish data to the message bus from your module:

```python
async def execute(self, message_bus: MessageBus) -> None:
    keywords = ["democracy", "election", "politician"]
    await message_bus.publish("keywords", keywords)
    
    stats = {
        "processed": 120,
        "filtered": 45,
        "keywords_found": len(keywords)
    }
    await message_bus.publish("statistics", stats)
```

## Type Validation

The message bus performs automatic type validation to ensure data integrity. For more details on type specifications, see the [module configuration documentation](config.md).

## Advanced Patterns

## Multithreading

Multithreading can be as complex as you require it to be. `ModuleCore` provides a threadpool by default, where you can add tasks to it with the following:

``` py
result = await self.run_blocking(example_function, args...)
```

``` py
async def run_blocking(self, function, *args, **kwargs) -> Any:
    """
    Run a blocking function in the thread pool.

    Args:
        function: The blocking function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the blocking function
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(self.thread_pool, function, *args, **kwargs)
```

### Request-Response Pattern

While the message bus handles the majority of communication between modules, some more advanced communication patterns are possible.

For scenarios where modules need to request data from other modules (rather than relying on the dependent module to choose when to publish data):

```python
# Module A: Makes a request
async def execute(self, message_bus: MessageBus) -> None:
    request_id = str(uuid.uuid4())
    request = {
        "id": request_id,
        "type": "data_request",
        "parameters": {"date_range": "last_week"}
    }
    
    self.pending_requests.add(request_id)
    await message_bus.publish("data_requests", request)

# Module A: Handle the response
def process(self, data: Any) -> None:
    if isinstance(data, dict) and "response_to" in data:
        request_id = data["response_to"]
        if request_id in self.pending_requests:
            self._process_response(data["content"])
            self.pending_requests.remove(request_id)
```

```python
# Module B: Responds to requests
def process(self, data: Any) -> None:
    if isinstance(data, dict) and data.get("type") == "data_request":
        request_id = data["id"]
        content = self._get_requested_data(data["parameters"])
        self.pending_responses.append({
            "response_to": request_id,
            "content": content
        })

async def execute(self, message_bus: MessageBus) -> None:
    for response in self.pending_responses:
        await message_bus.publish("data_responses", response)
    
    self.pending_responses = []
```

### Event Broadcasting

For system-wide events that many modules might be interested in:

```python
# Broadcasting an event
async def execute(self, message_bus: MessageBus) -> None:
    event = {
        "type": "system_event",
        "name": "configuration_changed",
        "timestamp": datetime.now().isoformat(),
        "details": {"changed_parameters": ["api_key"]}
    }
    
    await message_bus.publish("system_events", event)
```

```python
# Handling events
def process(self, data: Any) -> None:
    if isinstance(data, dict) and data.get("type") == "system_event":
        event_name = data.get("name")
        
        if event_name == "configuration_changed":
            changed_params = data.get("details", {}).get("changed_parameters", [])
            if any(param in self.watched_parameters for param in changed_params):
                self._reload_configuration()
```

---

For module verification and security, see the [verification documentation](verification.md).

For testing message bus interactions, see the [testing documentation](tests.md).