# Scraping in batches: what the team needs to know

This folder runs the scraper (`../01_scrape.py`'s engine) in **batches**. After every batch it checks the data, and if
the checks pass it can keep going overnight. It also shares what was scraped, so nobody pays for the same query twice.

## The rules

1. **One runner at a time.** Only one computer scrapes at once. The Apify account allows 5 runs at once, and one runner
   uses all 5 (one per marketplace).
2. **Don't use the Apify token for anything else while a batch runs.** If you do, the runner's calls fail.
3. **Keep the runner's computer awake and online.** The work happens on Apify, but the laptop waits for each run.
   macOS: put `caffeinate -i` in front of the command. Windows: set sleep to "never" while it runs.

## Setup (once)

```bash
cd backend
uv sync
# the repo root .env holds the team's token:  APIFY_TOKEN=...
```

All commands below run from `backend/`.

## The commands

| I want to... | Command |
| --- | --- |
| See what the next batch would scrape and cost (free) | `uv run python pipeline/run/cli.py batch --rows 5000 --dry-run` |
| Run **one** batch, then stop so I can look | `uv run python pipeline/run/cli.py batch --rows 5000` |
| Run batches until $50, the money or the queries run out (overnight) | `uv run python pipeline/run/cli.py batch --rows 5000 --batches all --max-spend 50 > batch.log 2>&1 &` |
| Get everything the team has scraped | `uv run python pipeline/run/cli.py sync` |
| Save everything in one file | `uv run python pipeline/run/cli.py export sift-data.zip` |
| Load a file a teammate sent | `uv run python pipeline/run/cli.py import sift-data.zip` |

- **How much:** `--rows` × `--batches` raw rows. About 93% become listings. `--max-spend 50` caps what this command may
  spend; `--batches all` requires it.
- **Split:** a batch is split across the marketplaces in the ratio of the `quotas` in `../queries.yaml`. That is all
  they do here: they never stop a batch, however much the team has already scraped. A marketplace with no queries
  left hands its share to the others, and a quota of 0 keeps one out. Grailed's share is small on purpose ($0.012 a row).
- **What:** `--only depop,ebay` and `--categories tshirts,sneakers` narrow it down.
- A 5,000-row batch costs about $15 and takes about 15 minutes. The runner never plans past the account's balance, minus $2.

After `batch`, `sync` or `import`, the catalog is up to date in `pipeline/data/listings.jsonl`.

## What happens in a batch

1. It pulls the team's runs from Apify (`sync`), so it knows what's already done.
2. It refuses to start if the account already has active runs (someone else is scraping). `--force` overrides this.
3. It runs all 5 marketplaces side by side. Each run is judged as before (see `../BLOCKING.md`): a block or junk data
   stops that marketplace at once.
4. It uploads its runs to the team log on Apify (a dataset called `sift-runs`).
5. It **checks the batch**, and writes `pipeline/data/batches/<batch id>/CHECKS.md`.

## The checks

| Check | Fails (that marketplace stops) | Warns |
| --- | --- | --- |
| run health | the marketplace was blocked or returned junk | |
| unusable rows (no price, photo, url, title) | over 5% | |
| filtered rows (kids, wrong category, auction) | | over 30% |
| descriptions over 40 characters | under 70% | under 85% |
| valid listings (schema) | any invalid | |
| new listings (rows we paid for that we did not already have) | under 20% | under 50% |
| real cost (Apify's bill vs our estimate) | over 1.25x + $0.10 | |
| stated material | | under half of the review scrape's share |
| categories | | a queried category came back empty |
| privacy (seller usernames, ids...) | **stops everything** | |

A failed marketplace sits out the rest of that command, and the others carry on. Look for `ALERT` lines in the log.
To retry it, fix the cause (or wait) and run the command again.

## Stopping

- Create the file `pipeline/data/STOP`: no new batch starts, and running lanes stop before their next run.
  Delete it to continue.
- Ctrl-C once: every marketplace finishes its current run, then stops. Ctrl-C twice: quits at once (those runs are lost).
- Exit codes: 0 done, 2 a marketplace was stopped, 3 out of money (or `--max-spend`), 4 STOP file, 5 the token was busy, 130 Ctrl-C.

## Handing off

- **To another computer, same token:** run `sync` on the new computer, then `batch`. Apify keeps run data for 7 days.
- **To a new token** (when the account's money is used up): on the old computer `export sift-data.zip` and send it.
  On the new computer `import sift-data.zip`, put the new token in `.env`, then `batch`. The new account's team log starts
  empty, so teammates need the zip too.
- Rerunning is always safe: finished queries are skipped, bad runs are retried, and importing twice changes nothing.

## Files

| Path (in `pipeline/data/`) | What it is |
| --- | --- |
| `runs.jsonl` | every run anyone has done that this computer knows about: what "already scraped" means |
| `raw/<marketplace>/<run id>.jsonl` | the rows of each run (seller identity removed) |
| `batches/<batch id>/` | `CHECKS.md`, `batch.json` and `run_report.md` for each batch |
| `normalized.jsonl`, `listings.jsonl` | the catalog, rebuilt from the above (steps 02–03) |

Code: `batch.py` (planning, lanes, the loop), `checks.py` (the checks), `ledger.py` (sync, export, import), `cli.py`.
Tests: `uv run pytest` (no network, no money). Known test issue: `FLAKY_TESTS.md`.
