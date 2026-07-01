"""
複数ペルソナ運用のための共通ユーティリティ
分析レポート・バックアップファイルの命名に使うスラッグを生成する
"""
from pathlib import Path


def persona_slug(persona_path: str) -> str:
    """
    persona設定ファイルパスから分析レポート用のスラッグを生成する
    例: persona/config.yaml        -> "kurumi"
        persona/kazuto_config.yaml -> "kazuto"
    """
    stem = Path(persona_path).stem
    if stem == "config":
        return "kurumi"
    return stem.replace("_config", "")
