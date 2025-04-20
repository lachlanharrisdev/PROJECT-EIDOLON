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