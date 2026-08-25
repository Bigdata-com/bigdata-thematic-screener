
# Bigdata Thematic Screener Service
This repository contains a Python package and Docker image for running a thematic screener service on top of the Bigdata.com REST API. The service analyzes corporate exposure to specific themes and events, quantifying the impact for each company in your universe. See our [docs](https://docs.bigdata.com/use-cases/docker-services/thematic-screener) for more details.

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

Add `-e FMP_API_KEY=<fmp-api-key-here>` if you want the optional ETF tab (see [ETF tab](#etf-tab-optional)).

2. **Run directly from GitHub Container Registry:**

```bash
docker run -d \
  --name bigdata_thematic_screener \
  -p 8000:8000 \
  -e BIGDATA_API_KEY=<bigdata-api-key-here> \
  -e OPENAI_API_KEY=<openai-api-key-here> \
  ghcr.io/bigdata-com/bigdata_thematic_screener:latest
```

Add `-e FMP_API_KEY=<fmp-api-key-here>` for the optional ETF tab ([details below](#etf-tab-optional)).

This will start the thematic screener service locally on port 8000. You can then access the service @ `http://localhost:8000/` and the documentation for the API @ `http://localhost:8000/docs`.

For a custom enterprise-ready solution, please contact us at [support@bigdata.com](mailto:support@bigdata.com)


## Security Measures

We perform a pre-release security scan on our container images to detect vulnerabilities in all components.


## How to screen a set of companies?

A thematic screener report provides an executive summary of financially relevant information about a set of companies in your universe. You can generate a report either using the UI or programmatically, allowing you to build custom workflows on top of this service.

The company universe is provided either as a list of RavenPack (RP) entity IDs, or as an uploaded CSV. **Watchlists (watchlist IDs) are not supported.**

### Using the UI
There is a simple UI available @ `http://localhost:8000/` where you can set your parameters and receive an easy-to-read summary of the thematic screening results.

### ETF tab (optional)
After a thematic report is available (the run produced **theme scoring** for your company basket), open the **ETFs** tab to explore funds whose holdings overlap that basket. The tab ranks ETFs by estimated thematic weight in the basket and includes an in-app **How it works** explanation of the methodology.

**Data source and `FMP_API_KEY`:** ETF and holdings data come from [Financial Modeling Prep](https://financialmodelingprep.com/) (FMP). Set the environment variable **`FMP_API_KEY`** to your FMP API key. The service calls FMP **only from the server**; the key is never exposed to the browser. If `FMP_API_KEY` is unset or empty, the tab still appears but live ETF lookup is disabled and the UI states that the server must be configured.

**Controls:** You can choose how many basket names to use, how many ETFs to list, optionally add extra tickers (merge or replace the basket list), and optionally score specific **focus** ETFs via holdings-based analysis.

### Programmatically

The thematic screener API works asynchronously. You first submit a request to start the analysis, then check the status periodically until completion.

#### Step 1: Submit a Thematic Screener Request

**Option A — a list of RP entity IDs**, via `POST /thematic-screener`:

```bash
curl -X 'POST' \
  'http://localhost:8000/thematic-screener' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "theme": "Supply Chain Reshaping",
    "focus": "Logistics",
    "companies": ["D8442A", "228D42", "4A6F00"],
    "start_date": "2024-01-01",
    "end_date": "2025-08-26",
    "chunk_percentage": 0.05,
    "max_leaf_labels": 15
  }'
```

**Option B — a universe CSV**, via `POST /thematic-screener/upload` (multipart, same fields minus `companies`, sent as a JSON string in the `request` form field). The CSV needs `RP_ENTITY_ID` (alias `RP_COMPANY_ID`) and `COMPANY_NAME` columns; `TICKER`/`SECTOR`/`INDUSTRY`/`COUNTRY` are optional enrichment columns:

```bash
curl -X 'POST' \
  'http://localhost:8000/thematic-screener/upload' \
  -H 'accept: application/json' \
  -F 'file=@Internal/mag7.csv;type=text/csv' \
  -F 'request={"theme": "AI Adoption and Monetization", "focus": "How major tech companies are monetizing AI products and services.", "start_date": "2024-01-01", "end_date": "2025-08-26"};type=application/json'
```

Both endpoints return a response like:
```json
{
  "request_id": "12345678-1234-1234-1234-123456789abc",
  "status": "queued"
}
```

#### Step 2: Check status and retrieve results
Use the `request_id` from the previous step to check the status and retrieve the results:
```bash
curl -X 'GET' \
  'http://localhost:8000/status/12345678-1234-1234-1234-123456789abc' \
  -H 'accept: application/json'
```

The response will include:
- `status`: One of "queued", "in_progress", "completed", or "failed"
- `logs`: Progress messages from the analysis
- `report`: The complete thematic screening results (only when status is "completed")

For more details on the parameters, refer to the API documentation @ `http://localhost:8000/docs`.

## Demo Mode
The Thematic Screener supports a **Demo Mode** that allows users to explore pre-computed examples without the ability to run custom analyses. This is perfect for public demonstrations, sales presentations, or training environments where you want to showcase the service capabilities without incurring API costs or requiring credentials.

When Demo Mode is enabled, users can access all visualizations (heatmaps, company cards, mindmaps, and evidence tables) using pre-loaded sample data for Supply Chain, AI & Automation, and Climate Tech themes. However, the "Run Analysis" button is disabled, preventing new custom analyses. Demo mode is a **frontend-only restriction**.

To enable Demo Mode, set the `DEMO_MODE` environment variable:

```bash
docker run -d \
  --name bigdata_thematic_screener \
  -p 8000:8000 \
  -e DEMO_MODE=true \
  ghcr.io/bigdata-com/bigdata_thematic_screener:latest
```


# Install and for development locally
```bash
uv sync --dev
```

Copy [`.env.example`](.env.example) to `.env` and set your keys (never commit `.env`). Alternatively, export variables in your shell.

To run the service, you need an API key from Bigdata.com set on the environment variable `BIGDATA_API_KEY` and additionally provide an API key from a supported LLM provider, for now OpenAI.

Optional **`FMP_API_KEY`:** enables the [ETF tab](#etf-tab-optional); used only on the server when calling FMP (see that section).

Optional **`ACCESS_TOKEN`:** if you set this to a non-empty string, the app requires the same value as the **`token` query parameter** on protected API routes and on the main UI URL (for example `http://localhost:8000/?token=your-secret`). If it is **not** set (the default), no `token` parameter is required. This is a simple shared-secret gate, not full user authentication.

```bash
# Set environment variables
export BIGDATA_API_KEY=<bigdata-api-key-here>
export OPENAI_API_KEY=<openai-api-key-here>
# Optional — ETF tab (FMP):
# export FMP_API_KEY=<fmp-api-key-here>
# Optional — require ?token=... on API + UI:
# export ACCESS_TOKEN=<your-chosen-secret>
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
