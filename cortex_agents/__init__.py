"""Snowflake Cortex SDK

Simplified, ergonomic SDK for working with Snowflake's Cortex features:
- Cortex Agents: Agentic workflows with tools and orchestration
- Cortex Analyst: SQL generation from natural language

Example (Agents):
    ```python
    from cortex_agents import CortexAgent

    agent = CortexAgent()

    # Create an agent
    agent.create_agent(
        name="MY_AGENT",
        config={
            "instructions": {"system": "You are helpful"},
            "models": {"orchestration": "claude-sonnet-4-6"},
        },
        database="MY_DB",
        schema="MY_SCHEMA",
    )

    # Run the agent
    response = agent.run("What's the revenue?", agent_name="MY_AGENT", database="MY_DB", schema="MY_SCHEMA")
    print(response.text)
    print(response.sql)
    ```

Example (Analyst):
    ```python
    from cortex_agents import CortexAnalyst

    # Initialize
    analyst = CortexAnalyst()

    # Generate SQL from natural language
    response = analyst.message(
        "Which company had most revenue?",
        semantic_model_file="@my_stage/model.yaml"
    )
    print(response.text)  # Interpretation
    print(response.sql)   # Generated SQL
    ```
"""

from .agent import CortexAgent
from .analyst import CortexAnalyst
from .async_agent import AsyncCortexAgent
from .async_analyst import AsyncCortexAnalyst
from .base import SnowflakeAPIError
from .chart_utils import plot_charts
from .core.response import AgentResponse, EventType
from .core.run import AgentInlineConfig
from .utils import load_credentials, validate_account_url

__version__ = "0.1.0"
__all__ = [
    # Sync Agent classes
    "CortexAgent",
    "CortexAnalyst",
    # Async Agent classes
    "AsyncCortexAgent",
    "AsyncCortexAnalyst",
    # Response wrappers
    "AgentResponse",
    # Supporting types
    "AgentInlineConfig",
    "EventType",
    "SnowflakeAPIError",
    # Utilities
    "plot_charts",
    "load_credentials",
    "validate_account_url",
]
