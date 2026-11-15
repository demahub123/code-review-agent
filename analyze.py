import csv
from pathlib import Path
from statistics import mean, stdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CONDITIONS = ["baseline", "memory", "fault"]
PROJECTS = ["sample_project", "sample_project2", "sample_project3", "sample_project4"]
LABELS = ["Project 1", "Project 2", "Project 3", "Project 4"]
OUT = Path("charts")
OUT.mkdir(exist_ok=True)

rows = []
with open("results.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({
            "condition": r["condition"], "project": r["project"],
            "success": r["success"] == "True", "steps": int(r["steps"]),
            "patches": int(r["patches"]), "tool_errors": int(r["tool_errors"]),
            "llm_error": r["llm_error"] == "True",
        })

valid = [r for r in rows if not r["llm_error"]]
print(f"Total runs: {len(rows)} | excluded for LLM outage: {len(rows) - len(valid)}")


def avg(values):
    return mean(values) if values else 0.0


def sd(values):
    return stdev(values) if len(values) > 1 else 0.0


print("\nOVERALL BY CONDITION")
print(f"{'condition':10}{'runs':>5}{'success':>9}{'steps (mean ± sd)':>20}{'patches':>9}{'tool_err':>10}")
with open("summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["condition", "runs", "success_rate", "steps_mean", "steps_sd",
                "patches_mean", "tool_errors_mean"])
    for c in CONDITIONS:
        rs = [r for r in valid if r["condition"] == c]
        steps = [r["steps"] for r in rs]
        rate = sum(r["success"] for r in rs) / len(rs) if rs else 0
        patches = avg([r["patches"] for r in rs])
        errs = avg([r["tool_errors"] for r in rs])
        print(f"{c:10}{len(rs):>5}{rate:>8.0%}{avg(steps):>12.1f} ± {sd(steps):<5.1f}{patches:>9.1f}{errs:>10.1f}")
        w.writerow([c, len(rs), round(rate, 3), round(avg(steps), 2), round(sd(steps), 2),
                    round(patches, 2), round(errs, 2)])

print("\nMEAN STEPS BY PROJECT")
print(f"{'project':18}" + "".join(f"{c:>10}" for c in CONDITIONS))
for p, label in zip(PROJECTS, LABELS):
    cells = ""
    for c in CONDITIONS:
        vals = [r["steps"] for r in valid if r["condition"] == c and r["project"] == p]
        cells += f"{avg(vals):>10.1f}"
    print(f"{label:18}{cells}")

fault_runs = [r for r in valid if r["condition"] == "fault" and r["tool_errors"] >= 1]
recovered = sum(r["success"] for r in fault_runs)
print(f"\nFAULT RECOVERY: {recovered}/{len(fault_runs)} runs with a tool error still succeeded")


def grouped_bar(metric, title, ylabel, filename):
    width = 0.26
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, c in enumerate(CONDITIONS):
        means, errs = [], []
        for p in PROJECTS:
            vals = [r[metric] for r in valid if r["condition"] == c and r["project"] == p]
            means.append(avg(vals))
            errs.append(sd(vals))
        xs = [j + (i - 1) * width for j in range(len(PROJECTS))]
        ax.bar(xs, means, width, yerr=errs, capsize=3, label=c)
    ax.set_xticks(range(len(PROJECTS)))
    ax.set_xticklabels(LABELS)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=150)
    plt.close(fig)


grouped_bar("steps", "Mean steps per run (error bars: standard deviation)", "Steps", "steps_by_project.png")
grouped_bar("patches", "Mean successful patches per run", "Patches", "patches_by_project.png")

fig, ax = plt.subplots(figsize=(6, 4))
rates = []
for c in CONDITIONS:
    rs = [r for r in valid if r["condition"] == c]
    rates.append(100 * sum(r["success"] for r in rs) / len(rs) if rs else 0)
ax.bar(CONDITIONS, rates)
ax.set_ylim(0, 105)
ax.set_ylabel("Success rate (%)")
ax.set_title("Success rate by condition")
fig.tight_layout()
fig.savefig(OUT / "success_rate.png", dpi=150)
plt.close(fig)

print("\nCharts saved in the 'charts' folder, summary saved to summary.csv")