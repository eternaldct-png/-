"""
note.com ブラウザ自動化クライアント (Playwright)

公式APIがないため、実際のブラウザ操作で下書きを作成する。
"""
import sys
from pathlib import Path
from typing import Optional


def create_draft_via_browser(
    email: str,
    password: str,
    title: str,
    body: str,
    tags: Optional[list] = None,
    headless: bool = True,
) -> Optional[dict]:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("[note_browser] playwright がインストールされていません: pip install playwright")
        return None

    tags = tags or []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ja-JP",
        )
        page = context.new_page()

        try:
            # ── ログイン ──────────────────────────────────────────
            print("[note_browser] ログインページへ移動...")
            page.goto("https://note.com/login", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)  # SPA レンダリング待ち

            # スクリーンショットでデバッグ
            page.screenshot(path="/tmp/note_login_page.png")
            print(f"[note_browser] ログインページURL: {page.url}")
            print(f"[note_browser] フォーム要素: {page.locator('input').count()} 個")

            # メールアドレス入力（複数セレクタ試行）
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[autocomplete="email"]',
                'input[placeholder*="メール"]',
                'input[placeholder*="mail"]',
                'input[type="text"]:first-of-type',
                'form input:nth-child(1)',
            ]
            email_filled = False
            for sel in email_selectors:
                try:
                    page.wait_for_selector(sel, timeout=3000)
                    page.fill(sel, email)
                    print(f"[note_browser] メール入力 ({sel})")
                    email_filled = True
                    break
                except Exception:
                    continue

            if not email_filled:
                # 全 input の情報を出力してデバッグ
                inputs = page.locator("input").all()
                for i, inp in enumerate(inputs):
                    print(f"[note_browser] input[{i}]: type={inp.get_attribute('type')} name={inp.get_attribute('name')} placeholder={inp.get_attribute('placeholder')}")
                page.screenshot(path="/tmp/note_login_debug.png")
                browser.close()
                return None

            # パスワード入力
            pwd_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[autocomplete="current-password"]',
            ]
            for sel in pwd_selectors:
                try:
                    page.wait_for_selector(sel, timeout=3000)
                    page.fill(sel, password)
                    print(f"[note_browser] パスワード入力 ({sel})")
                    break
                except Exception:
                    continue

            # ログインボタン押下
            btn_selectors = [
                'button[type="submit"]',
                'button:has-text("ログイン")',
                'input[type="submit"]',
                'button:has-text("サインイン")',
            ]
            for sel in btn_selectors:
                try:
                    page.click(sel, timeout=5000)
                    print(f"[note_browser] ログインボタン押下 ({sel})")
                    break
                except Exception:
                    continue

            print("[note_browser] ログイン後リダイレクト待機...")
            page.wait_for_timeout(5000)
            page.screenshot(path="/tmp/note_after_login.png")
            print(f"[note_browser] ログイン後URL: {page.url}")

            # ── 新規記事ページへ ──────────────────────────────────
            print("[note_browser] 新規記事ページへ移動...")
            page.goto("https://note.com/notes/new", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            # タイトル入力
            title_sel = 'textarea[placeholder], input[placeholder*="タイトル"], .editor-title textarea, [data-placeholder*="タイトル"]'
            try:
                page.wait_for_selector(title_sel, timeout=10000)
                page.click(title_sel)
                page.fill(title_sel, title)
                print(f"[note_browser] タイトル入力: {title[:30]}")
            except PWTimeout:
                print("[note_browser] タイトル欄が見つかりません。スクリーンショット保存")
                page.screenshot(path="/tmp/note_new_error.png")
                browser.close()
                return None

            # 本文エリアへ移動してテキスト入力
            page.keyboard.press("Tab")
            page.wait_for_timeout(500)
            page.keyboard.type(body[:3000], delay=1)  # 長すぎる場合は先頭3000字
            print("[note_browser] 本文入力完了")

            # ── 下書き保存 ────────────────────────────────────────
            # 「投稿設定」または「下書き保存」ボタンを探す
            draft_btn_selectors = [
                'button:has-text("下書き保存")',
                'button:has-text("下書きに保存")',
                '[data-type="draft"]',
            ]
            saved = False
            for sel in draft_btn_selectors:
                try:
                    page.click(sel, timeout=5000)
                    page.wait_for_timeout(2000)
                    print(f"[note_browser] 下書き保存完了（{sel}）")
                    saved = True
                    break
                except PWTimeout:
                    continue

            if not saved:
                # Ctrl+S でも試みる
                page.keyboard.press("Control+s")
                page.wait_for_timeout(2000)
                print("[note_browser] Ctrl+S で保存を試みました")

            current_url = page.url
            print(f"[note_browser] 現在のURL: {current_url}")

            browser.close()
            return {"url": current_url, "title": title, "status": "draft"}

        except Exception as e:
            print(f"[note_browser] エラー: {e}")
            try:
                page.screenshot(path="/tmp/note_error.png")
            except Exception:
                pass
            browser.close()
            return None
