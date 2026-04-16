"""
Visualizer module for Auto-RAG-Optimizer.
Reads research_log.md and generates charts showing experiment progress,
parameter impact analysis, and convergence tracking.

Usage:
    python visualizer.py                    # generate all charts
    python visualizer.py --html             # also generate HTML dashboard
"""

import re
import argparse
import logging
from pathlib import Path
from typing import Optional
from io import StringIO

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
RESEARCH_LOG_PATH = BASE_DIR / "research_log.md"
CHARTS_DIR = BASE_DIR / "charts"

# Consistent styling
sns.set_theme(style="whitegrid", palette="muted")
COLORS = {
    "keep": "#2ecc71",
    "discard": "#cccccc",
    "crash": "#e74c3c",
    "baseline": "#3498db",
    "best_line": "#27ae60",
}


def parse_research_log(log_path: Optional[Path] = None) -> pd.DataFrame:
    """Parse the markdown table in research_log.md into a DataFrame."""
    log_path = log_path or RESEARCH_LOG_PATH

    if not log_path.exists():
        raise FileNotFoundError(f"Research log not found: {log_path}")

    text = log_path.read_text()

    # Extract markdown table lines (lines starting with |, skip separator lines)
    table_lines = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and not line.startswith("|---"):
            table_lines.append(line)

    if len(table_lines) < 2:
        raise ValueError("Research log has no experiment data yet.")

    # Parse header
    header = [h.strip() for h in table_lines[0].split("|") if h.strip()]

    # Parse rows
    rows = []
    for line in table_lines[1:]:
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) == len(header):
            rows.append(cells)

    df = pd.DataFrame(rows, columns=header)

    # Convert numeric columns
    numeric_cols = [
        "experiment_id", "chunk_size", "chunk_overlap", "top_k",
        "temperature", "faithfulness", "answer_relevance", "avg_score",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalize status
    if "status" in df.columns:
        df["status"] = df["status"].str.strip().str.lower()

    return df


def plot_score_progression(df: pd.DataFrame, save_path: Optional[Path] = None) -> None:
    """Plot avg_score over experiments with keep/discard/crash markers."""
    fig, ax = plt.subplots(figsize=(16, 8))

    # Separate by status
    for status, color in COLORS.items():
        mask = df["status"] == status
        subset = df[mask]
        if subset.empty:
            continue

        size = 60 if status == "keep" else (30 if status == "discard" else 40)
        marker = "o" if status in ("keep", "baseline") else ("x" if status == "crash" else "o")
        edge = "black" if status in ("keep", "baseline") else "none"
        alpha = 1.0 if status in ("keep", "baseline") else 0.5

        ax.scatter(
            subset.index, subset["avg_score"],
            c=color, s=size, marker=marker, alpha=alpha,
            edgecolors=edge, linewidths=0.5, zorder=3,
            label=status.capitalize(),
        )

    # Running best line (from kept experiments)
    kept = df[df["status"].isin(["keep", "baseline"])].copy()
    if not kept.empty:
        running_best = kept["avg_score"].cummax()
        ax.step(
            kept.index, running_best, where="post",
            color=COLORS["best_line"], linewidth=2.5, alpha=0.8,
            zorder=2, label="Running Best",
        )

        # Annotate best score
        best_idx = kept["avg_score"].idxmax()
        best_val = kept.loc[best_idx, "avg_score"]
        ax.annotate(
            f"Best: {best_val:.4f}",
            (best_idx, best_val),
            textcoords="offset points", xytext=(10, 10),
            fontsize=10, fontweight="bold", color=COLORS["best_line"],
            arrowprops=dict(arrowstyle="->", color=COLORS["best_line"], lw=1.5),
        )

    ax.set_xlabel("Experiment #", fontsize=12)
    ax.set_ylabel("Average Score (higher is better)", fontsize=12)
    ax.set_title(
        f"Auto-RAG-Optimizer Progress: {len(df)} Experiments",
        fontsize=14, fontweight="bold",
    )
    ax.legend(loc="lower right", fontsize=10)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.4f"))

    plt.tight_layout()
    path = save_path or CHARTS_DIR / "score_progression.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {path}")


def plot_metric_breakdown(df: pd.DataFrame, save_path: Optional[Path] = None) -> None:
    """Plot faithfulness and answer_relevance side by side over time."""
    valid = df[df["status"] != "crash"].copy().reset_index(drop=True)
    if valid.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

    for ax, metric, color in zip(
        axes,
        ["faithfulness", "answer_relevance"],
        ["#3498db", "#e67e22"],
    ):
        ax.scatter(
            valid.index, valid[metric],
            c=color, s=30, alpha=0.6, edgecolors="white", linewidths=0.3,
        )

        # Highlight kept
        kept = valid[valid["status"].isin(["keep", "baseline"])]
        ax.scatter(
            kept.index, kept[metric],
            c=color, s=60, edgecolors="black", linewidths=0.5, zorder=4,
        )

        # Running best for kept
        if not kept.empty:
            running = kept[metric].cummax()
            ax.step(kept.index, running, where="post", color=color, linewidth=2, alpha=0.7)

        ax.set_xlabel("Experiment #", fontsize=11)
        ax.set_ylabel(metric.replace("_", " ").title(), fontsize=11)
        ax.set_title(metric.replace("_", " ").title(), fontsize=12, fontweight="bold")

    fig.suptitle("Metric Breakdown Over Time", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = save_path or CHARTS_DIR / "metric_breakdown.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {path}")


def plot_parameter_impact(df: pd.DataFrame, save_path: Optional[Path] = None) -> None:
    """Show how each tunable parameter correlates with avg_score."""
    numeric_params = ["chunk_size", "chunk_overlap", "top_k", "temperature"]
    available = [p for p in numeric_params if p in df.columns]

    valid = df[df["status"] != "crash"].copy()
    if valid.empty or not available:
        return

    n = len(available)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
    if n == 1:
        axes = [axes]

    for ax, param in zip(axes, available):
        data = valid.dropna(subset=[param, "avg_score"])
        ax.scatter(
            data[param], data["avg_score"],
            c=data["avg_score"], cmap="RdYlGn", s=40,
            edgecolors="gray", linewidths=0.3, alpha=0.8,
        )

        # Trend line
        if len(data) >= 3:
            try:
                z = pd.np.polyfit(data[param], data["avg_score"], 1)
                p = pd.np.poly1d(z)
                x_line = sorted(data[param].unique())
                ax.plot(x_line, p(x_line), "--", color="gray", alpha=0.5, linewidth=1)
            except Exception:
                pass

        ax.set_xlabel(param.replace("_", " ").title(), fontsize=11)
        ax.set_ylabel("Avg Score", fontsize=11)
        ax.set_title(f"{param}", fontsize=11, fontweight="bold")

    fig.suptitle("Parameter Impact on Score", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = save_path or CHARTS_DIR / "parameter_impact.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {path}")


def plot_status_summary(df: pd.DataFrame, save_path: Optional[Path] = None) -> None:
    """Pie chart of experiment outcomes."""
    counts = df["status"].value_counts()
    color_map = {k: v for k, v in COLORS.items() if k in counts.index}
    colors = [color_map.get(s, "#999999") for s in counts.index]

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=[s.capitalize() for s in counts.index],
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 12},
    )
    for at in autotexts:
        at.set_fontweight("bold")

    total = len(df)
    kept = counts.get("keep", 0) + counts.get("baseline", 0)
    ax.set_title(
        f"Experiment Outcomes ({total} total, {kept} kept)",
        fontsize=14, fontweight="bold",
    )

    plt.tight_layout()
    path = save_path or CHARTS_DIR / "status_summary.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {path}")


def plot_categorical_impact(df: pd.DataFrame, save_path: Optional[Path] = None) -> None:
    """Box plots showing avg_score distribution per categorical parameter."""
    cat_params = ["embedding_model", "llm_model", "search_type", "splitter"]
    available = [p for p in cat_params if p in df.columns]

    valid = df[df["status"] != "crash"].copy()
    if valid.empty or not available:
        return

    n = len(available)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
    if n == 1:
        axes = [axes]

    for ax, param in zip(axes, available):
        data = valid.dropna(subset=[param, "avg_score"])
        if data[param].nunique() < 2:
            ax.text(0.5, 0.5, "Only 1 value tested", ha="center", va="center",
                    transform=ax.transAxes, fontsize=11, color="gray")
            ax.set_title(param, fontsize=11, fontweight="bold")
            continue

        sns.boxplot(data=data, x=param, y="avg_score", ax=ax, palette="Set2")
        ax.set_xlabel(param.replace("_", " ").title(), fontsize=10)
        ax.set_ylabel("Avg Score", fontsize=10)
        ax.set_title(param, fontsize=11, fontweight="bold")
        ax.tick_params(axis="x", rotation=20, labelsize=8)

    fig.suptitle("Categorical Parameter Impact", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = save_path or CHARTS_DIR / "categorical_impact.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {path}")


def generate_html_dashboard(df: pd.DataFrame, save_path: Optional[Path] = None) -> None:
    """Generate a self-contained HTML dashboard linking all charts."""
    path = save_path or CHARTS_DIR / "dashboard.html"

    kept = df[df["status"].isin(["keep", "baseline"])]
    best_score = kept["avg_score"].max() if not kept.empty else 0.0
    baseline_score = df.iloc[0]["avg_score"] if len(df) > 0 else 0.0
    improvement = best_score - baseline_score

    chart_files = [
        ("Score Progression", "score_progression.png"),
        ("Metric Breakdown", "metric_breakdown.png"),
        ("Parameter Impact", "parameter_impact.png"),
        ("Categorical Impact", "categorical_impact.png"),
        ("Status Summary", "status_summary.png"),
    ]

    charts_html = ""
    for title, fname in chart_files:
        fpath = CHARTS_DIR / fname
        if fpath.exists():
            charts_html += f"""
        <div class="chart-card">
            <h2>{title}</h2>
            <img src="{fname}" alt="{title}">
        </div>"""

    # Build the kept experiments table
    kept_rows = ""
    for _, row in kept.iterrows():
        kept_rows += f"""
            <tr>
                <td>{int(row.get('experiment_id', 0))}</td>
                <td>{row.get('chunk_size', '')}</td>
                <td>{row.get('chunk_overlap', '')}</td>
                <td>{row.get('top_k', '')}</td>
                <td>{row.get('embedding_model', '')}</td>
                <td>{row.get('temperature', '')}</td>
                <td>{row.get('faithfulness', 0):.4f}</td>
                <td>{row.get('answer_relevance', 0):.4f}</td>
                <td><strong>{row.get('avg_score', 0):.4f}</strong></td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Auto-RAG-Optimizer Dashboard</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #f0f2f5; color: #333; padding: 24px; }}
    .header {{ text-align: center; margin-bottom: 32px; }}
    .header h1 {{ font-size: 28px; color: #1a1a2e; }}
    .header p {{ color: #666; margin-top: 8px; }}
    .stats {{ display: flex; gap: 16px; justify-content: center; margin-bottom: 32px; flex-wrap: wrap; }}
    .stat-card {{ background: white; border-radius: 12px; padding: 20px 32px;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; min-width: 180px; }}
    .stat-card .value {{ font-size: 28px; font-weight: 700; color: #27ae60; }}
    .stat-card .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
    .chart-card {{ background: white; border-radius: 12px; padding: 24px;
                   box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }}
    .chart-card h2 {{ font-size: 18px; margin-bottom: 16px; color: #1a1a2e; }}
    .chart-card img {{ width: 100%; height: auto; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
    th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
    tr:hover {{ background: #f8fff8; }}
</style>
</head>
<body>
    <div class="header">
        <h1>Auto-RAG-Optimizer Dashboard</h1>
        <p>Autonomous RAG configuration optimization results</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="value">{len(df)}</div>
            <div class="label">Total Experiments</div>
        </div>
        <div class="stat-card">
            <div class="value">{len(kept)}</div>
            <div class="label">Kept Improvements</div>
        </div>
        <div class="stat-card">
            <div class="value">{baseline_score:.4f}</div>
            <div class="label">Baseline Score</div>
        </div>
        <div class="stat-card">
            <div class="value">{best_score:.4f}</div>
            <div class="label">Best Score</div>
        </div>
        <div class="stat-card">
            <div class="value" style="color: {'#27ae60' if improvement > 0 else '#e74c3c'}">
                {'+' if improvement >= 0 else ''}{improvement:.4f}
            </div>
            <div class="label">Total Improvement</div>
        </div>
    </div>

    {charts_html}

    <div class="chart-card">
        <h2>Kept Experiments</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th><th>Chunk Size</th><th>Overlap</th><th>Top K</th>
                    <th>Embedding</th><th>Temp</th>
                    <th>Faithfulness</th><th>Relevance</th><th>Avg Score</th>
                </tr>
            </thead>
            <tbody>{kept_rows}</tbody>
        </table>
    </div>
</body>
</html>"""

    path.write_text(html)
    logger.info(f"Saved HTML dashboard: {path}")


def generate_all_charts(html: bool = False) -> None:
    """Parse log and generate all visualization charts."""
    CHARTS_DIR.mkdir(exist_ok=True)

    df = parse_research_log()
    logger.info(f"Parsed {len(df)} experiments from research log.")

    plot_score_progression(df)
    plot_metric_breakdown(df)
    plot_parameter_impact(df)
    plot_categorical_impact(df)
    plot_status_summary(df)

    if html:
        generate_html_dashboard(df)

    logger.info(f"All charts saved to {CHARTS_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-RAG-Optimizer Visualizer")
    parser.add_argument("--html", action="store_true", help="Generate HTML dashboard")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    generate_all_charts(html=args.html)
    print(f"Charts saved to {CHARTS_DIR}/")
