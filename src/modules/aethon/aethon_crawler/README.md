# Aethon Web Crawler

Aethon is a modern, high-performance web crawler designed for flexibility and efficient operation within the Eidolon ecosystem. Inspired by the [Photon](https://github.com/s0md3v/Photon) project, Aethon brings improved architecture, performance optimizations, and seamless integration with other Eidolon modules.

## Features

- **High Performance**: Multi-threaded, asynchronous crawling with intelligent thread management
- **Rich Data Extraction**:
  - URLs (in-scope & out-of-scope)
  - URLs with parameters (example.com/gallery.php?id=2)
  - Intel (emails, social media accounts, Amazon buckets, etc.)
  - Files (pdf, png, xml, etc.)
  - Secret keys (auth/API keys & hashes)
  - JavaScript files & endpoints
  - Strings matching custom regex patterns
  - Subdomains & DNS related data
- **Flexible Configuration**: Control timeout, delay, add seeds, exclude URLs, and more
- **Smart Resource Management**: Optimized crawling with configurable resource limits
- **Wayback Integration**: Fetch archived URLs from archive.org to use as seeds
- **Progress Reporting**: Real-time status updates through the message bus

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
      only_urls: false
      exclude: "logout|sign-out"
```

### Available Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| url | Root URL to crawl | Required |
| level | Depth levels to crawl | 2 |
| threads | Number of threads | 10 |
| delay | Delay between requests (seconds) | 0 |
| cookie | Cookie string | None |
| regex | Custom regex pattern for extraction | None |
| timeout | HTTP request timeout (seconds) | 10 |
| exclude | URLs to exclude (regex pattern) | None |
| user_agent | Custom User-Agent | Random modern browser |
| only_urls | Only extract URLs | False |
| wayback | Use URLs from archive.org as seeds | False |
| headers | Custom HTTP headers | None |
| dns | Enumerate subdomains & DNS data | False |
| ninja | Use stealth request techniques | False |
| clone | Clone the website locally | False |

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
- **parameters**: URLs with parameters
- **intel**: Extracted intelligence items
- **secret_keys**: Extracted API keys and secrets
- **js_files**: JavaScript files and endpoints
- **subdomains**: Discovered subdomains
- **crawl_status**: Status updates about the crawl

## Examples

### Website Mapping

```yaml
modules:
  - name: aethon_crawler
    id: mapper
    config:
      url: "https://example.com"
      level: 3
      only_urls: true
```

### Intelligence Gathering

```yaml
modules:
  - name: aethon_crawler
    id: intel_gatherer
    config:
      url: "https://example.com"
      level: 2
      dns: true
      ninja: true
```

### API Endpoint Discovery

```yaml
modules:
  - name: aethon_crawler
    id: api_discoverer
    config:
      url: "https://example.com"
      level: 2
      regex: "api/v[0-9]+"
```

## Performance Considerations

- Higher thread counts improve speed but may increase server load
- Use appropriate delays when crawling production websites
- The `wayback` option can help discover content without hitting the target server
- Set reasonable `timeout` values to avoid hanging on slow resources