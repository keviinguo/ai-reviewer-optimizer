# AI Review Queue & Staffing Optimizer

A Python simulation that compares scheduling strategies and staffing levels for an AI review team. The project examines how task prioritization and reviewer capacity affect deadline compliance, waiting times, and backlog.

## Motivation

My experience evaluating AI responses prompted me to explore how review teams could manage uneven workloads and competing priorities. This project uses synthetic tasks to test those operational decisions.

All inputs are hypothetical. No internal Handshake data is used, and the results do not represent observed business improvements.

## Business Question

What is the smallest tested team that can complete at least 95% of tasks by their deadlines on at least 90% of simulated days?

## Tools

- Python
- NumPy: random task generation
- Pandas: task tracking and performance summaries
- Matplotlib: staffing comparisons and reviewer timelines
- heapq: tracking reviewer availability

## Methodology

Each task has an arrival time, review duration, deadline, task type, and risk score.

The simulation compares three scheduling strategies:

| Strategy | Assignment rule |
|----------|-----------------|
| First-in-first-out (FIFO) | Review the earliest-arriving task first |
| Earliest deadline | Review the task with the closest deadline first |
| Highest risk | Review the highest-risk task first |

Each strategy is tested with two through five reviewers under two workloads:

- Normal demand: 100 tasks per day
- Surge demand: 130 tasks per day

The experiment generates 100 days per workload. Within each day, every scheduling and staffing option receives the same task list, producing 2,400 simulations.

## Assumptions

- Each shift lasts eight hours.
- Task arrivals are uneven, with an assumed morning surge.
- Review durations follow a lognormal distribution and vary by task type.
- All reviewers work at the same speed and can handle every task type.
- Reviews cannot be interrupted once started.
- Tasks may finish after shift end, but no new task starts after the shift.
- Breaks, rework, quality differences, and multi-day backlog are not modeled.

## Performance Metrics

- On-time completion rate
- End-of-shift backlog
- Average waiting time among started tasks
- Reviewer utilization
- Overtime minutes
- High-risk task deadline compliance
- Percentage of days meeting the service target

Unstarted tasks count as failures when calculating on-time completion.

## Results

The default experiment selected four reviewers using earliest-deadline scheduling as the smallest tested team meeting the planning rule under both workloads.

| Workload | Mean on-time completion | Days meeting the 95% target |
|----------|-------------------------|----------------------------|
| Normal | 99.9% | 100 of 100 |
| Surge | 97.9% | 90 of 100 |

Under normal demand with three reviewers, earliest-deadline scheduling averaged 95.6% on-time completion, compared with 83.7% for FIFO. However, it achieved the daily target on only 80% of simulated days.

This illustrates why average performance alone may be insufficient for staffing decisions.

![Staffing comparison](results/staffing_comparison.png)

![Example reviewer schedule](results/sample_schedule.png)

## How to Run

Install Python 3.10 or newer, then install the dependencies:

    python -m pip install -r requirements.txt

Run the simulation:

    python optimizer.py

For a shorter experiment:

    python optimizer.py --repeats 10

Run the automated checks:

    python -m unittest test_optimizer.py -v

## Project Files

| File | Description |
|------|-------------|
| optimizer.py | Task generation, scheduling simulation, experiments, and charts |
| requirements.txt | Python dependencies |
| test_optimizer.py | Checks for scheduling behavior and metric calculations |
| results/sample_tasks.csv | One generated day's tasks |
| results/sample_schedule.csv | Task assignments and completion times |
| results/all_runs.csv | Metrics for every simulation |
| results/comparison_summary.csv | Performance summaries by workload, staffing, and strategy |
| results/findings.txt | Staffing recommendations |
| results/*.png | Comparison and schedule charts |

## Limitations

The recommendation depends on assumed task arrivals, durations, and deadlines. It minimizes headcount only among the tested options and does not solve a global optimization problem.

Prioritizing high-risk tasks measures timely coverage, not review quality. The surge result meets the reliability threshold exactly in this sample; additional simulations and sensitivity analysis would help assess its stability.

## Future Improvements

- Model reviewer breaks and skill restrictions
- Add labor costs and overtime limits
- Carry unfinished tasks into subsequent days
- Test different arrival patterns and deadline requirements
- Validate assumptions using an authorized operational dataset
