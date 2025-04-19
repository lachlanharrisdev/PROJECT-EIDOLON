# Creating a Module

This guide walks you through creating your own module for Project Eidolon, from basic setup to advanced features.

If you'd like a refresher on the basic module setup, please read the [modules overview](1-overview.md)

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
  - name: "data_output"
    type: "Dict[str, Any]"
    description: "Input data structure"
outputs:
  - name: "data_output"
    type: "List[Dict[str, Any]]"
    description: "List of processed results"
```

## Step 3: Implementing Your Module

Create a `main.py` file that implements your module's functionality. For a list of all abstract methods, and for detailed descriptions of each method, see the [module methods documentation](methods.md).

``` py
from logging import Logger
from typing import List, Dict, Any

from core.modules.engine import ModuleCore
from core.modules.models import Device, Meta
from core.modules.util.messagebus import MessageBus


class YourModule(ModuleCore):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)
        
        module_data = self.get_config()
        self.meta = Meta(
            name=module_data["name"],
            description=module_data["description"],
            version=module_data["version"],
        )
        
        self.input_data = {}
        self.processed_results = []

    def invoke(self, command: chr) -> Device:
        if command == "P" and self.input_data:
            self.processed_results = self._process_data()
            
        return Device(
            name=self.meta.name,
            firmware=0x10000,
            protocol="CUSTOM",
            errors=[]
        )
    async def shutdown(self):
        self._logger.info(f"Shutting down {self.meta.name}")

    def handle_input(self, data: Any) -> None:
        if isinstance(data, dict):
            self.input_data = data
        else:
            self._logger.warning(f"Unexpected data type: {type(data)}")

    def run(self, messagebus: MessageBus) -> None:
        if self.input_data:
            self.processed_results = self._process_data()
            
            if self.processed_results:
                messagebus.publish("processed_results", self.processed_results)


    def _example_function(self) -> List[Dict[str, Any]]:
        results = []
        return results
```

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
    assert isinstance(module.processed_results, list)


def test_handle_input():
    logger = Mock()
    module = YourModule(logger)
    
    test_data = {"param1": "value1", "param2": 42}
    module.handle_input(test_data)
    assert module.input_data == test_data


def test_run_with_data():
    logger = Mock()
    module = YourModule(logger)
    messagebus = Mock(spec=MessageBus)
    
    module.input_data = {"test": "data"}
    
    with patch.object(module, '_process_data', return_value=[{"result": "test"}]):
        module.run(messagebus)
        messagebus.publish.assert_called_once_with("processed_results", [{"result": "test"}])
```

## Best Practices

1. **Single Responsibility**: Each module should do one thing well
2. **Clean Error Handling**: Log errors appropriately and fail gracefully
3. **Type Safety**: Use Python type hints to ensure type safety
4. **Documentation**: Document your module's purpose, inputs, outputs, and behavior in a `docs/` directory or `README.md` file
5. **Testing**: Write comprehensive tests for your module's functionality

## Advanced Features

### Custom Commands

You can implement custom commands in the `invoke()` method:

``` py
def invoke(self, command: chr) -> Device:
    if command == "R":
        self.input_data = {}
        self.processed_results = []
    elif command == "D":
        self._logger.info(f"Current state: {self.input_data}")
        
    return Device(name=self.meta.name, firmware=0x10000, protocol="CUSTOM", errors=[])
```

## Troubleshooting

### Common Issues

1. **Module Not Loading**
   - Check that your module.yaml is correctly formatted
   - Ensure your class inherits from ModuleCore
   - Verify all required methods are implemented

2. **No Data Received**
   - Check topic names in pipeline configuration
   - Verify input_mappings are correctly set up
   - Ensure publishing modules are running

3. **Type Errors**
   - Ensure published data matches the expected type
   - Check type hints in your code match module.yaml