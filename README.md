# AI Review Queue & Staffing Optimizer

A Python operations project comparing staffing and scheduling decisions for a
synthetic AI review team. It uses a discrete-event simulation, rather than a
machine-learning model. No confidential Handshake data is used.

## Run it

1. Install Python 3.10 or newer.
2. Extract this folder and open a terminal in it. On Windows, open the folder,
   click the address bar, type `cmd`, and press Enter.
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Run: `python optimizer.py`
5. Open the PNG charts and CSV tables in the `results` folder.

If Windows uses the Python launcher, replace `python` with `py`.
For a quicker run: `python optimizer.py --repeats 10`
For more simulated days: `python optimizer.py --repeats 500 --seed 42`
Run checks: `python -m unittest test_optimizer.py -v`

Precomputed results from the default 100-day experiment are included, so you can
inspect the project without running anything first. Dependency ranges are not
an exact environment lock; minor differences can occur across library versions.

## The business question

How many reviewers should be scheduled, and which waiting task should they
handle next, to complete at least 95% of tasks by their deadlines?

The staffing decision uses a second criterion: the 95% daily target must be met
in at least 90% of simulated days. This avoids choosing a team solely because its
average day looks good. Both targets are illustrative management assumptions.

## What a task contains

| Field | Meaning |
|---|---|
| task_id | Unique identifier |
| arrival | Minutes after shift start when the task enters the queue |
| duration | Required review time in minutes |
| deadline | Latest acceptable completion time |
| task_type | Factual, quantitative, or safety review |
| risk | Illustrative priority score: 1, 2, or 3 |

The normal workload has 100 tasks; the surge workload has 130. Each shift is
480 minutes. Tasks arrive within the first 420 minutes. On average, 65% arrive
in the first four hours, creating an uneven workload.

Task types are sampled with probabilities 50%, 35%, and 15%. Their assumed
median durations are 8, 15, and 20 minutes, respectively. Durations follow a
lognormal distribution with log-scale standard deviation 0.4 and are clipped
to 3–60 minutes. Risk scores are assigned by type, not estimated from data.
Deadline windows are randomly selected from 45, 90, and 180 minutes, with
probabilities 25%, 50%, and 25%, and capped at shift end.

These are hypothetical assumptions, not measurements of AI review work.

## How the simulation works

1. Generate one day's task list using a random seed.
2. Track when each reviewer becomes available.
3. Move time to the next reviewer availability or task arrival as needed.
4. Select a task only from tasks that have already arrived and are waiting.
5. Assign it to an available reviewer and calculate its finish time.
6. Repeat until no work remains or no reviewer can start before shift end.

Once started, a task cannot be interrupted. All reviewers have equal speed and
can review every task type. A task started before minute 480 may finish after
the shift; that overtime is reported. No new work starts at minute 480 or later.
Missed-deadline tasks stay in the queue and may still be processed.

The simulation knows the generated task duration when reporting finish time,
but the scheduling policies do not prioritize using duration. It does not
model uncertain estimates, breaks, quality differences, rework, or multi-day
backlog carryover.

## The three policies

| Policy | Selection rule | Business tradeoff |
|---|---|---|
| FIFO | Earliest arrival first | Simple and predictable; ignores urgency |
| Earliest deadline | Closest deadline first | Prioritizes timeliness; may delay less urgent work |
| Highest risk | Highest risk score first | Prioritizes consequential tasks; may miss low-risk deadlines |

Ties use arrival and task ID, except highest risk first uses deadline before
arrival. Risk priority measures timely coverage, not review accuracy or safety.

## Fair comparisons

For each generated day, run every policy with 2, 3, 4, and 5 reviewers on the
exact same task list. Repeat with 100 different seeds for each workload.
This produces 2 × 100 × 4 × 3 = 2,400 simulations.

Compare policies at a fixed headcount to assess scheduling effects. Compare
headcounts under a fixed policy to assess staffing effects. The normal and
surge scenarios use the same seed sequence but have different generated task
lists; they are separate workload scenarios, not a task-by-task matched pair.

## Metrics and interpretation

| Metric | Calculation / interpretation |
|---|---|
| On-time rate | Tasks finished by deadline / all generated tasks; unstarted tasks count as failures |
| End-of-shift backlog | Tasks unfinished at minute 480, including tasks still in progress |
| Not started | Tasks that never begin during the shift |
| Average wait | Start minus arrival, averaged only over started tasks |
| Turnaround | Finish minus arrival, reported per started task |
| Lateness | Max(0, finish minus deadline), reported per started task |
| Utilization | Reviewer busy minutes within shift / available reviewer minutes |
| Overtime minutes | Total reviewer minutes worked after shift end |
| High-risk on-time rate | On-time fraction among risk-3 tasks |
| P10 on-time rate | 10th percentile of simulated daily on-time rates; describes weaker days, not a confidence interval |
| Share of days meeting target | Fraction of simulated days achieving at least 95% on-time |

Average wait excludes unstarted tasks, so read it alongside backlog and
not-started counts. High utilization can coexist with missed deadlines.
The scheduler does not deliberately idle to preserve capacity for future tasks.

## Outputs

- `sample_tasks.csv`: one reproducible normal day.
- `sample_schedule.csv`: assignment, wait, finish, and deadline status for
  that day using three reviewers and earliest deadline.
- `all_runs.csv`: all 2,400 simulation summaries.
- `comparison_summary.csv`: average and variability metrics for each option.
- `staffing_comparison.png`: on-time rate versus headcount.
- `sample_schedule.png`: reviewer timelines colored by risk.
- `findings.txt`: lowest tested headcount meeting the planning criterion.

The recommendation first minimizes headcount, then breaks ties by higher mean
on-time rate and lower average wait. It searches only the tested options. It
does not solve a global mathematical optimization or estimate labor costs.

## Make it your own

Start by reading `generate_tasks()`, then `simulate()`, then `experiment()`.
Change one assumption at a time and rerun:

1. Change task counts in `experiment()` to test larger demand shocks.
2. Change duration medians to test more complex reviews.
3. Change deadline windows to test stricter service commitments.
4. Extend the staffing range and compare whether extra capacity is worth it.

For a stronger second version, add reviewer breaks and skill restrictions,
then test how recommendations change. A later version could accept a public
or authorized anonymized task dataset, with validation and explicit assumptions.
Do not present synthetic results as measured improvements at Handshake.

## Resume wording after you understand and adapt the project

- Developed a Python discrete-event simulation of AI review operations,
  comparing three scheduling policies across four staffing levels and 2,400
  simulated daily workloads.
- Analyzed deadline compliance, backlog, utilization, and high-risk task
  coverage to identify the lowest tested staffing level meeting a defined
  service target under normal and surge demand.

The 2,400 count assumes the default run. These describe a simulation project,
not deployed operational changes. Be ready to explain the queue logic, input
assumptions, and the difference between average performance and reliable
performance across days.
