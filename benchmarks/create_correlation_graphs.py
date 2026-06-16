import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

CSV_PATH = SCRIPT_DIR / "results.csv"
FIGURE_DIR = PROJECT_ROOT / "figures"

if not CSV_PATH.exists():
    raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

FIGURE_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV_PATH)

summary = (
    df.groupby(["operation", "api"], as_index=False)
    .agg({
        "average_latency_ms": "mean",
        "energy_per_request_kwh": "mean",
    })
)

summary["energy_per_request_uwh"] = summary["energy_per_request_kwh"] * 1_000_000_000

correlation = summary["average_latency_ms"].corr(summary["energy_per_request_uwh"])

x = summary["average_latency_ms"]
y = summary["energy_per_request_uwh"]

slope, intercept = np.polyfit(x, y, 1)
line_x = np.linspace(x.min(), x.max(), 100)
line_y = slope * line_x + intercept

plt.figure(figsize=(7, 4.5))

markers = {
    "REST": "o",
    "GraphQL": "s",
    "gRPC": "^",
}

for api in ["REST", "GraphQL", "gRPC"]:
    api_data = summary[summary["api"] == api]

    plt.scatter(
        api_data["average_latency_ms"],
        api_data["energy_per_request_uwh"],
        label=api,
        marker=markers[api],
        s=70,
        facecolors="white",
        edgecolors="black",
        linewidths=1.2,
    )

plt.plot(
    line_x,
    line_y,
    color="black",
    linestyle="--",
    linewidth=1,
    label="Trend line",
)

for _, row in summary.iterrows():
    label = row["operation"].replace("_task", "").replace("get_", "get ")

    plt.annotate(
        label,
        (row["average_latency_ms"], row["energy_per_request_uwh"]),
        textcoords="offset points",
        xytext=(4, 4),
        fontsize=7,
        color="black",
    )

plt.xlabel("Average latency (ms)")
plt.ylabel("Energy per request (µWh)")
plt.legend(title="API")
plt.grid(True, linestyle=":", linewidth=0.6)

plt.tight_layout()

pdf_path = FIGURE_DIR / "latency_energy_correlation_bw.pdf"
png_path = FIGURE_DIR / "latency_energy_correlation_bw.png"

plt.savefig(pdf_path, format="pdf")
plt.savefig(png_path, dpi=300)
plt.close()

print(f"Correlation: {correlation:.4f}")
print(f"Saved: {pdf_path}")
print(f"Saved: {png_path}")