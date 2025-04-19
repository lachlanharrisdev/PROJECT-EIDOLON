# Message Bus and Module Methods

This document explains the message bus system in Project Eidolon and the key methods that modules must implement to communicate effectively with each other.

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

## Required Module Methods

Every module must implement the following methods to interact with the message bus system. For a complete implementation example, see [Creating a Module](2-creating-a-module.md).

### `handle_input(self, data)`

This method is called when data is delivered to your module from a topic it has subscribed to.

```python
def handle_input(self, data: Any) -> None:
    if isinstance(data, list) and all(isinstance(item, str) for item in data):
        self._process_keywords(data)
    elif isinstance(data, dict) and "config" in data:
        self._update_config(data["config"])
    else:
        self._logger.warning(f"Received unrecognized data: {type(data)}")
```

### `run(self, messagebus: MessageBus) -> None`

This method is called by the module engine to execute the module's main logic and publish results.

```python
def run(self, messagebus: MessageBus) -> None:
    self._logger.info(f"Running {self.meta.name}")
    
    if self.input_data:
        results = self._analyze_data(self.input_data)
        
        if results:
            messagebus.publish("analysis_results", results)
```

### `invoke(self, command: chr) -> Device`

This method handles commands sent from the module engine and returns a Device object with status information.

```python
def invoke(self, command: chr) -> Device:
    if command == "S":
        self._logger.info("Status check")
    elif command == "R":
        self.input_data = None
        self.results = []
    elif command == "P":
        self._process_data()
    
    return Device(
        name=self.meta.name,
        firmware=0x10001,
        protocol="STATUS", 
        errors=[]
    )
```

### `shutdown(self) -> None`

This method is called when the module is being shut down and should clean up any resources.

```python
async def shutdown(self):
    self._logger.info(f"Shutting down {self.meta.name}")
    
    if hasattr(self, "connection") and self.connection:
        await self.connection.close()
```

## Publishing Data

To publish data to the message bus, use the `publish` method of the MessageBus object:

```python
def run(self, messagebus: MessageBus) -> None:
    keywords = ["democracy", "election", "politician"]
    messagebus.publish("keywords", keywords)
    
    stats = {
        "processed": 120,
        "filtered": 45,
        "keywords_found": len(keywords)
    }
    messagebus.publish("statistics", stats)
```

## Type Validation

The message bus performs automatic type validation to ensure data integrity. For more details on type specifications, see the [module configuration documentation](config.md).

## Advanced Patterns

### Request-Response Pattern

While the message bus handles the majority of communication between modules, some more advanced communication patterns are possible.

For scenarios where modules need to request data from other modules (rather than relying on the dependent module to choose when to publish data):

```python
# Module A: Makes a request
def run(self, messagebus: MessageBus) -> None:
    request_id = str(uuid.uuid4())
    request = {
        "id": request_id,
        "type": "data_request",
        "parameters": {"date_range": "last_week"}
    }
    
    self.pending_requests.add(request_id)
    messagebus.publish("data_requests", request)

# Module A: Handle the response
def handle_input(self, data: Any) -> None:
    if isinstance(data, dict) and "response_to" in data:
        request_id = data["response_to"]
        if request_id in self.pending_requests:
            self._process_response(data["content"])
            self.pending_requests.remove(request_id)
```

```python
# Module B: Responds to requests
def handle_input(self, data: Any) -> None:
    if isinstance(data, dict) and data.get("type") == "data_request":
        request_id = data["id"]
        content = self._get_requested_data(data["parameters"])
        self.pending_responses.append({
            "response_to": request_id,
            "content": content
        })

def run(self, messagebus: MessageBus) -> None:
    for response in self.pending_responses:
        messagebus.publish("data_responses", response)
    
    self.pending_responses = []
```

### Event Broadcasting

For system-wide events that many modules might be interested in:

```python
# Broadcasting an event
def run(self, messagebus: MessageBus) -> None:
    event = {
        "type": "system_event",
        "name": "configuration_changed",
        "timestamp": datetime.now().isoformat(),
        "details": {"changed_parameters": ["api_key"]}
    }
    
    messagebus.publish("system_events", event)
```

```python
# Handling events
def handle_input(self, data: Any) -> None:
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