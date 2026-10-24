# Flaky tests in `run/tests` (to look at later)

## What happened

`pipeline/run/tests/test_batch.py` failed about 1 run in 40. The failing tests were
`test_batches_all_keeps_going_until_nothing_is_left` (3 batches instead of 2) and
`test_one_batch_scrapes_every_lane_checks_it_shares_it_and_rebuilds_the_catalog` (the eBay lane ran no query).

## Cause (found)

A real race in the runner, not just in the tests. Each lane (thread) called `scrape.run_plan`, and `run_plan`
read `runs.jsonl` when it started. If another lane had already written its first entry by then, that lane's
spend counted toward this lane's money limit (`max_spend`), so this lane stopped early and scraped less than
planned. In a real run, the effect would have been a smaller batch, not lost money.

## Fix (done)

`run_plan(..., past=...)`: `run_lanes` reads `runs.jsonl` once and gives every lane the same snapshot. A test in
`tests/test_scrape.py` covers it (`test_lanes_can_share_one_snapshot_of_past_runs_instead_of_reading_the_file`).
After the fix, 60 of 60 and then 150 of 150 repeated runs passed.

## What is still timing-based (could flake on a slow or loaded machine)

- `test_ctrl_c_lets_the_lanes_finish_their_current_run_then_stops` sends a fake Ctrl-C with
  `_thread.interrupt_main()` and relies on a 0.3 s sleep inside the fake run, so the main thread handles it first.
- `test_lanes_run_side_by_side_and_every_entry_lands_whole` relies on a 0.05 s sleep so the two lanes overlap.

If either one flakes, make it wait on a `threading.Event` instead of sleeping.

## How to check

```bash
cd backend
for i in $(seq 1 100); do uv run pytest -q pipeline/run/tests | tail -1; done | sed 's/ in .*//' | sort | uniq -c
```
