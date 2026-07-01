"""
ペルソナ自動更新モジュール
ベンチマーク分析と自投稿のエンゲージメントデータを元に
ペルソナYAMLを継続的に改善する（複数ペルソナ対応）
"""
import os
import re
import json
import yaml
import difflib
import anthropic
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from persona_utils import persona_slug

JST = ZoneInfo("Asia/Tokyo")
ANALYSIS_DIR = Path("analysis")
BACKUP_DIR = Path("persona/backups")


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_reports(slug: str) -> dict:
    """最新の分析レポートをすべて読み込む（ペルソナごとに名前空間を分ける）"""
    return {
        "benchmark": _load_text(ANALYSIS_DIR / f"{slug}_benchmark_latest.md"),
        "own_performance": _load_text(ANALYSIS_DIR / f"{slug}_latest_report.md"),
        "benchmark_patterns": _load_text(ANALYSIS_DIR / f"{slug}_benchmark_patterns_latest.json"),
    }


def load_current_persona(persona_path: Path) -> tuple[dict, str]:
    """現在のpersona YAMLを辞書とテキストの両方で返す"""
    if not persona_path.exists():
        raise FileNotFoundError(f"ペルソナファイルが見つかりません: {persona_path}")
    raw = persona_path.read_text(encoding="utf-8")
    return yaml.safe_load(raw), raw


def generate_persona_update(
    persona: dict,
    persona_raw: str,
    reports: dict,
    persona_path: Path,
) -> tuple[str, str]:
    """
    Claude に現在のペルソナと分析結果を渡し、
    更新後のYAMLと変更理由を生成してもらう

    Returns:
        (updated_yaml_str, reasoning_str)
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    persona_name = persona.get("name", "アカウント")

    benchmark_summary = reports["benchmark"][:3000] if reports["benchmark"] else "（ベンチマークデータなし）"
    own_summary = reports["own_performance"][:2000] if reports["own_performance"] else "（自己分析データなし）"

    # パターンJSONからキーデータだけ抽出
    patterns_summary = ""
    if reports["benchmark_patterns"]:
        try:
            bp = json.loads(reports["benchmark_patterns"])
            p = bp.get("patterns", {})
            patterns_summary = f"""
抽出パターン（定量データ）:
- 疑問文含有率: {p.get('question_ratio', '?')}%
- 絵文字使用率: {p.get('emoji_ratio', '?')}%
- 改行使用率: {p.get('line_break_ratio', '?')}%
- CTA（返信誘導）含有率: {p.get('cta_ratio', '?')}%
- 平均文字数: {p.get('avg_length', '?')}文字
- 最適時間帯（上位）: {list(p.get('best_hours', {}).keys())[:3]}
"""
        except (json.JSONDecodeError, AttributeError):
            pass

    prompt = f"""あなたはXのSNS戦略の専門家です。
「{persona_name}」のX投稿ペルソナを、分析データに基づいて改善してください。

== 現在のペルソナ設定（YAML）==
```yaml
{persona_raw[:4000]}
```

== ベンチマーク分析レポート（競合・高エンゲージメントアカウント）==
{benchmark_summary}
{patterns_summary}

== 自分の投稿パフォーマンス分析 ==
{own_summary}

## 指示
上記のデータを踏まえ、{persona_name}のペルソナYAMLを改善してください。

### 変更対象（必要なものだけ変更する）
1. `post_styles` の各スタイルのexamples（高エンゲージメントパターンを反映した具体例に更新）
2. `posting_schedule.preferred_hours`（データが示す最適時間帯に調整）
3. `personality`（効果的だとわかった投稿スタイルの特徴を追加）
4. `hashtags.topic_specific`（有効なタグがあれば追加）
5. `day_specific` の各曜日の `mood`（パターンに合わせて具体化）

### 変更しないこと
- `name`, `screen_name`, `bio`, `background` は変更しない
- `avoid` リストは変更しない
- 大きな方向性の転換はしない（微調整に留める）

### 出力形式
以下のJSON形式で返してください（コードブロック不要）:
{{
  "reasoning": "変更した理由の要約（日本語200文字以内）",
  "changes": [
    {{
      "section": "変更するYAMLのキーパス（例: post_styles.company_love.examples）",
      "description": "何をどう変えたか（1行）",
      "new_value": "新しい値（YAMLの値として有効な形式）"
    }}
  ],
  "updated_yaml": "完全な更新後のYAML文字列（```なし、YAMLそのまま）"
}}
"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    # JSONパース
    try:
        # コードブロック除去
        cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()
        # 最初の { から最後の } を抽出
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            data = json.loads(cleaned)

        updated_yaml = data.get("updated_yaml", "")
        reasoning = data.get("reasoning", "（理由なし）")
        changes = data.get("changes", [])

        # changesのログ表示
        print(f"\n[updater] 変更理由: {reasoning}")
        print(f"[updater] 変更箇所 ({len(changes)}件):")
        for c in changes:
            print(f"  - {c.get('section', '?')}: {c.get('description', '')}")

        return updated_yaml, reasoning

    except (json.JSONDecodeError, AttributeError) as e:
        print(f"[updater] JSONパースエラー: {e}")
        # フォールバック: テキストからYAML部分を抽出
        yaml_match = re.search(r'updated_yaml["\s:]+(.+?)(?:reasoning|changes|\Z)', raw, re.DOTALL)
        if yaml_match:
            return yaml_match.group(1).strip().strip('"'), "（理由の抽出に失敗）"
        return "", "（更新YAMLの生成に失敗）"


def show_diff(old_yaml: str, new_yaml: str, persona_path: Path) -> None:
    """変更差分を見やすく表示する"""
    old_lines = old_yaml.splitlines(keepends=True)
    new_lines = new_yaml.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"{persona_path} (現在)",
        tofile=f"{persona_path} (更新後)",
        n=3,
    ))
    if not diff:
        print("[updater] 変更箇所はありませんでした")
        return
    print(f"\n{'='*60}")
    print("差分プレビュー:")
    print(f"{'='*60}")
    for line in diff[:100]:  # 長すぎる場合は最初の100行のみ
        print(line, end="")
    if len(diff) > 100:
        print(f"\n... 残り {len(diff) - 100} 行は省略")
    print(f"\n{'='*60}\n")


def backup_persona(persona_path: Path) -> Path:
    """現在のペルソナをバックアップする"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(JST)
    backup_path = BACKUP_DIR / f"{persona_path.stem}_{now.strftime('%Y%m%d_%H%M%S')}.yaml"
    backup_path.write_text(persona_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[updater] バックアップ保存: {backup_path}")
    return backup_path


def validate_yaml(yaml_str: str) -> bool:
    """生成されたYAMLが有効かチェックする"""
    try:
        parsed = yaml.safe_load(yaml_str)
        required_keys = ["name", "screen_name", "personality", "post_styles"]
        return all(k in parsed for k in required_keys)
    except yaml.YAMLError as e:
        print(f"[updater] YAML検証エラー: {e}")
        return False


def apply_update(new_yaml: str, reasoning: str, persona_path: Path, slug: str) -> bool:
    """バックアップ後にペルソナYAMLを更新する"""
    backup_persona(persona_path)
    persona_path.write_text(new_yaml, encoding="utf-8")

    # 更新ログを保存（ペルソナごとに名前空間を分ける）
    ANALYSIS_DIR.mkdir(exist_ok=True)
    log_path = ANALYSIS_DIR / f"{slug}_persona_update_log.jsonl"
    log_entry = {
        "updated_at": datetime.now(JST).isoformat(),
        "reasoning": reasoning,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(f"[updater] ペルソナを更新しました: {persona_path}")
    return True


def run_update(auto: bool = False, persona_path: str = "persona/config.yaml") -> bool:
    """
    ペルソナ更新のメインエントリーポイント

    Args:
        auto: True の場合、確認なしで自動適用（GitHub Actions用）
        persona_path: 更新対象のペルソナ設定ファイルパス

    Returns:
        更新を適用した場合 True
    """
    path = Path(persona_path)
    slug = persona_slug(persona_path)

    print(f"[updater] [{slug}] 分析レポートを読み込み中...")
    reports = load_reports(slug)

    has_data = any(v for v in reports.values())
    if not has_data:
        print("[updater] 分析レポートが見つかりません。先にbenchmark_analyzerとanalyzeを実行してください。")
        return False

    print("[updater] 現在のペルソナを読み込み中...")
    persona, persona_raw = load_current_persona(path)

    print("[updater] Claude AIでペルソナ更新案を生成中...")
    new_yaml, reasoning = generate_persona_update(persona, persona_raw, reports, path)

    if not new_yaml:
        print("[updater] ペルソナ更新YAMLの生成に失敗しました")
        return False

    if not validate_yaml(new_yaml):
        print("[updater] 生成されたYAMLが無効です。更新をスキップします")
        return False

    show_diff(persona_raw, new_yaml, path)

    if auto:
        print("[updater] --auto モード: 確認なしで更新を適用します")
        return apply_update(new_yaml, reasoning, path, slug)

    # インタラクティブモード
    print(f"変更理由: {reasoning}")
    ans = input("この変更を適用しますか？ [y/N]: ").strip().lower()
    if ans == "y":
        return apply_update(new_yaml, reasoning, path, slug)
    else:
        print("[updater] 更新をキャンセルしました")
        return False
