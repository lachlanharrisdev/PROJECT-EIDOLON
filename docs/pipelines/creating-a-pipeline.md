# Creating a Pipeline

This guide walks through the process of creating a custom pipeline for Project Eidolon, allowing you to define how modules connect and interact with each other.

## Basic Structure

A pipeline is defined in a YAML file with a `.yaml` extension in the `src/pipelines/` directory. The file should have the following structure:

```yaml
pipeline:
  name: custom_pipeline_name
  description: "A description of what this pipeline does"
  
  execution:
    timeout: 300s
    retries: 2
    error_policy: halt
    
  modules:
    - id: module1
      module: module1_name
      
    - id: module2
      module: module2_name
      depends_on: [module1]
      input:
        module2_input: module1.module1_output
      config:
        option1: value1
      run_mode: reactive
```

## Step-by-Step Guide

### Step 1: Create a new YAML file

Create a new file in the `src/pipelines/` directory with a descriptive name, such as `analytics_pipeline.yaml`.

### Step 2: Define the pipeline properties

Start by defining the pipeline properties at the top of the file:

```yaml
pipeline:
  name: analytics_pipeline
  description: "Processes analytics data from various sources"
  
  execution:
    timeout: 300s
    retries: 3
    error_policy: halt
```

The name will be used when running the pipeline via the command line, and the description helps document the pipeline's purpose.

### Step 3: List the modules

Add all the modules that should be part of the pipeline under the `modules` key:

```yaml
pipeline:
  # ...pipeline properties...
  modules:
    - id: collector
      module: data_collector
      run_mode: loop
      
    - id: processor
      module: data_processor
      run_mode: reactive
```

The `id` field defines how the module is referenced within the pipeline, while the `module` field specifies the actual module name (directory) to load.

### Step 4: Define dependencies

For each module that depends on data from another module, add a `depends_on` list:

```yaml
pipeline:
  # ...pipeline properties...
  modules:
    - id: collector
      module: data_collector
      
    - id: processor
      module: data_processor
      depends_on: [collector]
```

### Step 5: Map inputs and outputs

Connect specific module inputs to other modules' outputs using the `input` field:

```yaml
pipeline:
  # ...pipeline properties...
  modules:
    - id: collector
      module: data_collector
      outputs:
        - collected_data
      
    - id: processor
      module: data_processor
      depends_on: [collector]
      input:
        raw_data: collector.collected_data
```

The `input` dictionary connects:

- Keys: Input names in the current module
- Values: Qualified references to outputs from dependency modules (module_id.output_name)

### Step 6: Configure module behavior

Add module-specific configuration via the `config` field and specify execution behavior with `run_mode`:

```yaml
pipeline:
  # ...pipeline properties...
  modules:
    - id: processor
      module: data_processor
      depends_on: [collector]
      input:
        raw_data: collector.collected_data
      config:
        batch_size: 100
        cleanup: true
      run_mode: reactive
```

Available run modes include:
- `loop`: Module runs continuously in a loop (default)
- `once`: Module runs once and completes
- `reactive`: Module runs whenever new data is received
- `on_trigger`: Module runs only when explicitly triggered

## Input Mapping Rules

When setting up input mappings, follow these rules:

1. The input name (key) must match an input defined in the module's `module.yaml`
2. The output reference (value) should use the format `module_id.output_name`
3. The types of the connected inputs and outputs must be compatible

## Advanced Pipeline Features

### Module Configuration

Each module can have custom configuration options that override the defaults:

```yaml
- id: processor
  module: data_processor
  config:
    batch_size: 100
    cleanup: true
    stopwords: ["the", "and", "is"]
```

### Run Mode Selection

The `run_mode` field controls how a module executes:

```yaml
- id: monitor
  module: keyword_monitor
  run_mode: loop  # Runs continuously in a loop

- id: processor
  module: data_processor
  run_mode: reactive  # Runs when new data is received

- id: reporter
  module: data_reporter
  run_mode: once  # Runs once and completes
```

### Error Handling

The `execution` section controls pipeline-wide error handling:

```yaml
execution:
  timeout: 300s  # Maximum execution time before shutdown
  retries: 2     # Number of retries if critical errors occur
  error_policy: halt  # How to handle errors (halt, continue, isolate, log_only)
```

## Common Patterns

### Linear Pipeline

Modules run in sequence with each depending on the previous:

```yaml
pipeline:
  name: linear_pipeline
  modules:
    - id: collector
      module: data_collector
      
    - id: processor
      module: data_processor
      depends_on: [collector]
      input:
        raw_data: collector.collected_data
      
    - id: analyzer
      module: data_analyzer
      depends_on: [processor]
      input:
        processed_data: processor.normalized_data
```

### Star Pattern

One central module feeds data to multiple independent modules:

```yaml
pipeline:
  name: star_pipeline
  modules:
    - id: publisher
      module: central_publisher
      
    - id: consumer_a
      module: consumer_a
      depends_on: [publisher]
      input:
        input_data: publisher.published_data
      
    - id: consumer_b
      module: consumer_b
      depends_on: [publisher]
      input:
        input_data: publisher.published_data
      
    - id: consumer_c
      module: consumer_c
      depends_on: [publisher]
      input:
        input_data: publisher.published_data
```

### Aggregation Pattern

Multiple modules feed into a single aggregator:

```yaml
pipeline:
  name: aggregation_pipeline
  modules:
    - id: source_a
      module: data_source_a
      
    - id: source_b
      module: data_source_b
      
    - id: source_c
      module: data_source_c
      
    - id: aggregator
      module: aggregator
      depends_on: [source_a, source_b, source_c]
      input:
        source_a_data: source_a.data_a
        source_b_data: source_b.data_b
        source_c_data: source_c.data_c
```

## Testing a Pipeline

To test your pipeline, run it using the `eidolon run` command:

```bash
eidolon run analytics_pipeline
```

You should see log messages showing:

1. The pipeline being loaded
2. Modules being discovered and loaded
3. Input and output connections being established
4. Modules running in the correct dependency order

## Troubleshooting

### Common Issues

1. **Module not found**: Ensure the module name in the pipeline matches the directory name in `src/modules/`
```
ERROR: Module 'sentiment_analizer' not found. Did you mean 'sentiment_analyzer'?
```

2. **Input/output mismatch**: Check that the input and output names match those defined in the module configuration files
```
WARNING: Module 'data_visualizer' has no input named 'raw_data'
```

3. **Type mismatch**: Ensure the types of connected inputs and outputs are compatible
```
WARNING: Type mismatch: Output 'keywords' (List[str]) -> Input 'numeric_data' (Dict[str, float])
```

4. **Circular dependencies**: Avoid creating circular dependencies between modules
```
ERROR: Circular dependency detected: module1 -> module2 -> module3 -> module1
```

### Debugging Tips

1. Run with increased log level to see more details:
   ```bash
   eidolon run analytics_pipeline --log-level=DEBUG
   ```

2. Check module configurations to ensure inputs and outputs are correctly defined:
   ```bash
   cat src/modules/sentiment_analyzer/module.yaml
   ```

3. List all available modules to verify name spelling:
   ```bash
   eidolon list modules
   ```

## Best Practices

1. **Descriptive naming**: Use clear, descriptive names for pipelines and maintain a consistent naming convention
2. **Minimal dependencies**: Only include necessary dependencies between modules
3. **Logical grouping**: Group related modules in the same pipeline
4. **Documentation**: Add comments in your pipeline YAML file to document non-obvious connections
5. **Incremental testing**: Build your pipeline incrementally, testing as you add each module

## Example: Full Analytics Pipeline

Here's a complete example of an analytics pipeline that:

1. Monitors news sources for keywords
2. Analyzes sentiment of the collected articles
3. Generates visualization data for a dashboard
4. Publishes results to both a web interface and a CSV exporter

```yaml
pipeline:
  name: full_analytics_pipeline
  description: "Full analytics pipeline for monitoring, analyzing, and visualizing data"
  
  execution:
    timeout: 300s
    retries: 3
    error_policy: halt
  
  modules:
    # Data collection layer
    - id: keyword_monitor
      module: keyword_monitor
      run_mode: loop
    
    - id: news_scraper
      module: news_scraper
      depends_on: [keyword_monitor]
      input:
        search_terms: keyword_monitor.keywords
      run_mode: reactive
    
    # Analysis layer
    - id: sentiment_analyzer
      module: sentiment_analyzer
      depends_on: [news_scraper]
      input:
        text_data: news_scraper.article_content
      run_mode: reactive
    
    - id: entity_extractor
      module: entity_extractor
      depends_on: [news_scraper]
      input:
        input_text: news_scraper.article_content
      run_mode: reactive
    
    # Visualization layer
    - id: chart_generator
      module: chart_generator
      depends_on: [sentiment_analyzer, entity_extractor]
      input:
        sentiment_data: sentiment_analyzer.sentiment_scores
        entity_data: entity_extractor.extracted_entities
      run_mode: reactive
    
    # Output layer
    - id: web_interface
      module: web_interface
      depends_on: [chart_generator]
      input:
        chart_data: chart_generator.visualization_data
      run_mode: reactive
    
    - id: csv_exporter
      module: csv_exporter
      depends_on: [sentiment_analyzer, entity_extractor]
      input:
        sentiment_export: sentiment_analyzer.sentiment_scores
        entity_export: entity_extractor.extracted_entities
      run_mode: reactive
```

## See Also

- [Pipeline Overview](1-overview.md) - Overview of the pipeline system
- [Module Methods](../modules/methods.md) - How modules communicate through the message bus
- [Module Configuration](../modules/config.md) - How to define module inputs and outputs