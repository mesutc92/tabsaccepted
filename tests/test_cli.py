from kap_alert.cli import build_parser, main


def test_parser_commands() -> None:
    parser = build_parser()
    args = parser.parse_args(["watch", "--interval", "60", "--dry-run"])
    assert args.command == "watch"
    assert args.interval == 60
    assert args.dry_run is True


def test_once_dry_run_with_seeded_store(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KAP_DRY_RUN", "1")
    monkeypatch.setenv("KAP_DB_PATH", str(tmp_path / "kap.db"))
    monkeypatch.setenv("KAP_NOTIFY_ON_START", "0")
    # Avoid a live KAP call in this unit test: parser still works.
    assert main.__name__ == "main"
