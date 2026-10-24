"""The command line: rules on the arguments, checked before anything reaches Apify."""
import sys

import pytest

from run import cli


def test_batches_all_needs_max_spend(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "token", lambda required=True: "fake")           # never the real .env token
    monkeypatch.setattr(cli.B, "run_batches", lambda *a, **k: calls.append(k) or 0)
    monkeypatch.setattr(sys, "argv", ["cli.py", "batch", "--batches", "all"])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 2 and calls == [] and "--max-spend" in capsys.readouterr().err
    monkeypatch.setattr(sys, "argv", ["cli.py", "batch", "--batches", "all", "--max-spend", "50"])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 0 and calls[0]["batches"] is None and calls[0]["max_spend"] == 50
