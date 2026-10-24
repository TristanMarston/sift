# Flaky tests in `run/tests` (fixed)

Two real races in the runner made `run/tests/test_batch.py` fail now and then. Both are fixed, and no test relies on a
sleep being long enough any more.

## 1. Lanes counted each other's spend

**Seen:** about 1 run in 40. `test_batches_all_keeps_going_until_nothing_is_left` (3 batches instead of 2) and
`test_one_batch_scrapes_every_lane_checks_it_shares_it_and_rebuilds_the_catalog` (the eBay lane ran no query).

**Cause:** each lane (thread) called `scrape.run_plan`, and `run_plan` read `runs.jsonl` when it started. If another
lane had already written its first entry by then, that lane's spend counted toward this lane's money limit
(`max_spend`), so this lane stopped early and scraped less than planned.

**Fix:** `run_plan(..., past=...)`: `run_lanes` reads `runs.jsonl` once and gives every lane the same snapshot.
`tests/test_scrape.py::test_lanes_can_share_one_snapshot_of_past_runs_instead_of_reading_the_file` covers it.

## 2. Ctrl-C could make the runner stop waiting for a lane

**Seen:** about 1 full `uv run pytest` in 3 on macOS. `test_ctrl_c_lets_the_lanes_finish_their_current_run_then_stops`
failed with exit code 130 but 0 actor calls, then a stray `KeyboardInterrupt` aborted the rest of the session.

**Cause:** a bug in Python 3.12 (our version). If Ctrl-C lands while the main thread is inside `Thread.join(timeout)` or
`Thread.is_alive()`, Python marks the thread as finished even though it is still running. `run_lanes` waited with
`join(0.2)`, so it stopped waiting for the lane, deleted the STOP file and ended the batch while the lane's run was still
on Apify. In a real run, that run was paid for but never recorded, and the lane went on to its next query until the
process exited. In the test, the leftover lane ran its next query after the test ended and sent a second Ctrl-C into
whatever test came next. Python 3.13 rewrote `join` and does not have this bug.

**Fix:** `run_lanes` no longer calls `join` or `is_alive`. Each lane adds itself to a `finished` set when it ends, and the
main thread checks that set every 0.2 s.

## Tests that used to depend on timing

- The Ctrl-C test now sends Ctrl-C while the main thread is waiting (the case that broke), and the fake run waits for
  the STOP file instead of sleeping 0.3 s.
- `test_lanes_run_side_by_side_and_every_entry_lands_whole` used a 0.05 s sleep to make the lanes overlap. Now each
  lane's first run waits at a `threading.Barrier(2)`. If the lanes ran one at a time, the barrier would time out and the
  run would fail.

## How to check

```bash
cd backend
for i in $(seq 1 100); do uv run pytest -q | tail -1; done | sed 's/ in .*//' | sort | uniq -c
```

Run the whole suite, not only `pipeline/run/tests`: a stray Ctrl-C from one test shows up as a failure in a later one.
