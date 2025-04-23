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
| `raw_content_length` | int | 10000 | Maximum number of characters to store from response text |

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
  - `text`: First N characters of response text (for successful requests), controlled by `raw_content_length`
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