import os
import sys
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.seasonal import seasonal_decompose

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent
PLOTS_DIR = DATA_DIR / "plots"
PLOTS_DIR.mkdir(exist_ok=True)

# Find all CSVs in the workspace (excluding analysis/comparison files)
def get_stock_csvs():
    return [f for f in DATA_DIR.glob("*.csv") if f.name not in ["comparison_stats.txt", "analysis_summary.txt", "google_analysis_summary.txt"]]

def load_stock_data(path: Path) -> pd.DataFrame:
    # Try to detect the date column automatically (case-insensitive, flexible)
    import csv
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader)
    date_col = None
    for col in header:
        if 'date' in col.strip().lower():
            date_col = col.strip()
            break
    if not date_col:
        # Try common alternatives
        for col in header:
            if 'time' in col.strip().lower() or 'day' in col.strip().lower():
                date_col = col.strip()
                break
    if not date_col:
        raise ValueError(f"No date-like column found in {path}. Please ensure your CSV has a 'Date' column or similar.")
    try:
        df = pd.read_csv(path, parse_dates=[date_col], comment='/', dayfirst=False, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(path, parse_dates=[date_col], comment='/', dayfirst=False, encoding='ISO-8859-1')
    df.columns = [c.strip() for c in df.columns]
    num_cols = [c for c in df.columns if c.lower() != date_col.lower()]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(how="all")
    if date_col in df.columns:
        df = df.set_index(date_col).sort_index()
    return df

def feature_engineer(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.ffill()
    if "Close" in df.columns:
        df["Daily_Return"] = df["Close"].pct_change()
        df["Log_Return"] = np.log(df["Close"]).diff()
        df["MA_20"] = df["Close"].rolling(20).mean()
        df["MA_50"] = df["Close"].rolling(50).mean()
        df["MA_200"] = df["Close"].rolling(200).mean()
    return df

def descriptive_stats(df: pd.DataFrame) -> str:
    parts = []
    parts.append("Basic info:\n")
    parts.append(f"Start: {df.index.min()}\nEnd: {df.index.max()}\nRows: {len(df)}\n")
    if "Close" in df.columns:
        close = df["Close"].dropna()
        parts.append("\nClose price stats:\n")
        parts.append(close.describe().to_string())
        parts.append("\n\n")
    if "Daily_Return" in df.columns:
        r = df["Daily_Return"].dropna()
        parts.append("Returns stats:\n")
        parts.append(r.describe().to_string())
        annual_vol = r.std() * np.sqrt(252)
        parts.append(f"\nAnnualized volatility (approx): {annual_vol:.4f}\n")
    return "\n".join(parts)

def plot_price_and_ma(df: pd.DataFrame, prefix):
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["Close"], label="Close", linewidth=1)
    for ma in ("MA_20", "MA_50", "MA_200"):
        if ma in df.columns:
            plt.plot(df.index, df[ma], label=ma, linewidth=1)
    plt.title(f"{prefix} Close Price and Moving Averages")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    f = PLOTS_DIR / f"{prefix}_price_ma.png"
    plt.savefig(f)
    plt.close()

def plot_volume(df: pd.DataFrame, prefix):
    if "Volume" not in df.columns:
        return
    plt.figure(figsize=(12, 3))
    plt.bar(df.index, df["Volume"], width=1.0)
    plt.title(f"{prefix} Volume")
    plt.xlabel("Date")
    plt.tight_layout()
    f = PLOTS_DIR / f"{prefix}_volume.png"
    plt.savefig(f)
    plt.close()

def plot_returns_distribution(df: pd.DataFrame, prefix):
    if "Daily_Return" not in df.columns:
        return
    r = df["Daily_Return"].dropna()
    plt.figure(figsize=(10, 4))
    sns.histplot(r, bins=80, kde=True)
    plt.title(f"{prefix} Histogram of Daily Returns")
    plt.tight_layout()
    f = PLOTS_DIR / f"{prefix}_returns_hist.png"
    plt.savefig(f)
    plt.close()
    plt.figure(figsize=(6, 6))
    sns.boxplot(x=r)
    plt.title(f"{prefix} Returns Boxplot")
    plt.tight_layout()
    f = PLOTS_DIR / f"{prefix}_returns_box.png"
    plt.savefig(f)
    plt.close()

def resample_and_plot_monthly(df: pd.DataFrame, prefix):
    if "Close" not in df.columns:
        return
    monthly = df["Close"].resample("M").last()
    plt.figure(figsize=(12, 5))
    plt.plot(monthly.index, monthly, marker="o")
    plt.title(f"{prefix} Monthly Close (last trading day of month)")
    plt.tight_layout()
    f = PLOTS_DIR / f"{prefix}_monthly_close.png"
    plt.savefig(f)
    plt.close()

def correlation_heatmap(df: pd.DataFrame, prefix):
    cols = [c for c in ("Open", "High", "Low", "Close", "Volume", "Daily_Return") if c in df.columns]
    if not cols:
        return
    corr = df[cols].corr()
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
    plt.title(f"{prefix} Correlation")
    plt.tight_layout()
    f = PLOTS_DIR / f"{prefix}_correlation.png"
    plt.savefig(f)
    plt.close()

def seasonal_decompose_and_plot(df: pd.DataFrame, prefix):
    if "Close" not in df.columns:
        return
    series = df["Close"].resample("D").last().interpolate()
    try:
        decomp = seasonal_decompose(series, model="multiplicative", period=365)
    except Exception:
        decomp = seasonal_decompose(series, model="additive", period=252)
    plt.rcParams.update({"figure.figsize": (10, 8)})
    decomp.plot().suptitle(f"{prefix} Seasonal Decompose of Close (daily, interpolated)")
    f = PLOTS_DIR / f"{prefix}_seasonal_decompose.png"
    plt.tight_layout()
    plt.savefig(f)
    plt.close()

def analyze_stock(csv_path: Path):
    stock_name = csv_path.stem.replace('_stock_data', '').replace('_5yr_one', '').replace('google', 'Google').replace('Netflix', 'Netflix')
    df = load_stock_data(csv_path)
    df = feature_engineer(df)
    summary = descriptive_stats(df)
    # Save summary
    summary_path = DATA_DIR / f"{stock_name}_analysis_summary.txt"
    summary_path.write_text(summary)
    # Plots
    plot_price_and_ma(df, stock_name)
    plot_volume(df, stock_name)
    plot_returns_distribution(df, stock_name)
    resample_and_plot_monthly(df, stock_name)
    correlation_heatmap(df, stock_name)
    seasonal_decompose_and_plot(df, stock_name)
    return stock_name, summary_path

def compare_stocks(df1, df2, label1, label2):
    stats = {}
    for label, df in [(label1, df1), (label2, df2)]:
        close = df["Close"].dropna()
        stats[label] = {
            "mean": close.mean(),
            "std": close.std(),
            "min": close.min(),
            "max": close.max(),
            "annual_volatility": df["Daily_Return"].std() * np.sqrt(252) if "Daily_Return" in df.columns else None
        }
    return stats

def plot_comparison(df1, df2, label1, label2):
    plt.figure(figsize=(12,6))
    plt.plot(df1.index, df1["Close"], label=label1)
    plt.plot(df2.index, df2["Close"], label=label2)
    plt.title(f"{label1} vs {label2} Close Price")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    f = PLOTS_DIR / f"{label1}_vs_{label2}.png"
    plt.savefig(f)
    plt.close()

def main():
    csvs = get_stock_csvs()
    stock_info = []
    dfs = {}
    for csv_path in csvs:
        stock_name, summary_path = analyze_stock(csv_path)
        stock_info.append((stock_name, summary_path))
        dfs[stock_name] = feature_engineer(load_stock_data(csv_path))
    # Pairwise comparison (for 2 stocks)
    if len(stock_info) == 2:
        label1, _ = stock_info[0]
        label2, _ = stock_info[1]
        df1 = dfs[label1]
        df2 = dfs[label2]
        plot_comparison(df1, df2, label1, label2)
        stats = compare_stocks(df1, df2, label1, label2)
        with open(DATA_DIR / "comparison_stats.txt", "w") as f:
            for label in stats:
                f.write(f"{label} stats:\n")
                for k, v in stats[label].items():
                    f.write(f"  {k}: {v}\n")
                f.write("\n")
    print("Analysis complete. Plots saved to", PLOTS_DIR)
    print("Summaries written for:", ', '.join([s[0] for s in stock_info]))
    if len(stock_info) == 2:
        print("Comparison written to comparison_stats.txt")
        

if __name__ == "__main__":
    main()