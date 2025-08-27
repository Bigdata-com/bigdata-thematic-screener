
# Bigdata Thematic Screener Service
This repository contains a Python package and Docker image for running a thematic screener service using Bigdata.com SDK. The service analyzes corporate exposure to specific themes and events, quantifying the impact for each company in your universe. See our [docs](https://docs.bigdata.com/use-cases/docker-services/thematic-screener) for more details.

# What does it do?
The thematic screener service allows you to analyze and quantify how companies are exposed to a given theme (e.g., supply chain reshaping, AI adoption, geopolitical events). It screens your trading universe and provides a detailed breakdown of theme scores, labeled content, and taxonomy.

## Prerequisites
- A [Bigdata.com](https://bigdata.com) account that supports programmatic access.
- A Bigdata.com API key, which can be obtained from your account settings.
    - For more information on how to get an API key, refer to the [Bigdata.com documentation](https://docs.bigdata.com/api-reference/introduction#api-key-beta).

# Quickstart
To quickly get started, you have two options:

1. **Build and run locally:**
You need to build the docker image first and then run it:

```bash
# Clone the repository and navigate to the folder
git clone git@github.com:Bigdata-com/bigdata-thematic-screener.git
cd "bigdata-thematic-screener"

# Build the docker image
docker build -t bigdata_thematic_screener .

# Run the docker image
docker run -d \
  --name bigdata_thematic_screener \
  -p 8000:8000 \
  -e BIGDATA_API_KEY=<bigdata-api-key-here> \
  -e OPENAI_API_KEY=<openai-api-key-here> \
  bigdata_thematic_screener
```

2. **Run directly from GitHub Container Registry:**

```bash
docker run -d \
  --name bigdata_thematic_screener \
  -p 8000:8000 \
  -e BIGDATA_API_KEY=<bigdata-api-key-here> \
  -e OPENAI_API_KEY=<openai-api-key-here> \
  ghcr.io/bigdata-com/bigdata_thematic_screener:latest
```

This will start the thematic screener service locally on port 8000. You can then access the service @ `http://localhost:8000/` and the documentation for the API @ `http://localhost:8000/docs`.

For a custom enterprise-ready solution, please contact us at [support@bigdata.com](mailto:support@bigdata.com)


## Security Measures

We perform a pre-release security scan on our container images to detect vulnerabilities in all components.



## How to screen a set of companies?

A thematic screener report provides an executive summary of financially relevant information about a set of companies that form your watchlist. You can generate a report either using the UI or programmatically, allowing you to build custom workflows on top of this service.

### Using the UI
There is a simple UI available @ `http://localhost:8000/` where you can set your parameters and receive an easy-to-read summary of the thematic screening results.

### Programmatically

You can generate a report for a universe of companies by sending a POST request to the `/thematic-screener` endpoint with the required parameters. For example, using `curl`:
```bash
curl -X 'POST' \
  'http://localhost:8000/thematic-screener' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "theme": "Supply Chain Reshaping",
    "focus": "Logistics",
    "companies": "44118802-9104-4265-b97a-2e6d88d74893",
    "start_date": "2024-01-01",
    "end_date": "2025-08-26",
    "fiscal_year": 2024,
    "document_type": "TRANSCRIPTS",
    "frequency": "M"
  }'
```

For more details on the parameters, refer to the API documentation @ `http://localhost:8000/docs`.

# Install and for development locally
```bash
uv sync --dev
```

To run the service, you need an API key from Bigdata.com set on the environment variable `BIGDATA_API_KEY` and additionally provide an API key from a supported LLM provider, for now OpenAI.
```bash
# Set environment variables
export BIGDATA_API_KEY=<bigdata-api-key-here>
export OPENAI_API_KEY=<openai-api-key-here>
```

Then, the following command will start the thematic screener service locally on port 8000.
```bash
uv run -m bigdata_thematic_screener
```

## Tooling
This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting and [ty](https://docs.astral.sh/ty/) for a type checker. To ensure your code adheres to the project's style guidelines, run the following commands before committing your changes:
```bash
make type-check
make lint
make format
```
