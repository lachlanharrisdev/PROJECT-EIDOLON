# Aethon Crawler

A lightweight, fast, and highly configurable web crawler module for Project Eidolon.

## Features

- **Asynchronous Architecture**: Built with `asyncio` and `httpx` for high-performance concurrent crawling
- **Configurable Concurrency**: Control the number of simultaneous requests
- **Comprehensive Error Handling**: Built-in retry logic, timeout management, and error reporting
- **Detailed Reporting**: Automatic generation of crawl statistics and performance metrics
- **Resource Efficient**: Optimized for minimal memory footprint while maintaining high throughput

## Integration with Aethon Workflow

This module is designed to work seamlessly with other Aethon modules:

1. Takes input from `aethon_urlclean` module, which provides sanitized URLs
2. Outputs structured crawl data that can be consumed by other data processing modules
3. Generates detailed console reports after each crawl operation

## Configuration Options

The crawler is highly configurable through the `module.yaml` file:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `concurrency` | int | 10 | Maximum number of concurrent requests |
| `timeout` | int | 30 | Request timeout in seconds |
| `user_agent` | str | "Eidolon/1.0 Web Crawler" | User agent string for requests |
| `follow_redirects` | bool | True | Whether to follow redirects automatically |
| `max_redirects` | int | 5 | Maximum number of redirects to follow |
| `retry_count` | int | 3 | Number of retry attempts for failed requests |
| `retry_delay` | int | 1 | Delay between retries in seconds |
| `verify_ssl` | bool | True | Whether to verify SSL certificates |

## Input/Output

### Input
- **urls**: List of strings, each containing a valid URL to crawl
  - Source: Typically from `aethon_urlclean.cleaned_urls`

### Output
- **crawled_data**: List of dictionaries, each containing:
  - `url`: The crawled URL
  - `timestamp`: Unix timestamp of when the request was made
  - `success`: Boolean indicating if the request was successful
  - `status_code`: HTTP status code
  - `headers`: Response headers
  - `content_length`: Size of the response in bytes
  - `content_type`: Content-Type header value
  - `elapsed`: Time taken to complete the request in seconds
  - `text`: First 10,000 characters of response text (for successful requests)
  - `error`: Error message (if any)

## Custom Commands

The module supports the following custom commands:

- **report**: Regenerates and displays the crawl report
- **clear**: Clears the current URL list and results

## Usage Example

The module is typically used as part of an Aethon pipeline, but can also be tested independently:

```python
from core.modules.engine import ModuleEngine
import logging
import asyncio

# Setup logger
logger = logging.getLogger("test")
logger.setLevel(logging.INFO)

# Create engine instance
engine = ModuleEngine(logger)

# Discover and load the crawler module
engine.discover_modules(["/path/to/modules"])
crawler = engine.load_module("aethon_crawler")

# Test URLs
test_urls = [
    "https://example.com",
    "https://httpbin.org/status/404",
    "https://httpbin.org/delay/1"
]

# Handle the input manually for testing
crawler.handle_input(test_urls)

# Run the crawler (normally handled by the engine)
asyncio.run(crawler.run(engine.message_bus))
```

## Performance Considerations

- For optimal performance, adjust `concurrency` based on your system capabilities
- Large URL lists are efficiently processed in batches
- Memory usage scales linearly with the number of URLs processed
- Consider setting lower timeouts for time-sensitive operations

## Error Handling

The crawler has comprehensive error handling:

- Invalid URLs are detected before making requests
- Connection issues are retried automatically
- SSL errors are logged with detailed information
- All errors are included in the final report
=======
# Aethon Web Crawler

Aethon is a lightweight, high-performance web crawler designed for flexibility and efficient operation within the Eidolon ecosystem. It provides basic web crawling functionality with performance optimizations and console-based reporting.

## Features

- **High Performance**: Multi-threaded, asynchronous crawling with intelligent thread management
- **Core Data Extraction**:
  - URLs (in-scope & out-of-scope)
  - Emails and social media accounts
  - JavaScript files & endpoints
  - Parameters in URLs
  - Subdomains (when DNS option is enabled)
- **Console Reporting**: Clean summary output directly to the console
- **Flexible Configuration**: Control timeout, delay, seeds, exclude URLs, and more
- **Performance Optimized**: Smart resource management with configurable thread limits

## Integration with Eidolon

Aethon is designed to work seamlessly within the Eidolon ecosystem:

- **Message Bus Communication**: Subscribe to Aethon's outputs to use crawled data in your modules
- **Pipeline Integration**: Easily incorporate Aethon in your data processing pipelines
- **Configuration via Pipeline**: Configure Aethon through pipeline definitions

## Usage

### Basic Configuration

```yaml
modules:
  - name: aethon_crawler
    id: crawler
    config:
      url: "https://example.com"
      level: 2
      threads: 10
      delay: 0.5
      timeout: 10
      exclude: "logout|sign-out"
```

### Available Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| url | Root URL to crawl | Required |
| level | Depth levels to crawl | 2 |
| threads | Number of threads | 10 |
| delay | Delay between requests (seconds) | 0 |
| timeout | HTTP request timeout (seconds) | 10 |
| exclude | URLs to exclude (regex pattern) | None |
| seeds | Additional seed URLs | [] |
| dns | Enumerate subdomains | False |
| wayback | Use archive.org for seeds | False |

### Subscribing to Aethon Outputs

Other modules can subscribe to Aethon's outputs in their pipeline configuration:

```yaml
modules:
  - name: your_module
    id: processor
    depends_on:
      - crawler
    input:
      website_data: crawler.extracted_data
```

## API Reference

### Inputs

- **crawl_config**: Dictionary with crawling configuration
- **additional_seeds**: List of additional seed URLs to crawl

### Outputs

- **crawled_urls**: List of all crawled URLs
- **extracted_data**: Dictionary of all extracted data
- **crawl_status**: Status updates about the crawl

## Performance Considerations

- Higher thread counts improve speed but may increase server load
- Use appropriate delays when crawling production websites
- Set reasonable `timeout` values to avoid hanging on slow resources