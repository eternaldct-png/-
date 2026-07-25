"""
実ブラウザでの診断フロー

診断ページのJSはテストクライアントでは検証できないため、実際に
Chromium で12問クリックして結果画面まで到達するかを確認する。

Playwright が入っていない環境では自動的にスキップされる。
CI では専用ジョブで実行する（他のテストより遅く、ブラウザが必要なため）。
"""
import os
import threading

import pytest

pytest.importorskip("playwright", reason="playwright 未インストールのためスキップ")

from playwright.sync_api import sync_playwright  # noqa: E402

PORT = 5099
BASE = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def live_server():
    """テスト用に実サーバーを立てる（テストクライアントではJSが動かないため）"""
    from werkzeug.serving import make_server

    import web_app

    server = make_server("127.0.0.1", PORT, web_app.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield BASE
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def page(live_server):
    # 通常は playwright install で入れたブラウザが使われる。
    # 既にブラウザがある環境（バージョンが噛み合わない場合など）では
    # PLAYWRIGHT_CHROMIUM_PATH に実行ファイルを指定して差し替えられる。
    launch_options = {}
    if executable := os.environ.get("PLAYWRIGHT_CHROMIUM_PATH"):
        launch_options["executable_path"] = executable

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_options)
        # スマホからのアクセスが大半なので iPhone 相当で確認する
        page = browser.new_page(viewport={"width": 390, "height": 844})
        # favicon の404は他ページと同じ挙動なので握りつぶす
        page.route("**/favicon.ico", lambda route: route.fulfill(status=200, body=""))
        yield page
        browser.close()


@pytest.fixture
def js_errors(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    return errors


@pytest.mark.browser
def test_一覧から診断を開いて最後まで答えられる(page, js_errors):
    import diagnosis

    page.goto(f"{BASE}/diagnosis")
    titles = page.locator(".quiz-title").all_text_contents()
    assert len(titles) == len(diagnosis.load_config()["quizzes"])

    page.locator(".quiz-link").first.click()
    page.wait_for_selector(".choice")

    for i in range(12):
        assert page.locator("#qnum").text_content() == f"Q{i + 1} / 12"
        assert page.locator("#choices .choice").count() == 4
        assert page.locator("#qtext").text_content().strip()
        page.locator(".choice").nth(i % 4).click()
        page.wait_for_timeout(80)

    page.wait_for_selector("#resultView:not(.hidden)", timeout=5000)
    assert page.locator("#rName").text_content().strip()
    assert page.locator("#rSummary").text_content().strip()
    assert page.locator("#buyBtn").is_visible()
    assert not js_errors, f"JSエラー: {js_errors}"


@pytest.mark.browser
def test_有料レポートの価格が設定と一致する(page):
    import diagnosis

    assert page.locator(".price").text_content() == f"{diagnosis.report_price():,}円"


@pytest.mark.browser
def test_やり直しと前の質問へが動く(page, js_errors):
    page.locator("#retryBtn").click()
    page.wait_for_selector("#quizView:not(.hidden)")
    assert page.locator("#qnum").text_content() == "Q1 / 12"

    page.locator(".choice").first.click()
    assert page.locator("#qnum").text_content() == "Q2 / 12"
    page.locator("#backBtn").click()
    assert page.locator("#qnum").text_content() == "Q1 / 12"
    assert not js_errors, f"JSエラー: {js_errors}"
