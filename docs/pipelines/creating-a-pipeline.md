# Creating a Pipeline

This guide walks through the process of creating a custom pipeline for Project Eidolon, allowing you to define how modules connect and interact with each other.

## Basic Structure

A pipeline is defined in a YAML file with a `.yaml` extension in the `src/pipelines/` directory. The file should have the following structure:

```yaml
name: custom_pipeline_name
modules:
  - name: module1_name
  
  - name: module2_name
    depends_on:
      - module1_name
    input_mappings:
      module2_input: module1_output
```

## Step-by-Step Guide

### Step 1: Create a new YAML file

Create a new file in the `src/pipelines/` directory with a descriptive name, such as `analytics_pipeline.yaml`.

### Step 2: Define the pipeline name

Start by defining the pipeline name at the top of the file:

```yaml
name: analytics_pipeline
```

This name will be used when running the pipeline via the command line.

### Step 3: List the modules

Add all the modules that should be part of the pipeline under a `modules` key:

```yaml
modules:
  - name: module_1
  - name: module_2
  # etc...
```

### Step 4: Define dependencies

For each module that depends on data from another module, add a `depends_on` list:

```yaml
modules:  
  - name: module_1
    depends_on:
      - module_2
```

### Step 5: Map inputs and outputs

Connect specific module inputs to other modules' outputs using `input_mappings`:

```yaml
modules:
  - name: module_1
    depends_on:
      - module_2
    input_mappings:
      my_input_string: module_2_output_string
```

The `input_mappings` dictionary connects:

- Keys: Input names in the current module
- Values: Output names from dependency modules

## Input Mapping Rules

When setting up input mappings, follow these rules:

1. The input name (key) must match an input defined in the module's `module.yaml`
2. The output name (value) must match an output defined in one of the dependency modules' `module.yaml`
3. The types of the connected inputs and outputs must be compatible

## Advanced Pipeline Features

### Implicit Mappings

If an input name exactly matches an output name, you can omit the mapping. The system will automatically connect them:

```yaml
# This implicit mapping:
- name: module_1
  depends_on:
    - module_2

# Is equivalent to this explicit mapping:
- name: module_1
  depends_on:
    - module_2
  input_mappings:
    my_input: their_output
```

### Multiple Dependencies

A module can depend on multiple other modules:

```yaml
- name: module_1
  depends_on:
    - module_2
    - module_3
    - module_4
  input_mappings:
    module_1_string: module_2_output
    module_1_list_strings: module_3_output_name
    another_input: module_4_named_their_output_weirdly_and_this_is_it
```

### Renaming Data Channels

Input mappings allow you to connect outputs to differently named inputs:

```yaml
- name: alert_system
  depends_on:
    - keyword_monitor
  input_mappings:
    alert_triggers: keywords  # Maps "keywords" output to "alert_triggers" input
```

## Common Patterns

### Linear Pipeline

Modules run in sequence with each depending on the previous:

```yaml
name: linear_pipeline
modules:
  - name: data_collector
  
  - name: data_processor
    depends_on:
      - data_collector
    input_mappings:
      raw_data: collected_data
  
  - name: data_analyzer
    depends_on:
      - data_processor
    input_mappings:
      processed_data: normalized_data
```

### Star Pattern

One central module feeds data to multiple independent modules:

```yaml
name: star_pipeline
modules:
  - name: central_publisher
  
  - name: consumer_a
    depends_on:
      - central_publisher
    input_mappings:
      input_data: published_data
  
  - name: consumer_b
    depends_on:
      - central_publisher
    input_mappings:
      input_data: published_data
  
  - name: consumer_c
    depends_on:
      - central_publisher
    input_mappings:
      input_data: published_data
```

### Aggregation Pattern

Multiple modules feed into a single aggregator:

```yaml
name: aggregation_pipeline
modules:
  - name: data_source_a
  - name: data_source_b
  - name: data_source_c
  
  - name: aggregator
    depends_on:
      - data_source_a
      - data_source_b
      - data_source_c
    input_mappings:
      source_a_data: data_a
      source_b_data: data_b
      source_c_data: data_c
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
name: full_analytics_pipeline
modules:
  # Data collection layer
  - name: keyword_monitor
  
  - name: news_scraper
    depends_on:
      - keyword_monitor
    input_mappings:
      search_terms: keywords
  
  # Analysis layer
  - name: sentiment_analyzer
    depends_on:
      - news_scraper
    input_mappings:
      text_data: article_content
  
  - name: entity_extractor
    depends_on:
      - news_scraper
    input_mappings:
      input_text: article_content
  
  # Visualization layer
  - name: chart_generator
    depends_on:
      - sentiment_analyzer
      - entity_extractor
    input_mappings:
      sentiment_data: sentiment_scores
      entity_data: extracted_entities
  
  # Output layer
  - name: web_interface
    depends_on:
      - chart_generator
    input_mappings:
      chart_data: visualization_data
  
  - name: csv_exporter
    depends_on:
      - sentiment_analyzer
      - entity_extractor
    input_mappings:
      sentiment_export: sentiment_scores
      entity_export: extracted_entities
```

## See Also

- [Pipeline Overview](1-overview.md) - Overview of the pipeline system
- [Module Methods](../modules/methods.md) - How modules communicate through the message bus
- [Module Configuration](../modules/config.md) - How to define module inputs and outputs