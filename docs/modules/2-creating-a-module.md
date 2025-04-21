# Creating a Module

This guide walks you through creating your own module for Project Eidolon, from basic setup to advanced features.

If you'd like a refresher on the basic module architecture, please read the [modules overview](1-overview.md)

## Module Structure

A typical Eidolon module consists of the following components:

```
your_module/
├── __init__.py
├── main.py
├── module.yaml
└── tests/
    └── __init__.py
```
Modules can, however, contain any files the creator pleases. This includes additional .py files, README files, LICENSE files etc.

## Step 1: Setting Up the Module Directory

Create a new directory under `src/modules/` with your module name:

```bash
# Example using Linux
mkdir -p src/modules/your_module/tests
touch src/modules/your_module/__init__.py
touch src/modules/your_module/tests/__init__.py
```

## Step 2: Creating the Module Configuration File

The `module.yaml` file defines your module's metadata, inputs, outputs, and dependencies. For more details on all configuration options, see the [module configuration guide](config.md).

Create a file named `module.yaml` in your module directory:

```yaml
name: 'your_module'
alias: 'your-module'
creator: 'Your Name'
runtime:
  main: 'main.py'
  tests:
    - 'tests/test_your_module.py'
repository: 'https://github.com/<username>/<repository>.git' # optional
description: 'Description of what your module does'
version: '1.0.0'
requirements:
  - name: 'example-python-package'
    version: '1.0.0'
inputs:
  - name: "input_data"
    type: "Dict[str, Any]"
    description: "Input data structure"
outputs:
  - name: "processed_results"
    type: "List[Dict[str, Any]]"
    description: "List of processed results"
```

## Step 3: Implementing Your Module

Create a `main.py` file that implements your module's functionality. With the enhanced ModuleCore, you only need to override specific hook methods for your module's custom logic. For a list of all available hook methods, see the [module methods documentation](methods.md).

Here's a simple module example:

``` py
from typing import List, Dict, Any

from core.modules.engine import ModuleCore
from core.modules.models import Device
from core.modules.util.messagebus import MessageBus


class YourModule(ModuleCore):
    """
    Your module description here.
    """

    def _initialize_module(self) -> None:
        """
        Initialize module-specific components.
        Called after the base ModuleCore initialization.
        """
        self.processed_results = []
        self.custom_state = {}
    
    def process(self, data: Any) -> None:
        """
        Process input data from the message bus.
        """
        if isinstance(data, dict):
            self.input_data = data
            self._logger.info(f"Received input data with keys: {data.keys()}")
        else:
            self._logger.warning(f"Received unexpected data type: {type(data)}")
    
    async def execute(self, message_bus: MessageBus) -> None:
        """
        A single iteration of the module's main logic.
        This is called periodically by the ModuleCore's run method.
        """
        if hasattr(self, 'input_data') and self.input_data:
            results = self._process_data()
            if results:
                await message_bus.publish("processed_results", results)
    
    def _process_data(self) -> List[Dict[str, Any]]:
        """
        Process the current input data.
        Returns the results to be published to the message bus.
        """
        results = []
        # Implement your data processing logic here
        for key, value in self.input_data.items():
            results.append({
                "original_key": key,
                "processed_value": f"Processed: {value}"
            })
        return results
        
    def cycle_time(self) -> float:
        """
        Get the time between execution cycles.
        """
        return 30.0  # Run every 30 seconds
```

This simplified implementation takes advantage of the built-in functionality provided by ModuleCore, including:

- Automatic metadata loading from module.yaml
- Standard lifecycle management
- Error handling
- Shutdown coordination
- Default command handling

## Step 4: Add Your Module to a Pipeline

To use your module, add it to a pipeline configuration file. For more details on pipelines, see the [pipeline overview](../pipelines/1-overview.md).

```yaml
modules:
  - name: "your_module"
    depends_on:
      - "keyword_monitor"
    input_mappings:
      input_data: "keywords"
```

### Pipeline Fields

| Field | Description | Required | Example |
|-------|-------------|----------|---------|
| `name` | A snake_case name matching the directory / configuration name of your module | yes | "example_module" |
| `depends_on` | The snake_case name matching the directory / config name of a module this module depends on | no | "dependent_module" |
| `input_mappings` | The name of the input(s) this module will be acquiring from the module it depends on | no | required_input: "dependent_module_output" |

## Step 5: Testing Your Module

Create a test file for your module in the `tests/` directory. For comprehensive testing guidance, see the [module testing documentation](tests.md).

``` py
import pytest
from unittest.mock import Mock, patch
from core.modules.util.messagebus import MessageBus
from ..main import YourModule


def test_module_initialization():
    logger = Mock()
    module = YourModule(logger)
    
    assert module.meta.name == "your_module"
    assert hasattr(module, 'processed_results')


@pytest.mark.asyncio
async def test_run_iteration():
    logger = Mock()
    module = YourModule(logger)
    message_bus = Mock(spec=MessageBus)
    message_bus.publish = Mock()
    
    module.input_data = {"test": "data"}
    
    await module.execute(message_bus)
    
    message_bus.publish.assert_called_once()
    args = message_bus.publish.call_args[0]
    assert args[0] == "processed_results"
    assert isinstance(args[1], list)


def test_process_input():
    logger = Mock()
    module = YourModule(logger)
    
    test_data = {"param1": "value1", "param2": 42}
    module.process(test_data)
    assert module.input_data == test_data
```

## Best Practices

1. **Single Responsibility**: Each module should do one thing well
2. **Override Only What You Need**: Take advantage of ModuleCore's default implementations
3. **Error Handling**: Let ModuleCore handle most errors, but add specific handling for your business logic
4. **Documentation**: Add docstrings to describe your module's purpose and methods
5. **Testing**: Write tests for your custom hook methods

## Advanced Features

### Custom Commands

You can implement custom commands by overriding the `_handle_custom_command` method:

``` py
def _handle_custom_command(self, command: chr) -> Device:
    if command == "C":  # Custom command to clear data
        self.input_data = {}
        self.processed_results = []
        self._logger.info("Cleared all data")
        return Device(
            name=self.meta.name,
            firmware=0x10000,
            protocol="CLEARED",
            errors=[]
        )
    
    # Fall back to standard command handling for other commands
    return super()._handle_custom_command(command)
```

### Module Lifecycle Hooks

For more control over the module lifecycle, override the lifecycle hook methods:

```python
async def _before_run(self, message_bus: MessageBus) -> None:
    """Setup code that runs once before the main module loop"""
    self._logger.info("Initializing external connections...")
    self.client = await self._create_client()

async def _after_run(self, message_bus: MessageBus) -> None:
    """Cleanup code that runs once after the main module loop"""
    self._logger.info("Cleaning up resources...")
    await self.client.close()

async def cleanup(self):
    """Custom resource cleanup during shutdown"""
    self._logger.info("Performing custom shutdown tasks...")
    await self._save_state()
```

## Troubleshooting

### Common Issues

1. **Module Not Loading**
   - Check that your module.yaml is correctly formatted
   - Ensure your class inherits from ModuleCore
   - Verify module directory structure is correct

2. **No Data Received**
   - Check topic names in pipeline configuration
   - Verify input_mappings are correctly set up
   - Ensure publishing modules are running

3. **Type Errors**
   - Ensure published data matches the expected type
   - Check type hints in your code match module.yaml

4. **Module Crashes**
   - Check the logs for error messages
   - Add try/except blocks in your custom processing logic
   - Consider overriding _process_input to add stronger validation