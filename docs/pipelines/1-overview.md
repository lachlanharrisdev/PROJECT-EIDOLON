# Pipeline System Overview

Pipelines are a core concept in Project Eidolon that define how modules are connected and interact with each other. A pipeline is essentially a configuration that specifies which modules to load and how data flows between them.

The only way to run modules is via a pipeline, however pipelines are provided as default within the program to provide access to features most users will require.

## What are Pipelines?

Pipelines are YAML configuration files that:

1. Define which modules to load
2. Specify dependencies between modules
3. Map inputs and outputs between modules
4. Control the execution flow of the system

## Pipeline Structure

A pipeline file has the following structure:

```yaml
pipeline:
  name: pipeline_name
  description: "Description of what this pipeline does"
  
  execution:
    max_threads: 8
    
  modules:
    - id: first_module
      module: first_module_name
      
    - id: second_module
      module: second_module_name
      depends_on: [first_module]
      input:
        second_module_input: first_module.first_module_output
      
    - id: third_module
      module: third_module_name
      depends_on: [first_module, second_module]
      input:
        third_module_input1: first_module.first_module_output
        third_module_input2: second_module.second_module_output

#   - id: <identifier>
```

### Key Components

1. **`pipeline`**: The root element containing all pipeline information
     - **`name`**: Unique identifier for the pipeline
     - **`description`**: Human-readable description of the pipeline's purpose
     - **`execution`**: Pipeline execution configuration
        - **`timeout`**: Maximum execution time before shutdown
        - **`retries`**: Number of retries on critical errors
        - **`error_policy`**: How to handle errors

2. **`modules`**: List of modules to load
    - **`id`**: Module identifier within the pipeline
    - **`module`**: Actual module name (must match a module directory name)
    - **`depends_on`**: List of module IDs this module depends on
    - **`input`**: Dictionary mapping this module's inputs to other modules' outputs
    - **`config`**: Module-specific configuration
    - **`run_mode`**: How the module executes (loop, once, reactive)

## Input Mappings

The `input` field in a module configuration allows you to connect specific inputs of a module to specific outputs of another module. This provides flexibility in:

1. Renaming data channels between modules
2. Connecting one output to multiple inputs
3. Selecting specific data sources when multiple are available

The format for an input mapping is:
```yaml
input:
  input_name: module_id.output_name
```

Where:

- `input_name`: Name of an input defined in the current module's `module.yaml`
- `module_id`: ID of the module producing the output
- `output_name`: Name of the output from the source module

## Default Pipelines

Project Eidolon includes several pre-configured pipelines for common OSINT workflows:

1. **Default Pipeline** (`default.yaml`): A general-purpose pipeline that includes basic data collection and analysis
   
2. **Aethon Pipeline** (`aethon.yaml`): A web-focused pipeline for crawling and analyzing web content using the Aethon module package

You can use these as starting points for your own custom pipelines.

## Running a Pipeline

To run a specific pipeline, use the `eidolon run` command:

```bash
# Run the default pipeline
eidolon run

# Run a custom pipeline
eidolon run custom_pipeline
```

## See Also

- [Creating a Pipeline](creating-a-pipeline.md) - Detailed guide on creating your own pipelines
- [Module Configuration](../modules/config.md) - How to configure modules used in pipelines
- [Message Bus](../modules/methods.md) - How the message bus connects modules in a pipeline