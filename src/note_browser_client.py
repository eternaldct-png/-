"""
note.com ブラウザ自動化クライアント (Playwright)

公式APIがないため、実際のブラウザ操作で下書きを作成する。
ログインは1回の実行につき1回だけ行う（記事ごとにログインし直すと
note 側で「しばらくたってからもう一度お試しください」とブロックされるため）。
"""
from typing import Optional


class NoteBrowserSession:
    """1回のログインで複数の下書きを作成するブラウザセッション"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.last_error = ""
        self._pw = None
        self._browser = None
        self.page = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ja-JP",
            extra_http_headers={
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            },
        )
        # ボット検出回避
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """)
        self.page = context.new_page()
        return self

    def __exit__(self, *exc):
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    # ── ログイン ──────────────────────────────────────────────

    def login(self, email: str, password: str) -> bool:
        from playwright.sync_api import TimeoutError as PWTimeout

        page = self.page
        try:
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
                    page.click(sel)
                    page.wait_for_timeout(300)
                    page.keyboard.type(email, delay=80)  # 人間らしいキー入力
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
                self.last_error = "ログイン画面のメール欄が見つかりません"
                return False

            # パスワード入力
            pwd_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[autocomplete="current-password"]',
            ]
            for sel in pwd_selectors:
                try:
                    page.wait_for_selector(sel, timeout=3000)
                    page.click(sel)
                    page.wait_for_timeout(300)
                    page.keyboard.type(password, delay=80)
                    print(f"[note_browser] パスワード入力 ({sel})")
                    break
                except Exception:
                    continue

            page.wait_for_timeout(500)

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
            try:
                page.wait_for_url(lambda url: "login" not in url, timeout=15000)
            except PWTimeout:
                pass
            page.wait_for_timeout(2000)
            page.screenshot(path="/tmp/note_after_login.png")
            print(f"[note_browser] ログイン後URL: {page.url}")

            if "/login" not in page.url:
                return True

            # ログイン画面から進めなかった → エラーメッセージを拾って失敗扱い
            message = ""
            for err_sel in ['[class*="error"]', '[class*="Error"]', '.alert', '[role="alert"]']:
                try:
                    el = page.locator(err_sel).first
                    if el.is_visible():
                        message = el.inner_text()[:100].strip()
                        print(f"[note_browser] エラーメッセージ: {message}")
                        break
                except Exception:
                    pass
            self.last_error = "note へのログインに失敗" + (f"（{message}）" if message else "")
            return False

        except Exception as e:
            print(f"[note_browser] ログイン中のエラー: {e}")
            self.last_error = f"note へのログイン中にエラー: {e}"
            return False

    # ── 下書き作成 ────────────────────────────────────────────

    def create_draft(self, title: str, body: str, tags: Optional[list] = None) -> Optional[dict]:
        from playwright.sync_api import TimeoutError as PWTimeout

        page = self.page
        try:
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
                self.last_error = "note の新規記事画面でタイトル欄が見つかりません"
                return None

            # 本文エリアへ移動してテキスト入力
            page.keyboard.press("Tab")
            page.wait_for_timeout(500)
            page.keyboard.type(body, delay=1)
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
            return {"url": current_url, "title": title, "status": "draft"}

        except Exception as e:
            print(f"[note_browser] エラー: {e}")
            self.last_error = f"下書き作成中にエラー: {e}"
            try:
                page.screenshot(path="/tmp/note_error.png")
            except Exception:
                pass
            return None


def create_draft_via_browser(
    email: str,
    password: str,
    title: str,
    body: str,
    tags: Optional[list] = None,
    headless: bool = True,
) -> Optional[dict]:
    """1記事だけ作成する（ログイン → 下書き作成）。複数記事は NoteBrowserSession を使う。"""
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("[note_browser] playwright がインストールされていません: pip install playwright")
        return None

    with NoteBrowserSession(headless=headless) as s:
        if not s.login(email, password):
            return None
        return s.create_draft(title, body, tags)
