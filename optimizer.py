"""Synthetic AI review queue: non-preemptive scheduling and staffing experiments."""
from pathlib import Path
import argparse
import heapq
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SHIFT = 480  # eight hours; no new tasks start after shift end
POLICIES = ("FIFO", "Earliest deadline", "Highest risk")


def generate_tasks(seed=42, n_tasks=100):
    """A morning arrival surge; all distributions are illustrative assumptions."""
    rng = np.random.default_rng(seed)
    early = rng.random(n_tasks) < 0.65
    arrivals = np.where(early, rng.uniform(0, 240, n_tasks),
                        rng.uniform(240, 420, n_tasks))
    kinds = rng.choice(["Factual", "Quantitative", "Safety"], n_tasks,
                       p=[0.50, 0.35, 0.15])
    medians = np.array([{"Factual": 8, "Quantitative": 15, "Safety": 20}[k]
                        for k in kinds])
    durations = np.clip(rng.lognormal(np.log(medians), 0.40), 3, 60)
    risks = np.array([{"Factual": 1, "Quantitative": 2, "Safety": 3}[k]
                      for k in kinds])
    # Deadlines vary by urgency. Deadline and risk priorities can conflict.
    windows = rng.choice([45, 90, 180], n_tasks, p=[0.25, 0.50, 0.25])
    return pd.DataFrame({"task_id": np.arange(1, n_tasks + 1),
                         "arrival": arrivals, "duration": durations,
                         "deadline": np.minimum(arrivals + windows, SHIFT),
                         "task_type": kinds, "risk": risks}).sort_values(
                             ["arrival", "task_id"]).reset_index(drop=True)


def simulate(tasks, reviewers, policy, shift=SHIFT):
    """Assign only arrived tasks to the earliest available reviewer.

    Tasks run to completion without interruption. Reviewers may finish their
    last task after the shift, but cannot start a new task at/after shift end.
    """
    if reviewers < 1 or policy not in POLICIES:
        raise ValueError("Use at least one reviewer and a supported policy.")
    required = {"task_id", "arrival", "duration", "deadline", "risk"}
    if not required.issubset(tasks.columns):
        raise ValueError("Missing required task columns.")
    if tasks.empty or tasks.task_id.duplicated().any():
        raise ValueError("Tasks must be nonempty with unique IDs.")
    if (tasks[["arrival", "duration", "deadline", "risk"]].isna().any().any()
        or not np.isfinite(tasks[["arrival", "duration", "deadline", "risk"]]).all().all()
        or (tasks.duration <= 0).any() or (tasks.arrival < 0).any()):
        raise ValueError("Task values must be finite with positive durations.")
    data = tasks.sort_values(["arrival", "task_id"]).reset_index(drop=True).copy()
    records = data.to_dict("records")
    available = [(0.0, r) for r in range(1, reviewers + 1)]
    heapq.heapify(available)
    waiting, next_task, assignments = [], 0, {}
    clock = 0.0
    while available:
        free_at, reviewer = heapq.heappop(available)
        t = max(free_at, clock)
        if not waiting and next_task < len(records):
            t = max(t, records[next_task]["arrival"])
        if t >= shift:
            break  # all remaining reviewer availability times are >= this time
        clock = t
        while next_task < len(records) and records[next_task]["arrival"] <= t:
            waiting.append(records[next_task])
            next_task += 1
        if not waiting:
            break
        if policy == "FIFO":
            key = lambda x: (x["arrival"], x["task_id"])
        elif policy == "Earliest deadline":
            key = lambda x: (x["deadline"], x["arrival"], x["task_id"])
        else:
            key = lambda x: (-x["risk"], x["deadline"], x["arrival"], x["task_id"])
        chosen = min(waiting, key=key)
        waiting.remove(chosen)
        finish = t + chosen["duration"]
        assignments[chosen["task_id"]] = (reviewer, t, finish)
        heapq.heappush(available, (finish, reviewer))
    data["reviewer"] = [assignments.get(i, (np.nan,) * 3)[0] for i in data.task_id]
    data["start"] = [assignments.get(i, (np.nan,) * 3)[1] for i in data.task_id]
    data["finish"] = [assignments.get(i, (np.nan,) * 3)[2] for i in data.task_id]
    data["wait"] = data.start - data.arrival
    data["turnaround"] = data.finish - data.arrival
    data["lateness"] = (data.finish - data.deadline).clip(lower=0)
    data["on_time"] = data.finish.le(data.deadline)
    data["completed_in_shift"] = data.finish.le(shift)
    started = data.start.notna()
    busy = (np.minimum(data.loc[started, "finish"], shift)
            - data.loc[started, "start"]).sum()
    high_risk = data.risk.eq(3)
    metrics = {
        "policy": policy, "reviewers": reviewers, "tasks": len(data),
        "on_time_rate": data.on_time.mean(),
        "completed_in_shift": int(data.completed_in_shift.sum()),
        "backlog": int((~data.completed_in_shift).sum()),
        "not_started": int((~started).sum()),
        "avg_wait_started": data.wait.mean(),
        "p95_wait_started": data.wait.quantile(0.95),
        "utilization": busy / (reviewers * shift),
        "overtime_minutes": (data.finish - shift).clip(lower=0).sum(),
        "high_risk_on_time_rate": data.loc[high_risk, "on_time"].mean(),
    }
    return data, metrics


def experiment(repeats=100, seed=42, target=0.95):
    rows = []
    for scenario, n in [("Normal", 100), ("Surge", 130)]:
        for repetition in range(repeats):
            # Same task set is reused across policies and staffing levels.
            tasks = generate_tasks(seed + repetition, n)
            for reviewers in range(2, 6):
                for policy in POLICIES:
                    _, metrics = simulate(tasks, reviewers, policy)
                    rows.append({"scenario": scenario, "seed": seed + repetition,
                                 **metrics})
    runs = pd.DataFrame(rows)
    summary = runs.groupby(["scenario", "reviewers", "policy"]).agg(
        mean_on_time=("on_time_rate", "mean"),
        p10_on_time=("on_time_rate", lambda s: s.quantile(0.10)),
        share_runs_meeting_target=("on_time_rate", lambda s: s.ge(target).mean()),
        mean_backlog=("backlog", "mean"),
        mean_wait_started=("avg_wait_started", "mean"),
        mean_utilization=("utilization", "mean"),
        mean_high_risk_on_time=("high_risk_on_time_rate", "mean"),
        mean_overtime_minutes=("overtime_minutes", "mean"),
    ).reset_index()
    return runs, summary


def make_charts(summary, sample, output):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, scenario in zip(axes, ["Normal", "Surge"]):
        for policy in POLICIES:
            part = summary[(summary.scenario == scenario) & (summary.policy == policy)]
            ax.plot(part.reviewers, part.mean_on_time * 100, marker="o", label=policy)
        ax.axhline(95, color="gray", ls="--", label="95% target")
        ax.set(title=f"{scenario} workload", xlabel="Reviewers", xticks=range(2, 6), ylim=(0, 102))
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Mean on-time completion (%)")
    axes[1].legend(fontsize=8)
    fig.suptitle("Synthetic AI review operations — 100/130 tasks per day")
    fig.tight_layout()
    fig.savefig(output / "staffing_comparison.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4))
    colors = {1: "#3578b8", 2: "#df9b20", 3: "#b74646"}
    for row in sample.itertuples():
        if pd.notna(row.start):
            ax.barh(row.reviewer, row.duration, left=row.start, height=0.6,
                    color=colors[row.risk], edgecolor="white", linewidth=0.3)
    ax.axvline(SHIFT, color="black", ls="--")
    ax.set(xlabel="Minutes after shift start", ylabel="Reviewer", yticks=[1, 2, 3],
           title="Sample: earliest deadline, 3 reviewers (blue/amber/red = risk 1/2/3)")
    fig.tight_layout()
    fig.savefig(output / "sample_schedule.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    tasks = generate_tasks(args.seed)
    tasks.to_csv(args.output / "sample_tasks.csv", index=False)
    sample, _ = simulate(tasks, 3, "Earliest deadline")
    sample.to_csv(args.output / "sample_schedule.csv", index=False)
    runs, summary = experiment(args.repeats, args.seed)
    runs.to_csv(args.output / "all_runs.csv", index=False)
    summary.to_csv(args.output / "comparison_summary.csv", index=False)
    make_charts(summary, sample, args.output)
    lines = ["SYNTHETIC RESULTS — assumptions, not observed business outcomes.",
             f"{args.repeats} seeded days per scenario; 95% on-time daily target.",
             "Planning rule: meet the daily target in at least 90% of simulated days."]
    for scenario in ["Normal", "Surge"]:
        eligible = summary[(summary.scenario == scenario)
                           & (summary.share_runs_meeting_target >= 0.90)]
        if eligible.empty:
            lines.append(f"{scenario}: no tested option meets the planning rule.")
        else:
            best = eligible.sort_values(["reviewers", "mean_on_time", "mean_wait_started"],
                                        ascending=[True, False, True]).iloc[0]
            lines.append(f"{scenario}: {best.reviewers} reviewers / {best.policy}; "
                         f"mean on-time {best.mean_on_time:.1%}, "
                         f"days meeting target {best.share_runs_meeting_target:.1%}.")
    lines.append("The selection minimizes headcount within 2–5 reviewers; it is not a global optimum.")
    (args.output / "findings.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"Results saved to {args.output.resolve()}")


if __name__ == "__main__":
    main()
