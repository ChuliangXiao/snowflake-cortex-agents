# Installation

## System Requirements

- Python 3.10 or higher
- pip (Python package manager)

## Basic Installation

Install the package from PyPI:

```bash
pip install snowflake-cortex-agents
```

## Installation with Optional Dependencies

The SDK has optional dependencies for additional features:

**For chart plotting and visualization:**

```bash
pip install snowflake-cortex-agents[charts]
```

This installs Altair and Pandas for rendering Vega-Lite charts.

**For environment variable management:**

```bash
pip install snowflake-cortex-agents[dotenv]
```

This installs python-dotenv for `.env` file support.

**For all optional dependencies:**

```bash
pip install snowflake-cortex-agents[all]
```

## Configuration

Before using the SDK, you need to set up your Snowflake credentials.

### Environment Variables

Set these environment variables:

```bash
export SNOWFLAKE_ACCOUNT_URL="https://your-account.snowflakecomputing.com"
export SNOWFLAKE_PAT="your-personal-access-token"
```

### Using .env File

Create a `.env` file in your project root. If you're working from this repository, you can copy `.env.example` to `.env` first:

```ini
SNOWFLAKE_ACCOUNT_URL=https://your-account.snowflakecomputing.com
SNOWFLAKE_PAT=your-personal-access-token
```

### Direct Parameters

Pass credentials directly to the client:

```python
from cortex_agents import CortexAgent, load_credentials

agent = CortexAgent()
# Credentials are loaded from environment or .env file

# Or explicitly:
url, pat = load_credentials(
    account_url="https://your-account.snowflakecomputing.com",
    pat="your-personal-access-token"
)
```

### Key-Pair JWT Authentication

If your Snowflake account uses key-pair authentication instead of a PAT, pass the JWT and set `token_type="KEYPAIR_JWT"`:

```python
from cortex_agents import CortexAgent

agent = CortexAgent(
    account_url="https://your-account.snowflakecomputing.com",
    pat="your-keypair-jwt-token",
    token_type="KEYPAIR_JWT",
)
```

This adds the `X-Snowflake-Authorization-Token-Type: KEYPAIR_JWT` header to all requests.

## Getting Your Credentials

1. **Snowflake Account URL**: Found in your Snowflake account settings
2. **Personal Access Token (PAT)**: Generate from Snowflake web UI
   - Login to Snowflake
   - Go to Admin → Users & Roles
   - Select your user
   - Click "Security" tab
   - Generate a new authentication token

## Troubleshooting

**ImportError: No module named 'cortex_agents'**

Make sure you've installed the package:

```bash
pip install snowflake-cortex-agents
```

**Missing credentials error**

Ensure your environment variables are set:

```bash
echo $SNOWFLAKE_ACCOUNT_URL
echo $SNOWFLAKE_PAT
```

**Connection refused**

Verify your account URL is correct and your PAT is still valid.

## Next Steps

- Check out the [Quick Start](quickstart.md) guide
- Explore [Examples](guides/agents.md) and use cases
- Read the [API Reference](api/agent.md) for detailed API documentation
