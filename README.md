# Project Eidolon

A system for monitoring online discourse, detecting bot behavior, and analyzing misinformation patterns across social media platforms.

## Overview

Project Eidolon passively observes public online discourse on political topics, uses various detection algorithms to identify suspected bot behavior, and logs patterns of influence, misinformation tactics, sentiment evolution, and possible coordinated campaigns.

## Features

- Multi-platform social media monitoring (Twitter/X, Reddit, Facebook)
- Bot detection algorithms 
- Data collection and storage
- CLI and API interfaces
- Cross-platform compatibility (Windows, Linux, ARM, x86)

## Setup

### Requirements

- Python 3.10+
- API keys for social media platforms

### Installation

1. Clone the repository
```bash
git clone [repository-url]
cd project-eidolon
```

2. Create and activate a virtual environment (recommended)
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages
```bash
pip install -r requirements.txt
```

4. Set up environment variables by copying the template
```bash
cp .env.example .env
```

5. Edit the `.env` file with your API credentials

### Docker Setup

You can also run the application using Docker:

```bash
# Build the Docker image
docker build -f docker/full_build.Dockerfile -t eidolon .

# Run the container in CLI mode
docker run -it --env-file .env eidolon python main.py

# Run the container in API mode
docker run -p 8000:8000 --env-file .env eidolon python main.py --mode api
```

## Usage

### CLI Interface

```bash
# Test API connectivity
python main.py test

# Search Twitter for a query
python main.py twitter "climate change" --count 50

# Search Reddit in a specific subreddit
python main.py reddit politics --query "election" --count 30 --sort hot
```

### API Interface

Start the API server:
```bash
python main.py --mode api
```

The API will be available at `http://localhost:8000` with the following endpoints:
- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /twitter/search` - Search Twitter
- `POST /reddit/search` - Search Reddit

## Development

### Project Structure

- `core/` - Core functionality and algorithms
- `ingest/` - Data ingestion from social media platforms
- `interface/` - CLI and API interfaces
- `data/` - Stored data (automatically created)
- `tests/` - Unit and integration tests

### Running Tests

```bash
pytest
```

## License

[License information]