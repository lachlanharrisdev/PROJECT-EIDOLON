# Module Configuration

This document provides a detailed guide for configuring modules in Project Eidolon using the `module.yaml` format.

## Configuration File Structure

Each module in Project Eidolon requires a `module.yaml` file that defines its metadata, runtime settings, dependencies, inputs, and outputs. This standardized format ensures modules can be dynamically loaded and connected by the ModuleEngine.

### Basic Structure

```yaml
name: 'module_name'              # Internal identifier (required)
alias: 'module-name'             # Display name (required)
creator: 'Author Name'           # Module author (required)
description: 'Module purpose'    # Brief description (required)
version: '0.1.0'                 # Semantic version (required)
repository: 'https://github.com/repo/url'  # Source code URL (optional)

# Runtime configuration
runtime:
  main: 'main.py'                # Main module file (required)
  tests:                         # Test files (optional)
    - 'tests/test_module.py'

# External dependencies
requirements:              # Python package dependencies (optional)
  - name: 'package_name'
    version: '1.2.3'

# Input and output specifications
inputs:                   # Data the module accepts (optional)
  - name: "input_name"
    type: "type_annotation"
    description: "Input description"

outputs:                  # Data the module produces (optional)
  - name: "output_name" 
    type: "type_annotation"
    description: "Output description"
```

## Required Fields

### Module Identity

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Internal identifier used by the system | `'keyword_monitor'` |
| `alias` | Human-readable name for display | `'keyword-monitor'` |
| `creator` | Module author or organization | `'John Smith'` |
| `description` | One-line summary of module functionality | `'Monitors political keywords in news sources'` |
| `version` | [Semantic versioning](https://semver.org/) string | `'1.2.3'` |

### Runtime Configuration

The `runtime` section specifies the files that make up the module:

```yaml
runtime:
  main: 'main.py'
  tests:
    - 'tests/test_basic.py'
    - 'tests/test_advanced.py'
```

## Optional Fields

### Requirements

The `requirements` section lists external Python packages required by the module:

```yaml
requirements:
  - name: 'requests'
    version: '2.28.1'
  - name: 'beautifulsoup4'  
    version: '4.11.1'
  - name: 'nltk'
    version: '3.7'
```

Requirements are automatically installed when the module is first loaded.

### Repository

The `repository` field links to the source code repository:

```yaml
repository: 'https://github.com/user/repository'
```

## Input and Output Definitions

The `inputs` and `outputs` sections define the data interfaces for the module. For information on implementing these in code, see the [module methods documentation](methods.md).

### Input Definition

```yaml
inputs:
  - name: "raw_text"
    type: "str"
    description: "Unprocessed text content from news articles"
  
  - name: "configuration"
    type: "Dict[str, Any]"
    description: "Configuration parameters for text processing"
```

### Output Definition

```yaml
outputs:
  - name: "keywords"
    type: "List[str]"
    description: "Extracted political keywords"
  
  - name: "entities"
    type: "Dict[str, List[str]]"
    description: "Named entities grouped by type"
```

## Type Annotations

Type annotations should follow Python's typing syntax. These are the currently supported types:

| Common Type Annotations | Description | 
|------------------------|-------------|
| `str` | Text data |
| `int` | Integer values |
| `float` | Decimal values |
| `bool` | Boolean (True/False) values |
| `List[type]` | List containing elements of specified type |
| `Dict[key_type, value_type]` | Dictionary with specified key and value types |
| `Set[type]` | Set containing elements of specified type |
| `Tuple[type1, type2, ...]` | Tuple with elements of specified types |
| `Optional[type]` | Value of specified type or None |
| `Any` | Any data type |
| `Union[type1, type2, ...]` | Value that could be any of the specified types |

## Complete Example

```yaml
name: 'sentiment_analyzer'
alias: 'sentiment-analyzer'
creator: 'Project Eidolon Team'
runtime:
  main: 'main.py'
  tests:
    - 'tests/test_sentiment.py'
repository: 'https://github.com/lachlanharrisdev/PROJECT-EIDOLON'
description: 'Analyzes sentiment in political texts'
version: '0.2.1'
requirements:
  - name: 'transformers'
    version: '4.26.0'
  - name: 'torch'
    version: '2.0.0'
inputs:
  - name: "text_data"
    type: "Union[str, List[str]]"
    description: "Text content to analyze"
  - name: "analysis_options"
    type: "Dict[str, Any]"
    description: "Configuration options"
outputs:
  - name: "sentiment_scores"
    type: "Dict[str, float]"
    description: "Sentiment scores with positive/negative/neutral values"
  - name: "entity_sentiment"
    type: "Dict[str, Dict[str, float]]"
    description: "Entity-specific sentiment analysis"
```

## Best Practices

1. **Be Specific with Types**: Use specific type annotations rather than `Any` when possible
2. **Descriptive Names**: Use clear, descriptive names for inputs and outputs
3. **Complete Descriptions**: Write thorough descriptions for each input and output
4. **Minimal Dependencies**: Only include necessary external dependencies
5. **Consistent Naming**: Follow naming conventions across all modules

## Common Mistakes

- **Missing Required Fields**: Ensure all required fields are present
- **Incorrect Indentation**: YAML is whitespace-sensitive; maintain proper indentation
- **Type Annotation Format**: Type annotations must follow Python typing syntax
- **Version Format**: Version strings should follow semantic versioning (MAJOR.MINOR.PATCH)
- **Inconsistent Naming**: Input/output names should match what your code publishes/receives

For information on creating a complete module, see the [Creating a Module guide](2-creating-a-module.md).

For guidance on module verification and security, see the [verification documentation](verification.md).