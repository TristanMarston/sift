# What happens when a marketplace blocks us

Short version: every actor run is judged the moment it finishes. A bad one prints an `ALERT` line at once. A block or
junk data stops that marketplace immediately. Nothing bad reaches the catalog. The run ends with a report of good and
bad rows and what the bad runs cost. Code: `health.py` (the judge), `scrape.py` (the response), `scrape_report.py` (the report).

## Why "the run failed" is not enough

We found out the hard way. Our one blocked run (a Mercari actor that was served a challenge page) ended `SUCCEEDED`,
reported `Total 1 requests: 1 succeeded, 0 failed`, delivered 0 listings, and still billed $0.04. Apify's own community
tooling and forum reports describe the same thing: a run can finish successfully without having collected data
([Apify dataset gate](https://apify.com/vittuhy/dataset-result-gate), [silent-failure checks](https://apify.com/ryanclinton/actor-test-runner/examples/catch-silent-scraper-failures)).
Crawlee's own guide says status codes (401/403/429) miss a block page served with a 200 and tells you to inspect the result
([session management](https://crawlee.dev/docs/guides/session-management)).

Searching the logs for block words is not safe either. In our real logs, **healthy** runs contain these:

| Healthy run | What its log says | What it means |
| --- | --- | --- |
| Mercari | `refused this run's address (HTTP 403 (Cloudflare)) ... (1 of 6)` | It switched address and delivered all 20 listings |
| Poshmark | `Both 'blockedStatusCodes' and 'retryOnBlocked' are set` | A config note |
| Grailed | `Could not read live Algolia config ... site layout may have changed` | An early warning, not a failure |
| Depop | nothing diagnostic at all | The log gives no signal either way |

So the judge looks at **what came back first** and uses the log only as supporting evidence.

## What is checked after every run

| Check | Verdict | Stops the marketplace? |
| --- | --- | --- |
| Run ended FAILED, TIMED-OUT, ABORTED, or the call errored | `failed` | after a second one in a row |
| Zero rows | `empty` | after a second one in a row |
| Zero rows and the log shows a refusal (403, 429, Cloudflare, captcha, ...) | `blocked` | **at once** |
| The actor ran out of fresh addresses (`6 of 6`), reports giving up, or most of its requests failed | `blocked` | **at once** |
| eBay's auth-token pool is empty | `blocked` | **at once** |
| Over 30% of the rows are unusable (no price, photo, url or title) | `degraded` | **at once** |
| Fewer than 30% of the rows have a real description (the actor returned card data only, as the first Mercari actor did) | `degraded` | **at once** |
| Fewer than 10% of the rows are usable because the rest were filtered out (wrong country or currency, for example) | `degraded` | **at once** |
| Far fewer rows than asked for (under 20%) | `short` | no, but it is counted and flagged in the report |

Rows are judged with the same mapper that step 02 uses, so "unusable" means exactly "step 02 would reject it".
Kids' items, wrong categories and non-USD prices are *filtered* on purpose and never count as bad. Row-quality checks
need at least 10 rows, so a narrow query that returns 4 listings is not accused of anything.

## What happens when a run is bad

1. **An `ALERT` line is printed straight away** (flushed, so it shows in a log file), with the verdict, the reasons and a
   link to the Apify run, and a record is appended to `data/alerts.jsonl`.
2. **The marketplace is stopped** (immediately for `blocked` and `degraded`, on the second strike for `empty` and `failed`).
   The other marketplaces keep running. With `--stop-all-on-block` everything halts instead.
3. **The rows of that run are quarantined**: they stay on disk, but step 02 never reads them and they do not count toward
   the quota.
4. **Nothing is lost.** Rerun the same command after the cause is fixed or has passed: finished queries are skipped, bad
   ones are retried. A query that comes back empty twice is treated as really empty and not retried again.
5. **The run ends with a report** and an exit code: 0 finished, 2 a marketplace was stopped, 3 the `--max-spend` limit,
   4 a `STOP` file, 130 Ctrl-C. Ctrl-C still prints the report.

To halt a running scrape politely, create the file `data/STOP`; it is checked before every actor call.

A real example (an empty Depop query, run against the live API):

```
ALERT [depop] EMPTY on 'zzqxwvk plmnbvc' (run https://console.apify.com/actors/runs/Sk5U...): no rows returned. Strike 1 of 2: one more bad run in a row stops this marketplace.
ALERT [depop] EMPTY on 'qqqzzzxxx wwwvvvuuu' (run https://console.apify.com/actors/runs/EDSv...): no rows returned. Marketplace STOPPED, the others continue. Re-run the same command to resume once it is fixed.
```

## The report at the end

Printed, and saved as `data/run_report.md` and `data/run_report.json`. Per marketplace: queries ok / short / bad / skipped
because done earlier; rows saved, and how many were **good** (usable and new), **duplicate**, **filtered** (left out on
purpose, with the reasons), **unusable** (with the reasons) and **quarantined** (saved by a bad run); progress toward the
quota; estimated spend and how much of it was **wasted** on bad runs. Below that: every alert, a "watch" line for any
marketplace whose queries mostly come back short (what a site that cuts us off after a few pages looks like), and a
"what to do next" line with the Apify run link for each stopped marketplace.

## How the big run will be operated

Started in the background with its output in a log file. An `ALERT` line is the trigger: it is watched for as it appears,
so a block is reported within seconds, not at the end. When a marketplace is stopped: read the alert and the Apify run log,
decide between waiting and rerunning, switching actor, or dropping that source, and rerun only after that decision.

## Fallbacks, and what is not built

- **Built:** fail fast (the stop above), quarantine, retry-on-rerun, and a hard charge cap and timeout on every call, so a
  bad run costs little. Empty runs cost almost nothing ($0.00 to $0.04 in our tests). A run that returns billed junk costs
  at most its own charge cap (about $0.25 for Depop up to $3.00 for Grailed), and then the marketplace is stopped.
- **Alternative actors are a manual switch.** Candidates: Depop `123webdata/depop-scraper`, Poshmark
  `xtracto/poshmark-detail-scraper`, Grailed `lulzasaur/grailed-scraper`, Mercari `tortuga/mercari-scraper`, eBay the
  official Browse API. Only Mercari's was probed with real output (3 identical listings to the main actor). They use
  different field names, so each needs its own mapper. Switching automatically in the middle of a run is not built:
  it would be untested code for a failure we have not seen.
- **Proxies:** Depop and eBay already default to residential proxies; Poshmark and Mercari expose no proxy setting. Grailed
  defaults to Apify's standard proxy and could be moved to residential, which is the only real escalation available. It is
  not automated, because we have not seen a Grailed block to test it on.

## What this cannot catch

- A block that returns believable data (fake or stale listings). Nothing here can tell.
- A block that only trims results slightly (a few percent fewer rows).
- A site changing its markup so that rows are present but a field such as the description is quietly empty on only
  some of them: caught only if the share crosses the thresholds above.
- A very slow trickle that never trips `short`. The "watch" line and the quota progress in the report are the backstops.

The thresholds are constants at the top of `health.py` (30% unusable, 30% described, 10% usable, 20% short) and were set
against the real runs we have: unusable rows were 0% in every healthy run, and descriptions were present in 75% to 100%
of rows. Check them against `run_report.md` after the first real hour and tell me if a marketplace is stopped too eagerly.
