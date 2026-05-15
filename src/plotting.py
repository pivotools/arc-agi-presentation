"""
Plotly helpers for ARC puzzle display and baseline-vs-interleaved figures.

Used by blog posts to show puzzle-with-code figures and publication-style
scatter/bar figures. Style (colors, shapes) from blog/style/style.yml only.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from IPython.display import HTML, display
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

ShowTestArg = bool | Literal["only"]

# ---------------------------------------------------------------------------
# ARC color palette (loaded from style.yml or fallback to original ARC scheme)
# ---------------------------------------------------------------------------

# ARC color palette from testing interface https://github.com/fchollet/ARC-AGI/blob/master/apps/css/common.css

ARC_COLORS_FALLBACK = [
    "#000",     # 0: black
    "#0074D9",  # 1: blue
    "#FF4136",  # 2: red
    "#2ECC40",  # 3: green
    "#FFDC00",  # 4: yellow
    "#AAAAAA",  # 5: grey
    "#F012BE",  # 6: fuschia
    "#FF851B",  # 7: orange
    "#7FDBFF",  # 8: teal
    "#870C25",  # 9: brown
]


def _style_path() -> Path:
    """Path to blog/style/style.yml."""
    return Path(__file__).resolve().parent.parent / "style" / "style.yml"


def _load_style_yml() -> dict:
    """Load style.yml; return {} if missing or invalid."""
    try:
        import yaml
    except ImportError:
        return {}
    path = _style_path()
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _get_arc_colors() -> list[str]:
    """Load ARC palette from blog/style/style.yml (colors.palette -> colors.<palette_name>) or use fallback."""
    data = _load_style_yml()
    colors = data.get("colors") or {}
    
    # Get the palette name from config
    palette_name = colors.get("palette")
    if not isinstance(palette_name, str):
        # No palette name configured, fall back to hardcoded
        return ARC_COLORS_FALLBACK
    
    # Look up the palette by name
    palette = colors.get(palette_name)
    if isinstance(palette, list) and len(palette) == 10 and all(isinstance(c, str) for c in palette):
        return palette
    
    # Palette name exists but palette not found or invalid, fall back to hardcoded
    return ARC_COLORS_FALLBACK


def _get_code_highlight_style() -> tuple[str, str]:
    """Load pygments style and fallback from style.yml (code_highlight.style, code_highlight.fallback_style)."""
    default_style = "github-light-default"
    default_fallback = "default"
    data = _load_style_yml()
    code = data.get("code_highlight") or {}
    style = code.get("style") if isinstance(code.get("style"), str) else default_style
    fallback = code.get("fallback_style") if isinstance(code.get("fallback_style"), str) else default_fallback
    return (style, fallback)


def arc_heatmap(grid: list[list[int]], colors: list[str] | None = None, gap=1) -> go.Heatmap:
    """
    Create a Plotly Heatmap trace for a single ARC grid (0-9 colors).
    
    Args:
        grid: 2D list of integers (0-9) representing cell colors.
        colors: Optional color palette (defaults to style.yml or fallback).
        gap: Gap between cells in pixels. Default 1 for visible grid lines.
             Figure dimensions are calculated to ensure integer pixel sizes.
             Non-integer values may cause antialiasing effects when viewing.
    """
    if colors is None:
        colors = _get_arc_colors()
    colorscale = []
    for i, color in enumerate(colors):
        colorscale.extend([(i / 10, color), ((i + 1) / 10, color)])

    return go.Heatmap(
        z=grid,
        zmin=-0.5,
        zmax=9.5,
        showscale=False,
        colorscale=colorscale,
        xgap=gap,
        ygap=gap,
        hoverinfo="skip",
    )


def _calculate_optimal_dimensions(
    pairs: list[tuple[list[list[int]], list[list[int]] | None]],
    target_width: int | None,
    gap,
    margin: dict[str, int],
    horizontal_spacing: float,
    vertical_spacing: float,
    pairs_per_row: int = 2,
) -> tuple[int, int, int]:
    """
    Calculate optimal figure dimensions and cell size to ensure integer pixel sizes.
    
    The key insight: we want each ARC cell to be an exact integer number of pixels.
    We calculate backwards from the target width to find a cell size that results
    in integer pixel dimensions for all cells.
    
    Returns:
        (figure_width, figure_height, cell_size_px) where cell_size_px ensures
        each ARC pixel (including gap) is an exact pixel size.
    """
    # Find maximum grid dimensions
    max_rows = 0
    max_cols = 0
    for in_grid, out_grid in pairs:
        if in_grid:
            max_rows = max(max_rows, len(in_grid))
            max_cols = max(max_cols, len(in_grid[0]) if in_grid else 0)
        if out_grid:
            max_rows = max(max_rows, len(out_grid))
            max_cols = max(max_cols, len(out_grid[0]) if out_grid else 0)
    
    if max_rows == 0 or max_cols == 0:
        return (400, 300, 20)  # Default fallback

    P = max(1, pairs_per_row)
    n_pairs = len(pairs)
    n_rows = (n_pairs + P - 1) // P
    n_cols = 2 * P  # each pair: input | output
    
    margin_l = margin.get("l", 5)
    margin_r = margin.get("r", 5)
    margin_t = margin.get("t", 20)
    margin_b = margin.get("b", 5)
    
    # Target cell size (pixels per ARC cell)
    # Start with a reasonable default or calculate from target_width
    if target_width is not None:
        # Estimate: available width = target_width - margins
        # Account for spacing: n_cols subplot columns -> (n_cols - 1) gaps
        # Each gap is horizontal_spacing fraction of the plot area width
        # Simplified: assume spacing takes ~horizontal_spacing * (n_cols-1) of total width
        plot_area_width = target_width - margin_l - margin_r
        spacing_width = plot_area_width * horizontal_spacing * (n_cols - 1)
        available_for_subplots = plot_area_width - spacing_width
        subplot_width_approx = available_for_subplots / n_cols
        
        # Calculate cell size that gives integer pixels
        cell_size = subplot_width_approx / max_cols
        # Round to nearest integer, but ensure minimum size
        cell_size = max(1, round(cell_size))
        
        # Now work backwards to get exact figure width
        subplot_width = cell_size * max_cols
        total_subplot_width = subplot_width * n_cols
        # Spacing is a fraction of the plot area, so we need to solve:
        # plot_area_width = total_subplot_width + spacing_width
        # spacing_width = plot_area_width * horizontal_spacing * (n_cols - 1)
        # plot_area_width = total_subplot_width / (1 - horizontal_spacing * (n_cols - 1))
        plot_area_width = total_subplot_width / (1 - horizontal_spacing * (n_cols - 1))
        figure_width = int(plot_area_width + margin_l + margin_r)
    else:
        # Use default cell size
        cell_size = 20
        subplot_width = cell_size * max_cols
        total_subplot_width = subplot_width * n_cols
        # Calculate plot area needed
        plot_area_width = total_subplot_width / (1 - horizontal_spacing * (n_cols - 1))
        figure_width = int(plot_area_width + margin_l + margin_r)
    
    # Calculate height similarly
    subplot_height = cell_size * max_rows
    total_subplot_height = subplot_height * n_rows
    if n_rows > 1:
        plot_area_height = total_subplot_height / (1 - vertical_spacing * (n_rows - 1))
    else:
        plot_area_height = total_subplot_height
    figure_height = int(plot_area_height + margin_t + margin_b)
    
    return (figure_width, figure_height, cell_size)


def _puzzle_pair_subplot_cols(
    pair_index: int,
    n_pairs: int,
    pairs_per_row: int,
) -> tuple[int, int]:
    """
    Return 1-based subplot column indices (input, output) for training/test pair `pair_index`.

    Full rows have ``pairs_per_row`` pairs (``2 * pairs_per_row`` subplot columns). If the last
    row is incomplete, that row's pairs are centered in the row.
    """
    P = max(1, pairs_per_row)
    n_rows = (n_pairs + P - 1) // P
    pairs_in_last_row = n_pairs - (n_rows - 1) * P
    last_row_start = (n_rows - 1) * P
    if pair_index >= last_row_start and pairs_in_last_row < P:
        k = pair_index - last_row_start
        start = (2 * P - 2 * pairs_in_last_row) // 2 + 1
        return (start + 2 * k, start + 2 * k + 1)
    pos = pair_index % P
    return (2 * pos + 1, 2 * pos + 2)


def _build_puzzle_figure(
    puzzle: Mapping[str, Any],
    show_test: ShowTestArg = False,
    width: int | None = None,
    gap=1,
    pairs_per_row: int = 2,
) -> go.Figure:
    """
    Build a figure of input/output grids per pair.

    ``pairs_per_row`` sets how many input–output pairs are placed on one row (default ``2``,
    i.e. four subplot columns: in|out|in|out). Test output cells show ``?``.

    ``show_test``: ``False`` — training pairs only; ``True`` — training plus test inputs
    (unknown output as ``?``); ``\"only\"`` — test pairs only (same ``?`` convention).
    """
    train = puzzle.get("train", [])
    test_raw = puzzle.get("test", [])
    pairs: list[tuple[list[list[int]], list[list[int]] | None]] = []
    if isinstance(show_test, str) and show_test.strip().lower() == "only":
        for ex in test_raw:
            pairs.append((ex["input"], None))
    elif show_test is True:
        for ex in train:
            pairs.append((ex["input"], ex["output"]))
        for ex in test_raw:
            pairs.append((ex["input"], None))
    else:
        for ex in train:
            pairs.append((ex["input"], ex["output"]))
    n_pairs = len(pairs)
    if n_pairs == 0:
        return go.Figure()

    P = max(1, pairs_per_row)
    n_rows = (n_pairs + P - 1) // P
    n_subplot_cols = 2 * P

    # Calculate optimal dimensions for pixel-perfect rendering
    margin = dict(l=5, r=5, t=20, b=5)
    horizontal_spacing = 0.04
    vertical_spacing = 0.08
    figure_width, figure_height, cell_size = _calculate_optimal_dimensions(
        pairs, width, gap, margin, horizontal_spacing, vertical_spacing, pairs_per_row=P
    )

    fig = make_subplots(
        rows=n_rows,
        cols=n_subplot_cols,
        horizontal_spacing=horizontal_spacing,
        vertical_spacing=vertical_spacing,
    )

    for p, (in_grid, out_grid) in enumerate(pairs):
        row = p // P + 1
        col_in, col_out = _puzzle_pair_subplot_cols(p, n_pairs, P)
        fig.add_trace(arc_heatmap(in_grid, gap=gap), row=row, col=col_in)
        if out_grid is not None:
            fig.add_trace(arc_heatmap(out_grid, gap=gap), row=row, col=col_out)
        # For test output we add no trace; subplot stays empty, "?" annotation added below

    n_subplots = n_rows * n_subplot_cols
    for idx in range(1, n_subplots + 1):
        suffix = "" if idx == 1 else str(idx)
        fig.update_yaxes(
            autorange="reversed",
            scaleanchor=f"x{suffix}",
            scaleratio=1,
            selector=dict(anchor=f"x{suffix}"),
        )

    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False, showline=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, showline=False)
    layout_dict = {
        "height": figure_height,
        "width": figure_width,
        "autosize": False,  # Disable autosize to preserve calculated dimensions
        "showlegend": False,
        "margin": margin,
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
    }
    fig.update_layout(**layout_dict)

    # Triangle / "?" markers use paper coords. Triangle height tracks layout cell_size;
    # "?" font is derived from the test output subplot size ÷ grid so it matches a cell
    # on screen (layout cell_size can be a few px while the drawn cell is larger).
    paper_aspect = figure_width / max(1.0, float(figure_height))
    triangle_height_px = max(10.0, 4.0 * float(cell_size))

    # Right-pointing triangles between input → output for each pair; "?" on test output cells
    for p, (in_grid, out_grid) in enumerate(pairs):
        row = p // P + 1
        col_in, col_out = _puzzle_pair_subplot_cols(p, n_pairs, P)
        idx_in = (row - 1) * n_subplot_cols + col_in
        idx_out = (row - 1) * n_subplot_cols + col_out
        xaxis_in_name = "xaxis" if idx_in == 1 else f"xaxis{idx_in}"
        xaxis_out_name = f"xaxis{idx_out}"
        yaxis_in_name = "yaxis" if idx_in == 1 else f"yaxis{idx_in}"
        if xaxis_in_name not in fig.layout or xaxis_out_name not in fig.layout:
            continue
        d_in = fig.layout[xaxis_in_name].domain
        d_out = fig.layout[xaxis_out_name].domain
        if yaxis_in_name in fig.layout:
            dy = fig.layout[yaxis_in_name].domain
            y_mid = (dy[0] + dy[1]) / 2
        else:
            dy = (0.0, 1.0)
            row_frac = (row - 0.5) / n_rows
            y_mid = 1.0 - row_frac

        yaxis_out_name = "yaxis" if idx_out == 1 else f"yaxis{idx_out}"
        dy_out = fig.layout[yaxis_out_name].domain if yaxis_out_name in fig.layout else dy
        y_mid_out = (dy_out[0] + dy_out[1]) / 2

        # Calculate exact center between subplots
        # x_mid is the center point between the right edge of input and left edge of output
        x_mid = (d_in[1] + d_out[0]) / 2

        gap_x = max(1e-6, d_out[0] - d_in[1])
        triangle_height = triangle_height_px / float(figure_height)
        triangle_width = triangle_height / paper_aspect
        if triangle_width > gap_x * 0.88:
            triangle_width = gap_x * 0.88
            triangle_height = triangle_width * paper_aspect

        # Right-pointing triangle: centered at x_mid, pointing right
        # Triangle points: left-top (base), right tip, left-bottom (base)
        tip_x = x_mid + triangle_width / 2
        base_x = x_mid - triangle_width / 2
        top_y = y_mid - triangle_height / 2
        bottom_y = y_mid + triangle_height / 2
        fig.add_shape(
            type="path",
            path=f"M {base_x},{top_y} L {tip_x},{y_mid} L {base_x},{bottom_y} Z",
            xref="paper",
            yref="paper",
            fillcolor="#666",
            line=dict(color="#666", width=0),
        )
        if out_grid is None:
            output_x_mid = (d_out[0] + d_out[1]) / 2
            nr = max(len(in_grid) if in_grid else 0, 1)
            nc = max(len(in_grid[0]) if in_grid and in_grid[0] else 0, 1)
            out_w_px = (d_out[1] - d_out[0]) * float(figure_width)
            out_h_px = (dy_out[1] - dy_out[0]) * float(figure_height)
            cell_px = min(out_w_px / nc, out_h_px / nr)
            # "?" ~ one cell visually; on dense grids tie to triangle / cell_size.
            # Size is 4× that baseline (two +100% steps) for slide legibility.
            _base = max(
                22,
                min(
                    420,
                    round(
                        max(
                            cell_px * 5.5,
                            float(cell_size) * 5.0,
                            triangle_height_px * 1.15,
                        )
                    ),
                ),
            )
            mark_font = int(min(1680, max(88, round(_base * 4))))
            fig.add_annotation(
                x=output_x_mid,
                y=y_mid_out,
                xref="paper",
                yref="paper",
                xanchor="center",
                yanchor="middle",
                text="?",
                showarrow=False,
                font=dict(size=mark_font, color="#666"),
            )
    return fig


def show_puzzle(
    puzzle_id: str,
    show_test: ShowTestArg = False,
    show_code: bool = False,
    width: int | None = None,
    gap=1,
    pairs_per_row: int = 2,
) -> go.Figure | HTML:
    """
    Load and display an ARC puzzle by id.

    - Loads puzzle from data/puzzles/{puzzle_id}.json.
    - Layout: ``pairs_per_row`` input–output pairs per row (default ``2`` → four subplots per row:
      input1 | output1 | input2 | output2).
    - ``show_test``: ``False`` — training pairs only; ``True`` — training plus test inputs
      (unknown output as ``?``); ``\"only\"`` (case-insensitive) — **test** pairs only.
    - If show_code=True: also show solution code from data/puzzles/{puzzle_id}.py,
      or "no code found" if the file is missing. Returns HTML. Otherwise returns go.Figure.
    - width: Optional target figure width in pixels. Actual width is calculated to ensure
             integer pixel sizes for each ARC cell (prevents moiré patterns).
    - gap: Gap between grid cells in pixels. Default 1 for visible grid lines.
           Figure dimensions are automatically calculated to ensure pixel-perfect rendering.
           Non-integer values may cause antialiasing effects when viewing.
    - pairs_per_row: How many (input, output) pairs to place on one horizontal row (minimum 1).
    """
    from src.data import get_solution_path, load_puzzle

    try:
        puzzle = load_puzzle(puzzle_id)
    except FileNotFoundError:
        raise FileNotFoundError(f"Puzzle not found: {puzzle_id} (expected data/puzzles/{puzzle_id}.json)")
    except Exception as e:
        raise RuntimeError(f"Failed to load puzzle {puzzle_id}: {e}") from e

    fig = _build_puzzle_figure(
        puzzle, show_test=show_test, width=width, gap=gap, pairs_per_row=pairs_per_row
    )

    if not show_code:
        return fig

    code_path = get_solution_path(puzzle_id)
    # Apply interactivity config from style.yml
    cfg = _plotly_config_for("puzzle")
    plotly_html = fig.to_html(include_plotlyjs="cdn", full_html=False, config=cfg)
    if not code_path.exists():
        code_html = '<p style="margin-top: 1em; color: #666;">no code found</p>'
    else:
        code = code_path.read_text()
        style_name, fallback_name = _get_code_highlight_style()
        try:
            from pygments.styles import get_style_by_name
            get_style_by_name(style_name)
        except (ClassNotFound, ValueError):
            style_name = fallback_name
        formatter = HtmlFormatter(style=style_name, noclasses=True, nowrap=False)
        code_html = highlight(code, PythonLexer(), formatter)
    combined = f"""
    <div class="puzzle-with-code">
        {plotly_html}
        <div style="text-align: left; margin-top: 1em;">
            {code_html}
        </div>
    </div>
    """
    return HTML(combined)


# ---------------------------------------------------------------------------
# Tool-calls histogram (styled like other figures)
# ---------------------------------------------------------------------------


def tool_calls_histogram(
    values: list[int] | list[float],
    nbins: int = 40,
    style_config: dict | None = None,
) -> go.Figure:
    """Histogram of tool-call counts. Layout and bar color from style (figures.tool_calls_histogram)."""
    style = style_config if style_config is not None else _load_style_yml()
    cfg = _get_figure_config("tool_calls_histogram", style)
    layout_cfg = cfg.get("layout") or {}
    margin = layout_cfg.get("margin", dict(l=60, r=30, t=40, b=60))
    height = layout_cfg.get("height", 400)
    width = layout_cfg.get("width", 520)
    bar_color = cfg.get("bar_color", "#D2691E")
    fig = go.Figure(data=[go.Histogram(x=list(values), nbinsx=nbins, marker=dict(color=bar_color), hoverinfo="skip")])
    fig.update_layout(
        xaxis_title="number of tool calls per turn",
        yaxis_title="count",
        height=height,
        width=width,
        margin=margin,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.1)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.1)")
    return fig


# ---------------------------------------------------------------------------
# Scatter / subplot helpers (primary figures; style from style.yml only)
# ---------------------------------------------------------------------------


def _get_baseline_vs_interleaved_style(style: dict | None = None) -> dict:
    """Return figures.baseline_vs_interleaved from style.yml (colors and shapes for figures using baseline_vs_interleaved.json)."""
    data = style if style is not None else _load_style_yml()
    figures = data.get("figures") or {}
    return figures.get("baseline_vs_interleaved") or {}


def _get_figure_config(fig_key: str, style: dict | None = None) -> dict:
    """Return figures.<fig_key> from style.yml."""
    data = style if style is not None else _load_style_yml()
    figures = data.get("figures") or {}
    return figures.get(fig_key) or {}


def _is_figure_interactive(fig_key: str, style: dict | None = None) -> bool:
    """
    Return whether a given figure should be interactive, based on style.yml.
    
    Special case: puzzle figures default to False (static) if not specified.
    Other figures default to True (interactive) if not specified.
    """
    data = style if style is not None else _load_style_yml()
    figures = data.get("figures") or {}
    cfg = figures.get(fig_key) or {}
    
    # Check if interactive flag is explicitly set
    if "interactive" in cfg:
        return bool(cfg["interactive"])
    
    # Special case: puzzle figures default to static
    if fig_key == "puzzle":
        return False
    
    # For other figures, check defaults, then fall back to True
    defaults = figures.get("defaults") or {}
    default_interactive = defaults.get("interactive", True)
    return bool(default_interactive)


def _plotly_config_for(fig_key: str, style: dict | None = None) -> dict:
    """
    Return plotly.js config dict, toggling interactions based on style.yml.
    
    Returns empty dict {} for interactive plots, or static config for non-interactive plots.
    """
    interactive = _is_figure_interactive(fig_key, style)
    if interactive:
        return {}
    return {
        "staticPlot": True,          # Disable panning/zooming/hover
        "displayModeBar": False,     # Hide toolbar
        "responsive": False,
    }


def _merge_dicts(
    base: Mapping[str, Any] | None,
    override: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Shallow merge for Plotly style dicts (override wins)."""
    out: dict[str, Any] = {}
    if base:
        out.update(dict(base))
    if override:
        out.update(dict(override))
    return out


def is_present(value: Any) -> bool:
    """True iff value should be treated as 'present' for hover display."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
        return False
    return True


def format_hover_value(value: Any, *, missing: str = "—") -> str:
    """Format a value for HTML hovertext (escaped)."""
    if not is_present(value):
        return missing
    return escape(str(value))


def build_hovertext(
    entry: Mapping[str, Any],
    *,
    title_key: str = "modelDisplayName",
    required_keys: Sequence[str] = ("costPerTask", "score"),
    optional_keys: Sequence[str] | None = None,
    key_labels: Mapping[str, str] | None = None,
    value_transforms: Mapping[str, Callable[[Any], Any]] | None = None,
    include_required: bool = True,
) -> str:
    """Build HTML hovertext for a single datapoint."""
    labels = dict(key_labels or {})
    transforms = dict(value_transforms or {})

    title_value = entry.get(title_key)
    if title_key in transforms:
        try:
            title_value = transforms[title_key](title_value)
        except Exception:
            pass
    title = format_hover_value(title_value)
    lines: list[str] = [f"<b>{title}</b>"]

    if include_required:
        for k in required_keys:
            if k == title_key:
                continue
            v = entry.get(k)
            if k in transforms:
                try:
                    v = transforms[k](v)
                except Exception:
                    pass
            lines.append(f"{labels.get(k, k)}: {format_hover_value(v)}")

    if optional_keys is not None:
        for k in optional_keys:
            if k == title_key:
                continue
            v = entry.get(k)
            if is_present(v):
                if k in transforms:
                    try:
                        v = transforms[k](v)
                    except Exception:
                        pass
                lines.append(f"{labels.get(k, k)}: {format_hover_value(v)}")

    return "<br>".join(lines)


def make_scatter_trace(
    entries: Sequence[Mapping[str, Any]],
    *,
    name: str,
    x_key: str = "costPerTask",
    y_key: str = "score",
    y_scale: float = 1.0,
    hovertext_fn: Callable[[Mapping[str, Any]], str],
    mode: str = "markers",
    marker: Mapping[str, Any] | None = None,
    line: Mapping[str, Any] | None = None,
    showlegend: bool = False,
) -> go.Scatter:
    """Create a Plotly scatter trace from datapoint dicts."""
    x_values = [e.get(x_key) for e in entries]
    if y_scale == 1.0:
        y_values = [e.get(y_key) for e in entries]
    else:
        y_values = []
        for e in entries:
            v = e.get(y_key)
            if v is None:
                y_values.append(None)
            else:
                try:
                    y_values.append(float(v) * float(y_scale))
                except Exception:
                    y_values.append(v)
    hovertext = [hovertext_fn(e) for e in entries]

    return go.Scatter(
        x=x_values,
        y=y_values,
        mode=mode,
        name=name,
        showlegend=showlegend,
        marker=dict(marker or {}),
        line=dict(line or {}) if "lines" in mode else None,
        hovertext=hovertext,
        hovertemplate="%{hovertext}<extra></extra>",
    )


def _add_segment_arrows(
    fig: go.Figure,
    *,
    x: Sequence[Any],
    y: Sequence[Any],
    xref: str,
    yref: str,
    arrowcolor: str,
    arrowwidth: float = 2,
    arrowhead: int = 3,
    label: str | None = None,
) -> None:
    """Add annotation arrows for each consecutive pair of points."""
    if len(x) < 2 or len(y) < 2:
        return

    for i in range(len(x) - 1):
        x0, y0 = x[i], y[i]
        x1, y1 = x[i + 1], y[i + 1]
        if x0 is None or y0 is None or x1 is None or y1 is None:
            continue

        fig.add_annotation(
            x=x1,
            y=y1,
            xref=xref,
            yref=yref,
            ax=x0,
            ay=y0,
            axref=xref,
            ayref=yref,
            showarrow=True,
            arrowhead=arrowhead,
            arrowsize=1,
            arrowwidth=arrowwidth,
            arrowcolor=arrowcolor,
            text="",
        )
        if label:
            x_mid = (x0 + x1) / 2
            y_mid = (y0 + y1) / 2
            dx = x1 - x0
            dy = y1 - y0
            length = (dx**2 + dy**2) ** 0.5
            if length > 0:
                offset_scale = max(abs(x1 - x0), abs(y1 - y0)) * 0.1
                offset_x = dx / length * offset_scale
                offset_y = dy / length * offset_scale
                label_hash = hash(label) % 100
                stagger_scale = offset_scale * 0.2
                offset_x += -dy / length * stagger_scale * (label_hash / 100.0 - 0.5)
                offset_y += dx / length * stagger_scale * (label_hash / 100.0 - 0.5)
            else:
                offset_x, offset_y = 0.1, 0
            fig.add_annotation(
                x=x_mid + offset_x,
                y=y_mid + offset_y,
                xref=xref,
                yref=yref,
                xanchor="center",
                yanchor="top",
                showarrow=False,
                text=label,
                font=dict(size=10),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="rgba(0,0,0,0.2)",
                borderwidth=1,
                borderpad=3,
            )


def create_figure_with_subplots(
    *,
    rows: int,
    cols: int,
    subplot_titles: Sequence[str] | None = None,
    shared_xaxes: bool = False,
    shared_yaxes: bool = False,
) -> go.Figure:
    """Thin wrapper around plotly.subplots.make_subplots."""
    return make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=list(subplot_titles) if subplot_titles is not None else None,
        shared_xaxes=shared_xaxes,
        shared_yaxes=shared_yaxes,
    )


def add_scatter_traces_to_subplot(
    fig: go.Figure,
    *,
    row: int,
    col: int,
    traces: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
    data_spec: Mapping[str, Sequence[str]] | None = None,
    x_key: str = "costPerTask",
    y_key: str = "score",
    y_scale: float = 1.0,
    marker_defaults: Mapping[str, Any] | None = None,
    line_defaults: Mapping[str, Any] | None = None,
    arrow_defaults: Mapping[str, Any] | None = None,
    marker_by_trace_name: Mapping[str, Mapping[str, Any]] | None = None,
    arrow_by_trace_name: Mapping[str, Mapping[str, Any]] | None = None,
    key_labels: Mapping[str, str] | None = None,
    include_required_in_hover: bool = True,
    add_arrows: bool = False,
) -> go.Figure:
    """Add multiple scatter traces into a specific subplot. Style from style.yml only."""
    required_keys: Sequence[str] = (x_key, y_key)
    optional_keys: Sequence[str] | None = None
    if data_spec is not None:
        required_keys = data_spec.get("required_fields", required_keys)
        optional_keys = data_spec.get("extra_fields", None)

    transforms: dict[str, Callable[[Any], Any]] = {}
    if y_scale != 1.0:

        def _scale_y(v: Any) -> Any:
            if v is None:
                return None
            try:
                return float(v) * float(y_scale)
            except Exception:
                return v

        transforms[y_key] = _scale_y

    def _hover(e: Mapping[str, Any]) -> str:
        return build_hovertext(
            e,
            title_key="modelDisplayName",
            required_keys=required_keys,
            optional_keys=optional_keys,
            key_labels=key_labels,
            value_transforms=transforms,
            include_required=include_required_in_hover,
        )

    markers = dict(marker_by_trace_name or {})
    arrows = dict(arrow_by_trace_name or {})
    for trace_name, entries in traces:
        mode = "markers" if add_arrows else "markers"
        marker_style = _merge_dicts(marker_defaults, markers.get(trace_name))
        arrow_style = _merge_dicts(arrow_defaults, arrows.get(trace_name))
        trace = make_scatter_trace(
            entries,
            name=trace_name,
            x_key=x_key,
            y_key=y_key,
            y_scale=y_scale,
            hovertext_fn=_hover,
            mode=mode,
            marker=marker_style,
            line=None,
            showlegend=False,
        )
        fig.add_trace(trace, row=row, col=col)

        if add_arrows:
            added_trace = fig.data[-1]
            xref = getattr(added_trace, "xaxis", "x") or "x"
            yref = getattr(added_trace, "yaxis", "y") or "y"
            ac = arrow_style.get("color")
            mc = marker_style.get("color")
            if ac is not None:
                arrowcolor = str(ac)
            elif isinstance(mc, str):
                arrowcolor = mc
            else:
                arrowcolor = "rgba(0,0,0,0.6)"
            arrowwidth = float(arrow_style.get("width", 2))
            arrowhead = int(arrow_style.get("head", 3))
            _add_segment_arrows(
                fig,
                x=list(getattr(added_trace, "x", []) or []),
                y=list(getattr(added_trace, "y", []) or []),
                xref=xref,
                yref=yref,
                arrowcolor=arrowcolor,
                arrowwidth=arrowwidth,
                arrowhead=arrowhead,
                label=trace_name,
            )

    return fig


# Injected into <head> of every Plotly sidecar HTML written by this module.
# CSS: fills the iframe viewport.
# Reveal stub: quarto preview injects quarto-preview.js into every served HTML
# file; that script assumes a Reveal.js context and throws ReferenceError when
# window.Reveal is undefined, crashing before Plotly can initialise.
_SIDECAR_HEAD_INJECT = (
    "<style>"
    "html,body{margin:0;padding:0;height:100%;width:100%;overflow:hidden;}"
    ".plotly-graph-div{height:100%!important;width:100%!important;}"
    "</style>"
    "<script>"
    # quarto-preview.js is injected by `quarto preview` into every served HTML.
    # It calls Reveal.isReady() and other methods; without a stub it throws
    # TypeError before Plotly initialises.  A Proxy catches every property
    # access and returns a harmless no-op so the crash never happens.
    "if(typeof window.Reveal==='undefined'){"
    "window.Reveal=new Proxy({},"
    "{get:function(t,p){"
    "if(p==='isReady')return function(){return false;};"
    "if(p==='getConfig')return function(){return {};};"
    "if(p==='getState')return function(){return {};};"
    "return function(){};"
    "}});"
    "}"
    "</script>"
)


def display_figure(
    fig: go.Figure,
    fig_key: str,
) -> None:
    """Display a Plotly figure with ``config`` from ``style.yml`` (``figures.<fig_key>``)."""
    config = _plotly_config_for(fig_key)
    fig.show(config=config)


# ---------------------------------------------------------------------------
# Dummy figure for lightbox demo / testing
# ---------------------------------------------------------------------------


def create_dummy_scatter() -> go.Figure:
    """Simple scatter figure used to demo the two lightbox strategies."""
    import random
    import math

    rng = random.Random(42)
    n = 80
    # Box-Muller for normal samples without numpy
    def _randn() -> float:
        u1, u2 = rng.random(), rng.random()
        return math.sqrt(-2 * math.log(max(u1, 1e-12))) * math.cos(2 * math.pi * u2)

    x = [_randn() for _ in range(n)]
    y = [xi * 0.7 + _randn() * 0.5 for xi in x]
    colors = [rng.random() for _ in range(n)]

    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(
                size=10,
                color=colors,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="value"),
                line=dict(width=0.5, color="white"),
            ),
            hovertemplate="x=%{x:.2f}<br>y=%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Demo scatter — hover/zoom to explore",
        xaxis_title="x",
        yaxis_title="y",
        plot_bgcolor="rgba(245,245,250,1)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------------------------------------------------------------------------
# Strategy A: GLightbox iframe wrapper
# ---------------------------------------------------------------------------


def write_plotly_for_glightbox(
    fig: go.Figure,
    html_path: str | Path,
    *,
    fig_key: str,
    preview_png_path: str | Path | None = None,
    preview_scale: float = 2.0,
    lightbox_width: str = "90vw",
    lightbox_height: str = "85vh",
    caption: str = "",
) -> str:
    """
    Write a standalone Plotly HTML + optional preview PNG.

    Returns a raw HTML string: an ``<a class="lightbox" data-type="external">``
    element wrapping the preview image.  Quarto's GLightbox intercepts the click
    and opens the interactive HTML inside a modal iframe.

    ``caption`` — optional caption string rendered as ``data-description`` on
    the anchor.  GLightbox displays it in the styled description strip below the
    iframe (inheriting the ``$lightbox-caption-*`` SCSS variables).

    IMPORTANT: embed the returned string via a ``{=html}`` raw block in the
    ``.qmd``, NOT via ``display(HTML(...))`` — Pandoc strips ``<a>`` elements
    from notebook HTML outputs.

    ``html_path`` must be a path relative to the **rendered output file**
    (e.g. ``"scores-scatter-interactive.html"`` when the .qmd renders to
    ``presentation.html`` in the same directory).

    PNG export requires kaleido (``pip install kaleido``).
    """
    import copy as _copy

    out = Path(html_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    _fig = _copy.deepcopy(fig)
    _fig.update_layout(
        width=None, height=None, autosize=True,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    # Always fully interactive — this is the interactive half of the pair.
    _interactive_config = {"scrollZoom": True}
    _fig.write_html(str(out), config=_interactive_config, include_plotlyjs="directory", full_html=True)

    _html = out.read_text(encoding="utf-8")
    _html = _html.replace("<head>", "<head>" + _SIDECAR_HEAD_INJECT, 1)
    out.write_text(_html, encoding="utf-8")

    if preview_png_path is not None:
        png = Path(preview_png_path)
        png.parent.mkdir(parents=True, exist_ok=True)
        try:
            fig.write_image(str(png), scale=preview_scale)
        except Exception as e:
            raise RuntimeError(
                "Plotly static export failed (install kaleido: pip install kaleido). "
                f"Original error: {e}"
            ) from e

    href = out.name
    img_tag = (
        f'<img src="img/{Path(preview_png_path).name}" '
        f'alt="Interactive chart — click to open" '
        f'class="r-stretch" style="max-height:68vh;cursor:pointer" />'
        if preview_png_path
        else f'<span style="padding:2em;border:2px dashed #aaa;cursor:pointer">'
             f'Click to open interactive chart</span>'
    )
    # Use GLightbox natively via class="lightbox" data-type="external".
    # NOTE: data-type="external" NOT "iframe" — the GLightbox version bundled by
    # Quarto only triggers the iframe renderer (Z()) for type "external"; "iframe"
    # falls into a no-op branch and renders blank.
    # data-description → GLightbox renders it in .gslide-description below the
    # iframe, styled by $lightbox-caption-* SCSS variables in presentation-theme.scss.
    # IMPORTANT: embed via {=html} raw block, NOT display(HTML(...)) — Pandoc
    # strips <a> elements from notebook HTML outputs.
    desc_attr = f'\n     data-description="{caption}"' if caption else ""
    return (
        f'<div style="text-align:center;margin-top:0.75em">\n'
        f'  <a href="{href}"\n'
        f'     class="lightbox"\n'
        f'     data-type="external"\n'
        f'     data-width="{lightbox_width}"\n'
        f'     data-height="{lightbox_height}"{desc_attr}\n'
        f'     style="display:inline-block;cursor:pointer">\n'
        f'    {img_tag}\n'
        f'  </a>\n'
        f'</div>\n'
    )


# ---------------------------------------------------------------------------
# Baseline vs interleaved figures (modular: scatter and bar in separate places)
# ---------------------------------------------------------------------------


def _prepare_baseline_interleaved_data(
    experiments_data: dict,
) -> tuple[
    list[tuple[str, list[dict]]],
    list[str],
    list[float],
    list[float],
]:
    """Group baseline_vs_interleaved data into scatter traces and bar labels/scores (no style)."""
    entries = experiments_data.get("data") or []
    pairs_by_family: dict[str, dict[str, dict]] = {}
    family_order: list[str] = []
    for entry in entries:
        family = entry.get("baseModelFamily")
        if family is None:
            continue
        if family not in pairs_by_family:
            pairs_by_family[family] = {}
            family_order.append(family)
        mt = entry.get("modelType")
        if mt is not None:
            pairs_by_family[family][mt] = entry

    scatter_traces: list[tuple[str, list[dict]]] = []
    bar_labels: list[str] = []
    baseline_scores: list[float] = []
    interleaved_scores: list[float] = []

    for family in family_order:
        pair = pairs_by_family.get(family, {})
        baseline = pair.get("CoT")
        interleaved = pair.get("Interleaved Thinking")
        if not baseline or not interleaved:
            continue

        # Build label: baseModelFamily + effortLevel (if exists)
        label = family
        effort_level = baseline.get("effortLevel") or interleaved.get("effortLevel")
        if effort_level:
            label = f"{family} ({effort_level})"

        scatter_traces.append((label, [baseline, interleaved]))
        bar_labels.append(label)
        b_score = float(baseline.get("score", 0.0)) * 100.0
        i_score = float(interleaved.get("score", 0.0)) * 100.0
        baseline_scores.append(b_score)
        interleaved_scores.append(i_score)

    return (
        scatter_traces,
        bar_labels,
        baseline_scores,
        interleaved_scores,
    )


def _load_bar_data(experiments_data: dict, style_config: dict | None):
    """Load experiments, prepare bar data and config. Returns (bar_labels, baseline_scores, interleaved_scores, improvement_scores, color_plain_cot, color_agentic, names, layout_cfg, axis_cfg)."""
    style = style_config if style_config is not None else _load_style_yml()
    shared = _get_baseline_vs_interleaved_style(style)
    cfg = _get_figure_config("bar_baseline_vs_interleaved", style)
    series_names = cfg.get("series_names") or {}
    (
        _st,
        bar_labels,
        baseline_scores,
        interleaved_scores,
    ) = _prepare_baseline_interleaved_data(experiments_data)
    improvement_scores = [max(interleaved_scores[i] - baseline_scores[i], 0.0) for i in range(len(baseline_scores))]

    colors_cfg = shared.get("colors") or {}
    color_plain_cot = colors_cfg.get("baseline", "#808080")
    color_agentic = colors_cfg.get("interleaved", "#D2691E")

    names = (
        series_names.get("baseline", "Plain CoT"),
        series_names.get("interleaved", "Agentic Coding"),
        series_names.get("baseline_stacked", "Plain CoT"),
        series_names.get("improvement_stacked", "Agentic Coding Improvement"),
    )
    return bar_labels, baseline_scores, interleaved_scores, improvement_scores, color_plain_cot, color_agentic, names, cfg.get("layout") or {}, cfg.get("axis") or {}


def _add_grouped_bars(fig: go.Figure, bar_labels: list, baseline_scores: list, interleaved_scores: list, color_plain_cot: str, color_agentic: str, nb: str, ni: str, row: int | None = None, col: int | None = None) -> None:
    x_b = [i - 0.15 for i in range(len(bar_labels))]
    x_i = [i + 0.15 for i in range(len(bar_labels))]
    add = lambda t: fig.add_trace(t, row=row, col=col) if row is not None else fig.add_trace(t)
    add(go.Bar(name=nb, x=x_b, y=baseline_scores, marker=dict(color=color_plain_cot), customdata=bar_labels, hovertemplate="%{customdata}<br>" + nb + ": %{y:.2f}%<extra></extra>"))
    add(go.Bar(name=ni, x=x_i, y=interleaved_scores, marker=dict(color=color_agentic), customdata=bar_labels, hovertemplate="%{customdata}<br>" + ni + ": %{y:.2f}%<extra></extra>"))
    upd = lambda **kw: fig.update_xaxes(**kw, row=row, col=col) if row is not None else fig.update_xaxes(**kw)
    upd(tickmode="array", tickvals=list(range(len(bar_labels))), ticktext=bar_labels)


def _add_stacked_bars(fig: go.Figure, bar_labels: list, baseline_scores: list, improvement_scores: list, color_plain_cot: str, color_agentic: str, nbs: str, nis: str, row: int | None = None, col: int | None = None) -> None:
    x_cat = list(range(len(bar_labels)))
    add = lambda t: fig.add_trace(t, row=row, col=col) if row is not None else fig.add_trace(t)
    add(go.Bar(name=nbs, x=x_cat, y=baseline_scores, marker=dict(color=color_plain_cot), width=0.75, showlegend=False))
    add(go.Bar(name=nis, x=x_cat, y=improvement_scores, marker=dict(color=color_agentic), width=0.75, showlegend=False))
    upd = lambda **kw: fig.update_xaxes(**kw, row=row, col=col) if row is not None else fig.update_xaxes(**kw)
    upd(tickmode="array", tickvals=x_cat, ticktext=bar_labels)


def create_baseline_interleaved_scatter(
    experiments_data: dict | None = None,
    style_config: dict | None = None,
) -> go.Figure:
    """
    Single figure: cost vs score scatter with baseline -> interleaved arrows.
    Data and style from blog/data and blog/style/style.yml unless overridden.
    Colors and shapes from figures.baseline_vs_interleaved (shared with bar figure).
    """
    if experiments_data is None:
        from src.data import load_baseline_vs_interleaved
        experiments_data = load_baseline_vs_interleaved()
    style = style_config if style_config is not None else _load_style_yml()
    shared = _get_baseline_vs_interleaved_style(style)
    cfg = _get_figure_config("scatter_baseline_vs_interleaved", style)
    data_spec = cfg.get("data_spec")
    marker_cfg = cfg.get("marker") or {}
    arrow_cfg = cfg.get("arrow") or {}
    layout_cfg = cfg.get("layout") or {}
    axis_cfg = cfg.get("axis") or {}

    colors_cfg = shared.get("colors") or {}
    shapes_cfg = shared.get("shapes") or {}
    color_baseline = colors_cfg.get("baseline", "#808080")
    color_interleaved = colors_cfg.get("interleaved", "#D2691E")
    shape_baseline = shapes_cfg.get("baseline", "diamond")
    shape_interleaved = shapes_cfg.get("interleaved", "star")

    (
        scatter_traces,
        _bar_labels,
        _baseline_scores,
        _interleaved_scores,
    ) = _prepare_baseline_interleaved_data(experiments_data)

    marker_by_trace_name = {
        label: {
            "color": [color_baseline, color_interleaved],
            "symbol": [shape_baseline, shape_interleaved],
        }
        for label, _ in scatter_traces
    }

    fig = create_figure_with_subplots(rows=1, cols=1)
    marker_defaults = {"size": marker_cfg.get("size", 12), "opacity": marker_cfg.get("opacity", 0.9)}
    arrow_defaults = {
        "width": arrow_cfg.get("width", 2),
        "head": arrow_cfg.get("head", 3),
        "color": arrow_cfg.get("color", "rgba(128,128,128,0.5)"),
    }
    add_scatter_traces_to_subplot(
        fig,
        row=1,
        col=1,
        traces=scatter_traces,
        data_spec=data_spec,
        marker_defaults=marker_defaults,
        arrow_defaults=arrow_defaults,
        marker_by_trace_name=marker_by_trace_name,
        add_arrows=True,
        y_scale=100,
    )

    fig.update_xaxes(title_text=axis_cfg.get("x_title", "Cost per task [$]"), row=1, col=1)
    fig.update_yaxes(title_text=axis_cfg.get("y_title", "Score [%]"), row=1, col=1)
    
    # Set axis ranges: use config if provided, otherwise auto-calculate
    x_range = axis_cfg.get("x_range")
    if x_range is None:
        # Auto-calculate x-axis range from data
        all_costs = []
        for _fam, entries in scatter_traces:
            for e in entries:
                c = e.get("costPerTask")
                if c is not None:
                    all_costs.append(float(c))
        max_cost = max(all_costs) * 1.1 if all_costs else 1
        x_range = [0, max_cost]
    
    y_range = axis_cfg.get("y_range")
    
    # Apply ranges if specified
    xaxis_update = {"type": "linear", "showgrid": True, "gridcolor": "rgba(0,0,0,0.1)"}
    if x_range is not None:
        xaxis_update["range"] = x_range
    
    yaxis_update = {"type": "linear", "showgrid": True, "gridcolor": "rgba(0,0,0,0.1)"}
    if y_range is not None:
        yaxis_update["range"] = y_range
    
    fig.update_xaxes(**xaxis_update, row=1, col=1)
    fig.update_yaxes(**yaxis_update, row=1, col=1)

    # Legend: two entries for baseline vs interleaved (dummy traces, no data)
    series_names = cfg.get("series_names") or {}
    name_baseline = series_names.get("baseline", "Plain CoT")
    name_interleaved = series_names.get("interleaved", "Agentic Coding")
    marker_size = marker_cfg.get("size", 12)
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            name=name_baseline,
            marker=dict(
                symbol=shape_baseline,
                color=color_baseline,
                size=marker_size,
                opacity=marker_cfg.get("opacity", 0.9),
            ),
            showlegend=True,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            name=name_interleaved,
            marker=dict(
                symbol=shape_interleaved,
                color=color_interleaved,
                size=marker_size,
                opacity=marker_cfg.get("opacity", 0.9),
            ),
            showlegend=True,
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        showlegend=True,
        height=layout_cfg.get("height", 400),
        width=layout_cfg.get("width", 520),
        margin=layout_cfg.get("margin", dict(l=60, r=30, t=40, b=60)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_baseline_interleaved_bars(
    experiments_data: dict | None = None,
    variant: str = "grouped",
    style_config: dict | None = None,
) -> go.Figure:
    """Single figure: grouped or stacked bars. variant: "grouped" | "stacked"."""
    if experiments_data is None:
        from src.data import load_baseline_vs_interleaved
        experiments_data = load_baseline_vs_interleaved()
    bar_labels, baseline_scores, interleaved_scores, improvement_scores, color_plain_cot, color_agentic, names, layout_cfg, axis_cfg = _load_bar_data(experiments_data, style_config)
    nb, ni, nbs, nis = names
    fig = go.Figure()
    if variant == "grouped":
        _add_grouped_bars(fig, bar_labels, baseline_scores, interleaved_scores, color_plain_cot, color_agentic, nb, ni, None, None)
    else:
        _add_stacked_bars(fig, bar_labels, baseline_scores, improvement_scores, color_plain_cot, color_agentic, nbs, nis, None, None)
        fig.update_layout(barmode="stack")
    margin = layout_cfg.get("margin", dict(l=60, r=30, t=40, b=60))
    fig.update_layout(
        showlegend=True,
        height=layout_cfg.get("height", 400),
        width=layout_cfg.get("width", 520),
        margin=margin,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    
    # Apply axis configuration including ranges
    x_range = axis_cfg.get("x_range")
    y_range = axis_cfg.get("y_range")
    
    xaxis_update = {
        "title_text": axis_cfg.get("x_title", "Model"),
        "showgrid": True,
        "gridcolor": "rgba(0,0,0,0.1)"
    }
    if x_range is not None:
        xaxis_update["range"] = x_range
    
    yaxis_update = {
        "title_text": axis_cfg.get("y_title", "Score [%]"),
        "type": "linear",
        "showgrid": True,
        "gridcolor": "rgba(0,0,0,0.1)"
    }
    if y_range is not None:
        yaxis_update["range"] = y_range
    
    fig.update_xaxes(**xaxis_update)
    fig.update_yaxes(**yaxis_update)
    return fig


def create_baseline_interleaved_bars_panels(
    experiments_data: dict | None = None,
    style_config: dict | None = None,
) -> go.Figure:
    """Single figure with grouped bars showing baseline vs interleaved scores."""
    if experiments_data is None:
        from src.data import load_baseline_vs_interleaved
        experiments_data = load_baseline_vs_interleaved()
    bar_labels, baseline_scores, interleaved_scores, improvement_scores, color_plain_cot, color_agentic, names, layout_cfg, axis_cfg = _load_bar_data(experiments_data, style_config)
    nb, ni, nbs, nis = names
    fig = go.Figure()
    _add_grouped_bars(fig, bar_labels, baseline_scores, interleaved_scores, color_plain_cot, color_agentic, nb, ni, None, None)
    
    # Apply axis configuration including ranges
    x_range = axis_cfg.get("x_range")
    y_range = axis_cfg.get("y_range")
    
    # Disable vertical grid lines on grouped plot
    xaxis_update = {
        "title_text": axis_cfg.get("x_title", "Model"),
        "showgrid": False,
        "gridcolor": "rgba(0,0,0,0.1)"
    }
    if x_range is not None:
        xaxis_update["range"] = x_range
    
    yaxis_update = {
        "title_text": axis_cfg.get("y_title", "Score [%]"),
        "type": "linear",
        "showgrid": True,
        "gridcolor": "rgba(0,0,0,0.1)"
    }
    if y_range is not None:
        yaxis_update["range"] = y_range
    
    fig.update_xaxes(**xaxis_update)
    fig.update_yaxes(**yaxis_update)
    
    margin = layout_cfg.get("margin", dict(l=60, r=30, t=40, b=60))
    fig.update_layout(
        showlegend=True,
        height=layout_cfg.get("height", 400),
        width=layout_cfg.get("width", 520),
        margin=margin,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------------------------------------------------------------------------
# Horizontal timeline (team vs field milestones; data from data/timeline.json)
# ---------------------------------------------------------------------------


def _timeline_event_label(ev: Mapping[str, Any]) -> str:
    """Display string from `text` or alias `test`."""
    t = ev.get("text")
    if isinstance(t, str) and t.strip():
        return t.strip()
    t2 = ev.get("test")
    if isinstance(t2, str) and t2.strip():
        return t2.strip()
    return ""


def _timeline_anchor_y_frac(cfg: Mapping[str, Any], key: str, legacy_key: str) -> float:
    """Fraction from axis (0) to tick tip (1) where the label center sits; default mid-tick."""
    v = cfg.get(key)
    if v is not None:
        return min(1.0, max(0.05, float(v)))
    leg = cfg.get(legacy_key)
    if leg is not None:
        f = float(leg)
        if f > 1.02:
            return 0.5
        return min(1.0, max(0.05, f))
    return 0.5


def _timeline_label_slant_degrees(
    parsed: list[tuple[date, str, str, str]],
    span_days: int,
    cfg: Mapping[str, Any],
) -> list[float]:
    """
    Per-event textangle (degrees).

    ``label_slant_mode`` (default ``always``):

    - ``always``: slant every label (best for dense copy on slides).
    - ``never``: horizontal labels.
    - ``auto``: slant all labels on a placement if that side has 2+ events; otherwise
      slant when the nearest same-side neighbor is closer than the crowding gap
      (``label_crowd_min_gap_days``, else ``max(21, int(0.18 * span_days))``).
    """
    slant = float(cfg.get("label_slant_deg", -28))
    if abs(slant) < 1e-6:
        return [0.0] * len(parsed)

    mode = str(cfg.get("label_slant_mode", "always")).strip().lower()
    if mode in ("off", "none", "never", "false", "0"):
        return [0.0] * len(parsed)
    if mode in ("always", "all", "true", "1"):
        return [slant] * len(parsed)

    min_gap = cfg.get("label_crowd_min_gap_days")
    if min_gap is None:
        min_gap = max(21, int(0.18 * max(span_days, 1)))
    min_gap_i = max(1, int(min_gap))

    n = len(parsed)
    out = [0.0] * n
    by_pl: dict[str, list[int]] = {"upper": [], "lower": []}
    for i, row in enumerate(parsed):
        by_pl[row[1]].append(i)
    for idxs in by_pl.values():
        if len(idxs) >= 2:
            for i in idxs:
                out[i] = slant

    for i in range(n):
        if out[i] != 0.0:
            continue
        d_i, pl_i, _, _ = parsed[i]
        min_dist: int | None = None
        for j in range(n):
            if i == j or parsed[j][1] != pl_i:
                continue
            dist = abs((parsed[j][0] - d_i).days)
            if min_dist is None or dist < min_dist:
                min_dist = dist
        if min_dist is not None and min_dist < min_gap_i:
            out[i] = slant
    return out


def create_horizontal_timeline(
    events: list[dict] | None = None,
    style_config: dict | None = None,
) -> go.Figure:
    """
    Plotly figure: horizontal date axis, central baseline, upper and lower ticks.

    Each event dict: name, date (YYYY-MM-DD), placement (upper|lower), text or test.

    If ``events`` is None, loads ``data/timeline.json`` via ``load_timeline()``.
    Style from ``figures.timeline`` in style.yml.

    Labels use ``xanchor="center"`` and ``yanchor="middle"``. The anchor y is
    ``± tick_length × (frac + label_anchor_y_extra_tick_frac)`` from the timeline (``frac`` from
    ``label_anchor_y_frac_*``, default extra ``0.6`` = 60% of tick length past the base point).
    """
    style = style_config if style_config is not None else _load_style_yml()
    cfg = _get_figure_config("timeline", style)
    layout_cfg = cfg.get("layout") or {}
    margin = layout_cfg.get("margin", dict(l=72, r=48, t=28, b=72))
    height = layout_cfg.get("height", 320)
    width = layout_cfg.get("width", 900)
    tick_length = float(cfg.get("tick_length", 0.55))
    line_color = str(cfg.get("line_color", "rgba(60,60,60,0.9)"))
    upper_color = str(cfg.get("upper_color", "#2ECC40"))
    lower_color = str(cfg.get("lower_color", "#0074D9"))
    y_range = cfg.get("y_range", [-1.12, 1.12])
    if (
        not isinstance(y_range, (list, tuple))
        or len(y_range) != 2
        or not all(isinstance(x, (int, float)) for x in y_range)
    ):
        y_range = [-1.12, 1.12]
    x_pad_ratio = float(cfg.get("x_pad_ratio", 0.06))
    label_font_size = int(cfg.get("label_font_size", 15))
    tick_line_width = float(cfg.get("tick_line_width", 1.5))
    baseline_width = float(cfg.get("baseline_width", 2))
    anchor_y_frac_upper = _timeline_anchor_y_frac(
        cfg, "label_anchor_y_frac_upper", "upper_label_pad"
    )
    anchor_y_frac_lower = _timeline_anchor_y_frac(
        cfg, "label_anchor_y_frac_lower", "lower_label_pad"
    )
    label_anchor_y_extra_tick_frac = float(cfg.get("label_anchor_y_extra_tick_frac", 0.6))

    if events is None:
        from src.data import load_timeline

        payload = load_timeline()
        events_list = list(payload.get("events") or [])
    else:
        events_list = list(events)

    parsed: list[tuple[date, str, str, str]] = []
    for ev in events_list:
        if not isinstance(ev, dict):
            continue
        d_raw = ev.get("date")
        if not isinstance(d_raw, str):
            continue
        try:
            d = date.fromisoformat(d_raw.strip())
        except ValueError:
            continue
        pl = str(ev.get("placement", "")).strip().lower()
        if pl not in ("upper", "lower"):
            continue
        label = _timeline_event_label(ev)
        if not label:
            continue
        name = str(ev.get("name", ""))
        parsed.append((d, pl, label, name))

    parsed.sort(key=lambda row: row[0])

    fig = go.Figure()

    if not parsed:
        fig.update_layout(
            height=height,
            width=width,
            margin=margin,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    dates_only = [p[0] for p in parsed]
    min_d = min(dates_only)
    max_d = max(dates_only)
    span_days = max((max_d - min_d).days, 1)
    pad = max(1, int(round(span_days * x_pad_ratio)))
    x_min = min_d - timedelta(days=pad)
    x_max = max_d + timedelta(days=pad)

    fig.add_shape(
        type="line",
        x0=datetime(x_min.year, x_min.month, x_min.day),
        x1=datetime(x_max.year, x_max.month, x_max.day),
        y0=0,
        y1=0,
        xref="x",
        yref="y",
        line=dict(color=line_color, width=baseline_width),
    )

    slants = _timeline_label_slant_degrees(parsed, span_days, cfg)

    for k, (d, pl, label, _name) in enumerate(parsed):
        dt = datetime(d.year, d.month, d.day)
        if pl == "upper":
            y1 = tick_length
            color = upper_color
            y_text = tick_length * (anchor_y_frac_upper + label_anchor_y_extra_tick_frac)
        else:
            y1 = -tick_length
            color = lower_color
            y_text = -tick_length * (anchor_y_frac_lower + label_anchor_y_extra_tick_frac)
        fig.add_shape(
            type="line",
            x0=dt,
            x1=dt,
            y0=0,
            y1=y1,
            xref="x",
            yref="y",
            line=dict(color=color, width=tick_line_width),
        )
        label_html = f"<b>{escape(label)}</b>"
        ann: dict[str, Any] = dict(
            x=dt,
            y=y_text,
            xref="x",
            yref="y",
            text=label_html,
            showarrow=False,
            xanchor="center",
            yanchor="middle",
            font=dict(size=label_font_size, color=color),
        )
        ang = slants[k]
        if abs(ang) >= 1e-6:
            ann["textangle"] = ang
        fig.add_annotation(**ann)

    xs_hover = [datetime(p[0].year, p[0].month, p[0].day) for p in parsed]
    hovers = [
        f"<b>{escape(p[3])}</b><br>{escape(p[2])}<br>{p[0].isoformat()}"
        for p in parsed
    ]
    fig.add_trace(
        go.Scatter(
            x=xs_hover,
            y=[0.0] * len(parsed),
            mode="markers",
            marker=dict(size=16, color="rgba(0,0,0,0.01)", line=dict(width=0)),
            hovertext=hovers,
            hovertemplate="%{hovertext}<extra></extra>",
            showlegend=False,
        )
    )

    x0r = datetime(x_min.year, x_min.month, x_min.day)
    x1r = datetime(x_max.year, x_max.month, x_max.day)

    fig.update_xaxes(
        type="date",
        showgrid=True,
        gridcolor="rgba(0,0,0,0.08)",
        range=[x0r, x1r],
        tickformat="%b %Y",
        title_text="",
        automargin=True,
    )
    fig.update_yaxes(
        range=list(y_range),
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        title_text="",
    )
    fig.update_layout(
        height=height,
        width=width,
        margin=margin,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
