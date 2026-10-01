"""Deterministic checks of scheduling, capacity and reported metrics."""
import unittest
import pandas as pd
from optimizer import simulate, generate_tasks, POLICIES


def tasks(rows):
    return pd.DataFrame(rows, columns=["task_id", "arrival", "duration", "deadline", "risk"])


class SchedulingTests(unittest.TestCase):
    def test_policy_choice_and_nonpreemption(self):
        data = tasks([(1, 0, 20, 50, 1), (2, 1, 5, 60, 3), (3, 2, 5, 25, 1)])
        for policy, expected in [("FIFO", 2), ("Earliest deadline", 3), ("Highest risk", 2)]:
            schedule, _ = simulate(data, 1, policy)
            self.assertEqual(schedule.loc[schedule.start == 20, "task_id"].iloc[0], expected)
            self.assertEqual(schedule.loc[schedule.task_id == 1, "finish"].iloc[0], 20)

    def test_capacity_and_backlog(self):
        schedule, m = simulate(tasks([(1, 0, 12, 10, 3), (2, 0, 5, 10, 1)]), 1, "FIFO", shift=10)
        self.assertEqual(m["backlog"], 2)
        self.assertEqual(m["not_started"], 1)
        self.assertEqual(m["on_time_rate"], 0)
        self.assertEqual(m["utilization"], 1)
        self.assertEqual(m["overtime_minutes"], 2)

    def test_idle_gap_and_multiple_reviewers(self):
        schedule, m = simulate(tasks([(1, 10, 5, 15, 1), (2, 10, 5, 15, 3)]), 2, "FIFO", shift=20)
        self.assertEqual(schedule.start.tolist(), [10, 10])
        self.assertEqual(m["on_time_rate"], 1)
        self.assertEqual(m["utilization"], 0.25)

    def test_invariants_and_reproducibility(self):
        pd.testing.assert_frame_equal(generate_tasks(42), generate_tasks(42))
        for policy in POLICIES:
            schedule, m = simulate(generate_tasks(42), 3, policy)
            started = schedule.dropna(subset=["start"])
            self.assertTrue((started.start >= started.arrival).all())
            self.assertTrue((started.start < 480).all())
            self.assertTrue((started.finish == started.start + started.duration).all())
            for _, group in started.groupby("reviewer"):
                group = group.sort_values("start")
                self.assertTrue((group.start.to_numpy()[1:] >= group.finish.to_numpy()[:-1]).all())
            self.assertTrue(0 <= m["utilization"] <= 1)


if __name__ == "__main__":
    unittest.main()
