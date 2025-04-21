# Converting Existing Python Applications

This guide explains how to convert an existing Python application into an Eidolon-compatible module, allowing you to integrate your standalone tools into the Eidolon pipeline system.

## Overview

Converting an existing application into an Eidolon module involves:

1. Creating a module structure around your existing code
2. Moving your application logic into a module class that inherits from `ModuleCore`
3. Adapting command-line arguments to Eidolon's configuration system
4. Configuring module inputs and outputs for pipeline integration

## Step 1: Create the Module Structure

First, create a new directory for your module in the `src/modules/` directory:

```bash
mkdir -p src/modules/your_app_module/
```

Your final directory structure should look something like this:

```
your_app_module/
├── __init__.py
├── module.py         # Your new module integration file
├── module.yaml       # Module configuration
├── src/              # Optional directory for your existing application code
│   ├── __init__.py
│   ├── app.py        # Your existing application's main file
│   └── utils.py      # Other application files
└── tests/
    └── __init__.py
```

## Step 2: Create the Module Configuration

Create a `module.yaml` file in your module directory that defines your module's metadata, inputs, outputs, and configuration options:

```yaml
name: 'your_app_module'
alias: 'your-app'
creator: 'Your Name'
runtime:
  main: 'module.py'
  tests:
    - 'tests/test_your_module.py'
description: 'Eidolon module wrapper for YourApp'
version: '1.0.0'
requirements:
  - name: 'your-app-dependencies'
    version: '1.0.0'
inputs:
  - name: "input_data"
    type: "Dict[str, Any]"
    description: "Input data structure for your application"
outputs:
  - name: "results"
    type: "List[Dict[str, Any]]"
    description: "Results from your application's processing"
```

## Step 3: Create the Module Integration File

Create a `module.py` file that inherits from `ModuleCore` and integrates your existing application:

```python
from typing import Dict, List, Any
import os
import sys

from core.modules.engine import ModuleCore
from core.modules.util.messagebus import MessageBus

# Import your existing application
# This assumes your code has been moved to the src subdirectory
from .src import app

class YourAppModule(ModuleCore):
    """
    Eidolon module wrapper for your existing Python application.
    """

    def _initialize_module(self) -> None:
        """
        Initialize your application components.
        """
        self.results = []
        self.input_data = {}
        
        # Initialize any application-specific components
        self.app_instance = app.YourApp()
        
        # Set default configuration values
        self.batch_size = 10
        self.output_format = "json"
    
    def _load_config(self) -> None:
        """
        Load configuration values from the pipeline configuration.
        This replaces command-line arguments from your original app.
        """
        if hasattr(self, 'config'):
            # Example of loading config values that would have been CLI args
            if 'batch_size' in self.config:
                self.batch_size = self.config.get('batch_size')
            
            if 'output_format' in self.config:
                self.output_format = self.config.get('output_format')
            
            # You can also load more complex nested configurations
            if 'advanced_settings' in self.config:
                advanced = self.config.get('advanced_settings')
                if advanced and 'timeout' in advanced:
                    self.app_instance.set_timeout(advanced['timeout'])
    
    def process(self, data: Dict[str, Any]) -> None:
        """
        Process input data received from the message bus.
        This replaces the input handling from your original app.
        """
        if isinstance(data, dict):
            self.input_data = data
            self._logger.info(f"Received input data with keys: {data.keys()}")
        else:
            self._logger.warning(f"Received unexpected data type: {type(data)}")
    
    async def execute(self, message_bus: MessageBus) -> None:
        """
        The main execution logic for your module.
        This is where you call your application's core functionality.
        """
        if not hasattr(self, 'input_data') or not self.input_data:
            return
        
        try:
            # Call your application's main processing function
            # with the input data and configuration options
            results = self.app_instance.process(
                data=self.input_data,
                batch_size=self.batch_size,
                output_format=self.output_format
            )
            
            # Publish the results to the message bus
            if results:
                await message_bus.publish("results", results)
                self._logger.info(f"Published {len(results)} results")
                
                # Clear the input data after processing
                self.input_data = {}
                
        except Exception as e:
            self._logger.error(f"Error processing data: {str(e)}")
    
    def cycle_time(self) -> float:
        """
        Define how often this module should execute.
        """
        return 30.0  # Run every 30 seconds
```

## Step 4: Adapt Your Existing Application

You may need to refactor your existing application code to work well as a module. Here are some common adaptations:

### Moving from Command-Line Arguments to Configuration

If your application uses `argparse` or similar libraries for CLI arguments, you'll need to adapt it to use Eidolon's configuration system:

**Original application code:**
```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True, help='Input file')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size')
    parser.add_argument('--output-format', choices=['json', 'csv'], default='json')
    args = parser.parse_args()
    
    # Process using the arguments
    process_data(args.input, args.batch_size, args.output_format)
```

**Adapted code:**
```python
class YourApp:
    def __init__(self):
        self.timeout = 30  # Default value
        
    def set_timeout(self, timeout):
        self.timeout = timeout
    
    def process(self, data, batch_size=10, output_format='json'):
        # Process the data using the provided parameters
        # instead of command-line arguments
        results = []
        # Your processing logic here
        return results
```

### Handling File Input/Output

If your application reads from or writes to files, adapt it to handle data directly:

**Original file handling:**
```python
def process_file(input_file, output_file):
    with open(input_file, 'r') as f_in:
        data = json.load(f_in)
    
    results = process_data(data)
    
    with open(output_file, 'w') as f_out:
        json.dump(results, f_out)
```

**Adapted data handling:**
```python
def process(self, data, **kwargs):
    # Direct data handling instead of file I/O
    results = self._process_data(data)
    return results
```

## Step 5: Integrate Your Module in a Pipeline

Add your module to a pipeline configuration file:

```yaml
pipeline:
  name: your_app_pipeline
  description: "Pipeline using your converted application"
  
  modules:
    # Source module that provides data
    - id: data_source
      module: data_source_module
      
    # Your converted application module
    - id: your_app
      module: your_app_module
      depends_on: [data_source]
      input:
        input_data: data_source.output_data
      config:
        batch_size: 20
        output_format: "json"
        advanced_settings:
          timeout: 60
      
    # Result handling module
    - id: result_handler
      module: result_handler_module
      depends_on: [your_app]
      input:
        input_results: your_app.results
```

## Step 6: Running Your Module

To run your application within Eidolon, use the `eidolon run` command:

```bash
# Run with the default configuration in the pipeline
eidolon run your_app_pipeline

# Override configuration at runtime
eidolon run your_app_pipeline --set your_app.batch_size=50 --set your_app.output_format=csv
```

The `--set` argument allows you to override configuration values defined in the pipeline without editing the pipeline file.

## Best Practices

1. **Keep Core Logic Separate**: Maintain your original application's core logic in its own files/classes, and use the module class as an adapter
2. **Test Thoroughly**: Write tests that verify your module behaves correctly with the Eidolon framework
3. **Provide Good Defaults**: Set sensible default values for all configuration options
4. **Document Configuration Options**: Update your documentation to explain all available configuration options

## Advanced Integration

### State Persistence

If your application needs to maintain state between executions:

```python
async def _before_shutdown(self) -> None:
    """Save state before the module shuts down."""
    state_file = os.path.join(self.meta.path, "state.json")
    with open(state_file, "w") as f:
        json.dump(self.app_instance.get_state(), f)

def _initialize_module(self) -> None:
    # Initialize as before
    
    # Load previous state if it exists
    state_file = os.path.join(self.meta.path, "state.json")
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            self.app_instance.set_state(json.load(f))
```

### Error Handling

Implement robust error handling to ensure pipeline stability:

```python
async def execute(self, message_bus: MessageBus) -> None:
    if not hasattr(self, 'input_data') or not self.input_data:
        return
    
    try:
        # Process data and publish results
    except ValueError as e:
        self._logger.warning(f"Invalid input data: {str(e)}")
        # Handle the specific error appropriately
    except Exception as e:
        self._logger.error(f"Unexpected error: {str(e)}")
        # Optionally publish error information
        await message_bus.publish("error", {"error_type": type(e).__name__, "message": str(e)})
```

## Example: Converting a Text Analysis Tool

Let's say you have a text analysis tool that performs sentiment analysis on text content. Here's how you might convert it:

### Original Application
```python
# text_analyzer.py
import argparse
import json

def analyze_sentiment(text):
    # Simplified sentiment analysis logic
    positive_words = ["good", "great", "excellent", "happy"]
    negative_words = ["bad", "poor", "terrible", "sad"]
    
    positive_count = sum(1 for word in text.lower().split() if word in positive_words)
    negative_count = sum(1 for word in text.lower().split() if word in negative_words)
    
    if positive_count > negative_count:
        return {"text": text, "sentiment": "positive", "score": positive_count - negative_count}
    elif negative_count > positive_count:
        return {"text": text, "sentiment": "negative", "score": negative_count - positive_count}
    else:
        return {"text": text, "sentiment": "neutral", "score": 0}

def main():
    parser = argparse.ArgumentParser(description="Text sentiment analyzer")
    parser.add_argument("--input", type=str, help="Input file with text to analyze")
    parser.add_argument("--output", type=str, default="results.json", help="Output file path")
    
    args = parser.parse_args()
    
    # Read input file
    with open(args.input, "r") as f:
        texts = [line.strip() for line in f.readlines()]
    
    # Process each text
    results = [analyze_sentiment(text) for text in texts]
    
    # Write results
    with open(args.output, "w") as f:
        json.dump(results, f)
    
    print(f"Analyzed {len(results)} texts and saved to {args.output}")

if __name__ == "__main__":
    main()
```

### Converted Module
```python
# module.py
from typing import List, Dict, Any
import os

from core.modules.engine import ModuleCore
from core.modules.util.messagebus import MessageBus

# Import the existing functionality
from .src.text_analyzer import analyze_sentiment

class TextAnalyzerModule(ModuleCore):
    """
    Eidolon module for text sentiment analysis.
    """
    
    def _initialize_module(self) -> None:
        """Initialize the module."""
        self.texts = []
        self.results = []
    
    def process(self, data: Any) -> None:
        """Process incoming texts for analysis."""
        if isinstance(data, list):
            self.texts = data
            self._logger.info(f"Received {len(data)} texts for analysis")
        elif isinstance(data, dict) and 'texts' in data:
            self.texts = data['texts']
            self._logger.info(f"Received {len(data['texts'])} texts for analysis")
        elif isinstance(data, str):
            self.texts = [data]
            self._logger.info(f"Received 1 text for analysis")
        else:
            self._logger.warning(f"Received unexpected data type: {type(data)}")
    
    async def execute(self, message_bus: MessageBus) -> None:
        """Execute sentiment analysis on the received texts."""
        if not hasattr(self, 'texts') or not self.texts:
            return
        
        try:
            # Process each text using the existing analyze_sentiment function
            results = [analyze_sentiment(text) for text in self.texts]
            
            # Publish the results
            await message_bus.publish("sentiment_results", results)
            self._logger.info(f"Published sentiment analysis for {len(results)} texts")
            
            # Clear the input data after processing
            self.texts = []
            
        except Exception as e:
            self._logger.error(f"Error during sentiment analysis: {str(e)}")
```

### Module Configuration (module.yaml)
```yaml
name: 'text_analyzer'
alias: 'sentiment-analysis'
creator: 'Your Name'
runtime:
  main: 'module.py'
description: 'Text sentiment analysis module'
version: '1.0.0'
inputs:
  - name: "texts"
    type: "Union[List[str], str, Dict[str, List[str]]]"
    description: "Text content to analyze"
outputs:
  - name: "sentiment_results"
    type: "List[Dict[str, Any]]"
    description: "Sentiment analysis results"
```

## See Also

- [Creating a Module](2-creating-a-module.md) - More details on creating modules from scratch
- [Module Configuration](config.md) - How to configure module inputs, outputs, and settings
- [Module Methods](methods.md) - Available hook methods in the ModuleCore class
- [Pipeline Creation](../pipelines/creating-a-pipeline.md) - How to integrate your module into pipelines