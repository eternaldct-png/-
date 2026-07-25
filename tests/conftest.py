"""
テスト共通のセットアップ

アプリのコードは「リポジトリのルートから実行される」前提で相対パス
（persona/... や posts/...）を使っているため、テストでもルートに移動する。
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture
def client():
    """Flask のテストクライアント"""
    import web_app

    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


@pytest.fixture
def report_cache(tmp_path, monkeypatch):
    """レポートのキャッシュ先を一時ディレクトリに逃がす"""
    import diagnosis

    path = tmp_path / "diagnosis_reports"
    monkeypatch.setattr(diagnosis, "REPORT_CACHE_DIR", path)
    return path


@pytest.fixture
def promo_state(tmp_path, monkeypatch):
    """告知カウンターの保存先を一時ファイルに逃がす（実データを汚さない）"""
    import promo

    path = tmp_path / "promo_state.json"
    monkeypatch.setattr(promo, "STATE_PATH", path)
    return path
