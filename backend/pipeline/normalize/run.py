"""Step 02 driver: raw actor files -> data/normalized.jsonl, using one mapper per marketplace.
A mapper is `mapper(raw: dict, category: str, scraped_at: datetime) -> Normalized` and raises Drop(reason)
for a record it cannot use. `category` is the query's category, the fallback when the record has no label."""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

import jsonl
from listing import Normalized
from normalize.common import Drop, clean_text


def normalize_all(data_dir, mappers) -> Counter:
    data_dir = Path(data_dir)
    runs_path = data_dir / "runs.jsonl"
    runs = jsonl.load(runs_path)
    stats, best = Counter(), {}
    for run in runs:
        raw_path = data_dir / "raw" / run["marketplace"] / f"{run['run_id']}.jsonl"
        if run["status"] != "SUCCEEDED" or not raw_path.exists():
            continue
        mp, scraped_at = run["marketplace"], datetime.fromisoformat(run["at"])
        for line in jsonl.read(raw_path):
            try:
                n: Normalized = mappers[mp](json.loads(line), run["category"], scraped_at)
                title = clean_text(n.title, one_line=True)
                if not title:
                    raise Drop("no_title")
                n = n.model_copy(update={"title": title, "description": clean_text(n.description)})
            except Drop as why:
                stats[f"drop:{mp}:{why}"] += 1
            except ValidationError:
                stats[f"drop:{mp}:invalid"] += 1
            except Exception as e:
                stats[f"drop:{mp}:error:{type(e).__name__}"] += 1
            else:
                if n.id in best:
                    stats["duplicates"] += 1
                if n.id not in best or n.scraped_at >= best[n.id].scraped_at:
                    best[n.id] = n
    out = data_dir / "normalized.jsonl"
    out.with_suffix(".tmp").write_text("".join(jsonl.dumps(best[i].model_dump(mode="json")) + "\n" for i in sorted(best)))
    out.with_suffix(".tmp").replace(out)
    stats["kept"] = len(best)
    return stats
