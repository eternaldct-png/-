"""
Claude Code ⇔ Gemini TTS をつなぐ MCP サーバー（stdio）

リポジトリ直下の .mcp.json に登録済み。Claude Code をこのリポジトリで起動すると
「gemini-tts」サーバーとして読み込まれ、次のツールが使えるようになる:

    text_to_speech  テキスト → 音声ファイル（.wav / .mp3）
    list_voices     使える音声の一覧

事前準備: pip install -r requirements-mcp.txt / 環境変数 GEMINI_API_KEY
詳細: docs/gemini_tts_setup.md
"""
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_tts  # noqa: E402

mcp = FastMCP("gemini-tts")


@mcp.tool()
def text_to_speech(
    text: str,
    voice: str = gemini_tts.DEFAULT_VOICE,
    style: str = "",
    speakers: dict[str, str] | None = None,
    output_path: str = "",
    model: str = "",
) -> str:
    """Gemini TTS（デフォルト: gemini-3.8-flash-tts）でテキストを読み上げ、音声ファイルを保存してパスを返す。

    Args:
        text: 読み上げるテキスト。日本語OK。<laugh> <sigh> <short pause> などのタグで間や笑いを入れられる。
              2人の掛け合いにするときは「話者名: セリフ」の行で書き、speakers を指定する。
        voice: プリセット音声名（例: Kore, Puck, Aoede, Charon）。一覧は list_voices で確認。
        style: 読み上げ方の指示（例: "明るく元気に", "ささやくように", "ラジオDJ風にテンポよく"）。
        speakers: 2人の掛け合い用。{"話者名": "音声名"} 例: {"kazuto": "Puck", "あまりん": "Kore"}
        output_path: 保存先（.wav か .mp3）。空なら media/tts_output/tts_日時.wav
        model: モデル名を上書きするとき（例: gemini-3.8-flash-lite-tts）。空なら環境変数かデフォルト。
    """
    try:
        path = gemini_tts.text_to_speech(
            text,
            output=output_path or None,
            voice=voice,
            style=style,
            speakers=speakers or None,
            model=model or None,
        )
    except gemini_tts.GeminiTTSError as e:
        return f"エラー: {e}"
    return f"音声を保存しました: {path}"


@mcp.tool()
def list_voices() -> str:
    """Gemini TTS で使えるプリセット音声の一覧（名前と声の特徴）を返す。"""
    return "\n".join(f"{name}: {desc}" for name, desc in gemini_tts.PREBUILT_VOICES.items())


if __name__ == "__main__":
    mcp.run()
