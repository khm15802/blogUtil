from active_log.db import Database


def test_view_snapshots_keep_latest_count_and_delta(tmp_path):
    db = Database(tmp_path / "stats.db")

    assert db.save_view_snapshots([
        {"id": 12, "title": "첫 글", "url": "https://example.com/12", "views": 4},
        {"id": 13, "title": "둘째 글", "url": "https://example.com/13", "views": 9},
    ]) == 2
    assert db.save_view_snapshots([
        {"id": 12, "title": "첫 글", "url": "https://example.com/12", "views": 11},
    ]) == 1

    rows = db.latest_view_stats()
    by_id = {row["id"]: row for row in rows}
    assert by_id[12]["views"] == 11
    assert by_id[12]["delta"] == 7
    assert by_id[13]["views"] == 9
    assert by_id[13]["delta"] == 9
