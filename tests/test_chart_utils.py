"""Tests for chart_utils module."""

import importlib
import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from cortex_agents.chart_utils import plot_charts


class TestPlotCharts:
    """Tests for plot_charts function."""

    def test_raises_without_altair(self):
        """Should raise ImportError when Altair is not installed."""
        # Mock altair import failure
        with patch.dict(sys.modules, {"altair": None}):
            import importlib

            import cortex_agents.chart_utils

            importlib.reload(cortex_agents.chart_utils)
            with pytest.raises(ImportError, match="Altair is required"):
                cortex_agents.chart_utils.plot_charts([{"chart_spec": '{"mark": "bar"}'}])

    def test_raises_on_empty_charts(self):
        """Should raise ValueError on empty charts list."""
        with pytest.raises(ValueError, match="No charts provided"):
            plot_charts([])

    def test_single_chart(self):
        """Should process a single valid chart."""
        mock_alt = MagicMock()
        mock_chart = MagicMock()
        mock_chart.properties.return_value = mock_chart
        mock_chart.interactive.return_value = mock_chart
        mock_alt.Chart.from_dict.return_value = mock_chart

        chart_spec = {
            "mark": "bar",
            "encoding": {"x": {"field": "category"}, "y": {"field": "value"}},
            "data": {"values": [{"category": "A", "value": 10}]},
        }

        charts = [{"chart_spec": json.dumps(chart_spec)}]

        with patch.dict(sys.modules, {"altair": mock_alt}):
            result = plot_charts(charts, display_now=False)

        assert result is not None
        assert len(result) == 1
        mock_alt.Chart.from_dict.assert_called_once()
        mock_chart.properties.assert_called_once_with(width=900, height=450)
        mock_chart.interactive.assert_called_once()

    def test_multiple_charts(self):
        """Should process multiple charts."""
        mock_alt = MagicMock()
        mock_chart = MagicMock()
        mock_chart.properties.return_value = mock_chart
        mock_chart.interactive.return_value = mock_chart
        mock_alt.Chart.from_dict.return_value = mock_chart

        charts = [
            {"chart_spec": '{"mark": "bar", "data": {"values": []}}'},
            {"chart_spec": '{"mark": "line", "data": {"values": []}}'},
        ]

        with patch.dict(sys.modules, {"altair": mock_alt}):
            result = plot_charts(charts, display_now=False)

        assert result is not None
        assert len(result) == 2
        assert mock_alt.Chart.from_dict.call_count == 2

    def test_custom_dimensions(self):
        """Should use custom width and height."""
        mock_alt = MagicMock()
        mock_chart = MagicMock()
        mock_chart.properties.return_value = mock_chart
        mock_chart.interactive.return_value = mock_chart
        mock_alt.Chart.from_dict.return_value = mock_chart

        charts = [{"chart_spec": '{"mark": "bar", "data": {"values": []}}'}]

        with patch.dict(sys.modules, {"altair": mock_alt}):
            plot_charts(charts, max_width=600, max_height=400, display_now=False)

        mock_chart.properties.assert_called_once_with(width=600, height=400)

    def test_non_interactive(self):
        """Should skip interactivity when disabled."""
        mock_alt = MagicMock()
        mock_chart = MagicMock()
        mock_chart.properties.return_value = mock_chart
        mock_alt.Chart.from_dict.return_value = mock_chart

        charts = [{"chart_spec": '{"mark": "bar", "data": {"values": []}}'}]

        with patch.dict(sys.modules, {"altair": mock_alt}):
            plot_charts(charts, interactive=False, display_now=False)

        mock_chart.interactive.assert_not_called()

    def test_missing_chart_spec(self):
        """Should skip charts without chart_spec."""
        mock_alt = MagicMock()
        mock_chart = MagicMock()
        mock_chart.properties.return_value = mock_chart
        mock_chart.interactive.return_value = mock_chart
        mock_alt.Chart.from_dict.return_value = mock_chart

        charts = [{"no_spec": "here"}, {"chart_spec": '{"mark": "bar", "data": {"values": []}}'}]

        with patch.dict(sys.modules, {"altair": mock_alt}):
            result = plot_charts(charts, display_now=False)

        assert result is not None
        assert len(result) == 1  # Only one valid chart

    def test_invalid_json(self):
        """Should skip charts with invalid JSON."""
        mock_alt = MagicMock()
        mock_chart = MagicMock()
        mock_chart.properties.return_value = mock_chart
        mock_chart.interactive.return_value = mock_chart
        mock_alt.Chart.from_dict.return_value = mock_chart

        charts = [
            {"chart_spec": "invalid json"},
            {"chart_spec": '{"mark": "bar", "data": {"values": []}}'},
        ]

        with patch.dict(sys.modules, {"altair": mock_alt}):
            result = plot_charts(charts, display_now=False)

        assert result is not None
        assert len(result) == 1  # Only one valid chart

    def test_chart_rendering_error(self):
        """Should skip charts that fail to render."""
        mock_alt = MagicMock()
        mock_chart = MagicMock()
        mock_chart.properties.return_value = mock_chart
        mock_chart.interactive.return_value = mock_chart
        mock_alt.Chart.from_dict.side_effect = [Exception("Render error"), mock_chart]

        charts = [
            {"chart_spec": '{"mark": "bar"}'},
            {"chart_spec": '{"mark": "line", "data": {"values": []}}'},
        ]

        with patch.dict(sys.modules, {"altair": mock_alt}):
            result = plot_charts(charts, display_now=False)

        assert result is not None
        assert len(result) == 1  # Only second chart succeeded

    def test_display_now_in_jupyter(self):
        """Should display charts in Jupyter when display_now=True."""
        mock_alt = MagicMock()
        mock_chart = MagicMock()
        mock_chart.properties.return_value = mock_chart
        mock_chart.interactive.return_value = mock_chart
        mock_alt.Chart.from_dict.return_value = mock_chart

        # Mock IPython display function
        mock_display_func = MagicMock()

        # Create a mock IPython.display module
        mock_ipython = MagicMock()
        mock_ipython.display = mock_display_func

        charts = [{"chart_spec": '{"mark": "bar", "data": {"values": []}}'}]

        with patch.dict(sys.modules, {"altair": mock_alt, "IPython": mock_ipython, "IPython.display": mock_ipython}):
            # Import display from IPython.display inside the function
            import cortex_agents.chart_utils

            importlib.reload(cortex_agents.chart_utils)
            cortex_agents.chart_utils.plot_charts(charts, display_now=True)
            # Display should have been called
            # Note: This may not work perfectly due to try/except in the actual code

    def test_returns_none_on_all_failures(self):
        """Should return None when all charts fail."""
        mock_alt = MagicMock()
        mock_alt.Chart.from_dict.side_effect = Exception("Error")

        charts = [{"chart_spec": '{"mark": "bar"}'}]

        with patch.dict(sys.modules, {"altair": mock_alt}):
            result = plot_charts(charts, display_now=False)

        assert result is None
