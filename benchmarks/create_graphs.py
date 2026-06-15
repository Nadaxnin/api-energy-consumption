import pandas as pd
import matplotlib.pyplot as plt 
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "benchmarks" / "results.csv"
FIGURE_DIR = PROJECT_ROOT / "figures"

FIGURE_DIR.mkdir(exist_ok=True)

df = pd.read_csv(CSV_PATH)

summary = (
    df.groupby(["operation", "api"], as_index=False)
    .agg({
        "average_latency_ms": "mean",
        "throughput_requests_per_second": "mean",
        "energy_per_request_kwh": "mean",
    })
)

# convert kWh to µWh (kWh * 1e9 = µWh)
summary["energy_per_request_uwh"] = (
    summary["energy_per_request_kwh"] * int(1e9)
)

operation_order = [
    "get_all_tasks",
    "get_one_task",
    "create_task",
    "update_task",
    "delete_task",
]

api_order = ["REST", "GraphQL", "gRPC"]

summary["operation"] = pd.Categorical(
    summary["operation"],
    categories=operation_order,
    ordered=True,
)

summary["api"] = pd.Categorical(
    summary["api"],
    categories=api_order,
    ordered=True,
)

summary = summary.sort_values(["operation", "api"])


def make_bar_chart(metric, ylabel, title, output_name):
    pivot = summary.pivot(index="operation", columns="api", values=metric)
    pivot = pivot[api_order]

    ax = pivot.plot(kind="bar", figsize=(8, 4.5))

    ax.set_title(title)
    ax.set_xlabel("Operation")
    ax.set_ylabel(ylabel)
    ax.legend(title="API")
    ax.set_xticklabels(
        ["Get all", "Get one", "Create", "Update", "Delete"],
        rotation=0,
    )

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / output_name, format="pdf")
    plt.savefig(FIGURE_DIR / output_name.replace(".pdf", ".png"), dpi=300)
    plt.close()


make_bar_chart(
    "average_latency_ms",
    "Average latency (ms)",
    "Average latency by API paradigm",
    "average_latency_by_api.pdf",
)

make_bar_chart(
    "throughput_requests_per_second",
    "Throughput (requests/s)",
    "Throughput by API paradigm",
    "throughput_by_api.pdf",
)

make_bar_chart(
    "energy_per_request_uwh",
    "Energy per request (µWh)",
    "Estimated energy per request by API paradigm",
    "energy_per_request_by_api.pdf",
)

print("Graphs saved in the figures folder.")