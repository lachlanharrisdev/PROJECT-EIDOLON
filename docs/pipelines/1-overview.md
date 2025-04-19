# Pipeline System Overview

Pipelines are a core concept in Project Eidolon that define how modules are connected and interact with each other. A pipeline is essentially a configuration that specifies which modules to load and how data flows between them.

## What are Pipelines?

Pipelines are YAML configuration files that:

1. Define which modules to load
2. Specify dependencies between modules
3. Map inputs and outputs between modules
4. Control the execution flow of the system

## Pipeline Structure

A pipeline file has a simple structure:

```yaml
name: pipeline_name
modules:
  - name: first_module
  
  - name: second_module
    depends_on:
      - first_module
    input_mappings:
      second_module_input: first_module_output
      
  - name: third_module
    depends_on:
      - first_module
      - second_module
    input_mappings:
      third_module_input1: first_module_output
      third_module_input2: second_module_output
```

### Key Components

1. **`name`**: Unique identifier for the pipeline
2. **`modules`**: List of modules to load
   - **`name`**: Name of the module (must match a module directory name)
   - **`depends_on`**: List of modules this module depends on
   - **`input_mappings`**: Dictionary mapping this module's inputs to other modules' outputs

## How Pipelines Work

1. The `PipelineLoader` loads and parses the pipeline configuration file
2. The `ModuleEngine` discovers and loads the specified modules
3. The engine connects modules by subscribing inputs to the corresponding outputs
4. Modules are activated in dependency order
5. Data flows through the pipeline via the message bus

## Example Pipeline Flow

```
┌────────────────┐     ┌───────────────┐     ┌─────────────────┐
│                │     │               │     │                 │
│ keyword_monitor├────►│keyword_printer│     │  data_analyzer  │
│                │     │               │     │                 │
└────────┬───────┘     └───────────────┘     └────────┬────────┘
         │                                            │         
         │                                            │         
         │             ┌───────────────┐              │         
         │             │               │              │         
         └────────────►│template_module◄──────────────┘         
                       │               │                        
                       └───────────────┘                        
```

## Default Pipeline

Project Eidolon includes a default pipeline (`default.yaml`):

```yaml
name: default
modules:
  - name: keyword_monitor
  
  - name: keyword_printer
    depends_on:
      - keyword_monitor
    input_mappings:
      keywords: keywords
      
  - name: template_module
    depends_on:
      - keyword_monitor
    input_mappings:
      keywords: keywords
```

This pipeline:
1. Loads the `keyword_monitor` module, which scrapes news sources for political keywords
2. Loads the `keyword_printer` module, connecting its `keywords` input to the `keywords` output from `keyword_monitor`
3. Loads the `template_module` module, also connecting its `keywords` input to the `keywords` output from `keyword_monitor`

## Module Dependencies

Dependencies in the pipeline configuration ensure that:

1. Modules are loaded in the correct order
2. All required modules are present
3. Data connections are properly established

## Input Mappings

Input mappings allow you to connect specific inputs of a module to specific outputs of another module. This provides flexibility in:

1. Renaming data channels between modules
2. Connecting one output to multiple inputs
3. Selecting specific data sources when multiple are available

## Running a Pipeline

To run a specific pipeline, use the `eidolon run` command:

```bash
# Run the default pipeline
eidolon run

# Run a custom pipeline
eidolon run custom_pipeline
```

The system will:
1. Load the specified pipeline file from `src/pipelines/`
2. Initialize all required modules
3. Connect inputs and outputs as defined in the pipeline
4. Run all modules in the correct order

## Benefits of the Pipeline System

1. **Modularity**: Easily swap modules in and out
2. **Flexibility**: Create different workflows for different use cases
3. **Clarity**: Clear definition of data flow between components
4. **Separation of concerns**: Module logic is independent of the pipeline configuration

## Pipeline Loading Process

When you start Eidolon with a specific pipeline, the following happens:

1. The `PipelineLoader` resolves the pipeline file path
2. It parses the YAML into a `Pipeline` object
3. The `ModuleEngine` extracts input mappings from the pipeline
4. It loads only the modules specified in the pipeline
5. The engine connects modules according to the pipeline configuration
6. Modules are invoked in the correct dependency order

## See Also

- [Creating a Pipeline](creating-a-pipeline.md) - Detailed guide on creating your own pipelines
- [Module Configuration](../modules/config.md) - How to configure modules used in pipelines
- [Message Bus](../modules/methods.md) - How the message bus connects modules in a pipeline