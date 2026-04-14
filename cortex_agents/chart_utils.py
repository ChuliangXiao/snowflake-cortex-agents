"""Utility functions for plotting Cortex Agent charts.

The agent can generate Vega-Lite chart specifications, which can be
rendered using Altair (Python wrapper for Vega-Lite).

Note: Altair is an optional dependency. Install with: pip install altair pandas
"""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import altair as alt

logger = logging.getLogger(__name__)


def plot_charts(
    charts: list[dict[str, Any]],
    interactive: bool = True,
    max_width: int = 900,
    max_height: int = 450,
    display_now: bool = True,
) -> list | None:
    """Plot charts from agent response using Altair.

    Args:
        charts: List of chart dicts from response.get_charts()
        interactive: Enable interactive Altair features (default: True)
        max_width: Maximum chart width in pixels (default: 900)
        max_height: Maximum chart height in pixels (default: 600)
        display_now: Auto-display in Jupyter (default: True)

    Returns:
        List of Altair Chart objects (or None if Altair not installed)

    Raises:
        ImportError: If Altair is not installed
        ValueError: If charts list is empty or malformed

    Examples:
    ```python
    response = agent.run("Show dual eligible trend", agent_name="MY_AGENT", database="MY_DB", schema="MY_SCHEMA")
    charts = response.get_charts()

    if charts:
        plot_charts(charts)
    ```
    """
    try:
        import altair as alt
    except ImportError as e:
        raise ImportError("Altair is required for chart plotting. Install it with: pip install altair pandas") from e

    if not charts:
        raise ValueError("No charts provided")

    chart_objects = []

    for i, chart_dict in enumerate(charts):
        try:
            # Extract Vega-Lite spec
            spec_str = chart_dict.get("chart_spec")
            if not spec_str:
                logger.warning(f"Chart {i + 1}: No chart_spec found")
                continue

            # Parse JSON spec
            spec = json.loads(spec_str)

            # Create Altair chart from Vega-Lite spec
            chart = alt.Chart.from_dict(spec)

            # Configure size
            chart = chart.properties(width=max_width, height=max_height)

            # Enable interactivity if requested
            if interactive:
                chart = chart.interactive()

            chart_objects.append(chart)

            logger.info(f"Chart {i + 1}: {spec.get('title', 'Untitled')} (rendered)")

            # Auto-display in Jupyter if requested
            if display_now:
                try:
                    from IPython.display import display

                    display(chart)
                except ImportError:
                    pass  # Not in Jupyter

        except json.JSONDecodeError as e:
            logger.error(f"Chart {i + 1}: Failed to parse chart_spec JSON: {e}")
        except Exception as e:
            logger.error(f"Chart {i + 1}: Error rendering chart: {e}")

    return chart_objects if chart_objects else None


def plot_chart_dict(
    chart_spec: dict[str, Any],
    interactive: bool = True,
    max_width: int = 900,
    max_height: int = 600,
) -> "alt.Chart":
    """Plot a single chart from a Vega-Lite specification dict.

    Args:
        chart_spec: Vega-Lite specification dict
        interactive: Enable interactive features (default: True)
        max_width: Maximum chart width in pixels
        max_height: Maximum chart height in pixels

    Returns:
        Altair Chart object

    Raises:
        ImportError: If Altair is not installed

    Examples:
    ```python

            spec = {
                "mark": "line",
                "encoding": {
                    "x": {"field": "month", "type": "temporal"},
                    "y": {"field": "value", "type": "quantitative"}
                },
                "data": {"values": [...]}
            }
            plot_chart_dict(spec)
            To use it in Streamlit:
            ::

            chart_objects = plot_charts(charts, interactive=True)
                for i, chart in enumerate(chart_objects):
                    st.vega_lite_chart(json.loads(chart.to_json()), width='stretch')
    ```
    """
    try:
        import altair as alt
    except ImportError as e:
        raise ImportError("Altair is required for chart plotting. Install it with: pip install altair pandas") from e

    chart = alt.Chart.from_dict(chart_spec)

    chart = chart.properties(width=max_width, height=max_height)

    if interactive:
        chart = chart.interactive()

    return chart


def extract_chart_specs(charts: list[dict[str, Any]]) -> list[dict]:
    """Extract parsed Vega-Lite specs from chart dicts.

    Args:
        charts: List of chart dicts from response.get_charts()

    Returns:
        List of parsed Vega-Lite specification dicts

    Examples:
    ```python

            charts = response.get_charts()
            specs = extract_chart_specs(charts)
            for spec in specs:
                print(spec["title"])
    ```
    """
    specs = []

    for chart in charts:
        try:
            spec_str = chart.get("chart_spec")
            if spec_str:
                spec = json.loads(spec_str)
                specs.append(spec)
        except json.JSONDecodeError:
            pass

    return specs


def get_chart_info(charts: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Get metadata about charts without rendering.

    Args:
        charts: List of chart dicts from response.get_charts()

    Returns:
        List of dicts with chart info (title, mark, fields)

    Examples:
    ```python

            charts = response.get_charts()
            info = get_chart_info(charts)

            for chart_info in info:
                print(f"Title: {chart_info['title']}")
                print(f"Type: {chart_info['mark']}")
                print(f"Fields: {chart_info['fields']}")
    ```
    """
    info_list = []

    for i, chart in enumerate(charts):
        try:
            spec_str = chart.get("chart_spec")
            if not spec_str:
                continue

            spec = json.loads(spec_str)

            # Extract fields from encoding
            fields = set()
            if "encoding" in spec:
                for _encoding, config in spec["encoding"].items():
                    if "field" in config:
                        fields.add(config["field"])

            info = {
                "index": i,
                "title": spec.get("title", "Untitled"),
                "mark": spec.get("mark", "unknown"),
                "fields": sorted(fields),
                "num_data_points": len(spec.get("data", {}).get("values", [])),
            }
            info_list.append(info)

        except (json.JSONDecodeError, KeyError):
            pass

    return info_list


def chart_to_json(chart_spec: dict[str, Any], pretty: bool = True) -> str:
    """Convert chart spec to JSON string.

    Args:
        chart_spec: Vega-Lite specification dict
        pretty: Pretty-print JSON (default: True)

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(chart_spec, indent=2)
    else:
        return json.dumps(chart_spec)
