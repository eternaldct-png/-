"""文章の段階（脚本・キャラ・場面・絵コンテ）を作る。

どのAIで書くか（設定の ai_engine）:
- simple : AIなし。自分が書いたアイデアの文をそのまま使って、脚本とカット割りに並べる（作り話はしない）。何も入れなくても動く
- ollama : 端末内AI（Ollama）。このPCの中だけで動く・無料
- claude : Claude API（お金がかかる）。**明示して選んだときだけ**使う
- auto   : Ollama が動いていて設定のモデルがあれば ollama、無ければ simple
"""
from __future__ import annotations

import json
import os
import re

from tools.meeting_notes import local_ai

from .store import CAMERAS, STYLES

ENGINE_LABELS = {"claude": "Claude API", "ollama": "端末内AI（Ollama）", "simple": "AIなし（自分の文を並べる）"}
NARRATOR = "ナレーション"


class EngineError(RuntimeError):
    pass


def resolve_engine(settings: dict, client=None) -> str:
    choice = (settings.get("ai_engine") or "auto").strip()
    if choice in ENGINE_LABELS:
        return choice
    if client is not None:  # テストで Claude の代わりを渡したとき
        return "claude"
    models = local_ai.ollama_models()
    if models is not None and local_ai.has_model(models, settings.get("ollama_model") or local_ai.DEFAULT_OLLAMA_MODEL):
        return "ollama"
    return "simple"


# ── JSON スキーマ（AI の返事の形を固定する） ─────────────────────

def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_S = {"type": "string"}
SCRIPT_SCHEMA = _obj({
    "title": _S, "logline": _S,
    "scenes": {"type": "array", "items": _obj({
        "place": _S, "summary": _S,
        "lines": {"type": "array", "items": _obj({"speaker": _S, "text": _S})},
    })},
})
CHARACTERS_SCHEMA = _obj({"characters": {"type": "array", "items": _obj({"name": _S, "look": _S, "personality": _S})}})
SCENES_SCHEMA = _obj({"scenes": {"type": "array", "items": _obj({"name": _S, "description": _S})}})
STORYBOARD_SCHEMA = _obj({"shots": {"type": "array", "items": _obj({
    "seconds": {"type": "number"}, "scene": _S, "characters": {"type": "array", "items": _S},
    "camera": {"type": "string", "enum": list(CAMERAS)}, "action": _S, "speaker": _S, "dialogue": _S,
    "caption": _S, "image_prompt": _S,
})}})


# ── AI の呼び出し ───────────────────────────────────────────

def _claude_client():
    import anthropic
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise EngineError("ANTHROPIC_API_KEY が設定されていません（~/Tsuzuri/.env に書いて起動し直してください）。")
    return anthropic.Anthropic()


def _llm(engine: str, settings: dict, client, system: str, user: str, schema: dict, max_tokens: int = 8000) -> dict:
    last = None
    for _ in range(2):  # 返事の形が壊れていたら1回だけやり直す
        if engine == "ollama":
            try:
                raw = local_ai.ollama_chat(settings.get("ollama_model") or local_ai.DEFAULT_OLLAMA_MODEL, system, user,
                                           schema=schema, timeout=900, num_ctx=16384)
            except local_ai.LocalAIError as e:
                raise EngineError(str(e)) from e
        elif engine == "claude":
            raw = _claude(client or _claude_client(), settings, system, user, schema, max_tokens)
        else:
            raise EngineError("AIなしモードでは使えません。")
        try:
            return _parse_json(raw)
        except ValueError as e:
            last = e
    raise EngineError(f"AIの返事を読み取れませんでした（{last}）。もう一度押してください。")


def _claude(client, settings, system, user, schema, max_tokens) -> str:
    try:
        r = client.messages.create(
            model=settings.get("claude_model") or "claude-sonnet-5-5",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
    except Exception as e:  # 接続・429・5xx・400
        raise EngineError(f"Claude の呼び出しに失敗しました: {type(e).__name__}: {getattr(e, 'message', e)}") from e
    if getattr(r, "stop_reason", "") == "refusal":
        raise EngineError("AIがこの内容を断りました。アイデアの書き方を変えてみてください。")
    if getattr(r, "stop_reason", "") == "max_tokens":
        raise EngineError("AIの出力が長すぎて途中で切れました。尺を短くするか、カットを減らしてください。")
    return next((b.text for b in r.content if getattr(b, "type", "") == "text"), "")


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("JSON がありません")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(str(e)) from e
    if not isinstance(data, dict):
        raise ValueError("形が違います")
    return data


# ── 共通の前置き ─────────────────────────────────────────────

def _brief(project: dict) -> str:
    style = STYLES.get(project.get("style"), STYLES["anime"])
    kinds = {"story": "物語のショートアニメ", "mv": "曲に合わせたアニメMV", "quick": "説明・告知のショート動画"}
    lines = [
        f"作品の種類: {kinds.get(project.get('kind'), '物語のショートアニメ')}",
        f"絵柄: {style[0]}（{style[1]}）",
        f"縦横比: {project.get('aspect')}",
        f"尺: 約{project.get('duration_sec')}秒",
        f"セリフの言語: {'日本語' if project.get('language', 'ja') == 'ja' else project.get('language')}",
    ]
    if project.get("mood"):
        lines.append(f"雰囲気: {project['mood']}")
    if project.get("previous"):
        lines.append("前の回のあらすじ（この作品はその続き。キャラの性格・設定を変えない）:\n" + project["previous"])
    lines.append("アイデア（ユーザーが書いたもの）:\n" + (project.get("idea") or ""))
    rules = rules_text(project)
    if rules:
        lines.append(rules)
    return "\n".join(lines)


def rules_text(project: dict) -> str:
    """いつもの決まりごと（設定）とこの作品の決まりごと。毎回AIに最優先で渡す（不満: 指示より決まった流れが優先される・長期の記憶がない）。"""
    parts = [x.strip() for x in (project.get("house_rules", ""), project.get("notes", "")) if x and x.strip()]
    if not parts:
        return ""
    return "必ず守る決まりごと（どの指示・どの段階よりも優先する）:\n" + "\n".join(parts)


_RULES = ("ルール: 炎上しそうな話題・実在の人の悪口・根拠のない数字は入れない。"
          "既存のアニメ・ゲームのキャラや作品名をまねない（オリジナルにする）。"
          "どの動画にも使えそうな決まり文句（「〜な人必見」「最後まで見て」「衝撃の結末」など）は使わず、この作品だけの言葉で書く。")


def _instruction_text(instruction: str) -> str:
    return f"\n\n今回の直しの指示（最優先で反映する）:\n{instruction}" if instruction.strip() else ""


def max_chars(seconds: float, settings: dict) -> int:
    try:
        cps = float(settings.get("chars_per_second") or 8)
    except ValueError:
        cps = 8.0
    return max(1, int(seconds * cps))


# ── 脚本 ───────────────────────────────────────────────────

def gen_script(project: dict, settings: dict, instruction: str = "", client=None, engine: str | None = None) -> dict:
    engine = engine or resolve_engine(settings, client)
    if engine == "simple":
        return simple_script(project)
    cps = float(settings.get("chars_per_second") or 8)
    budget = int(project.get("duration_sec", 30) * cps * 0.8)
    system = ("あなたはショートアニメの脚本家です。短い尺で最初の2秒で引き込み、最後に余韻か行動のきっかけを残す脚本を書きます。"
              f"セリフとナレーションの合計は{budget}文字以内（読み上げ8文字/秒で尺に収める）。場面は1〜4個。"
              f"話者はキャラ名か「{NARRATOR}」。{_RULES}")
    user = _brief(project)
    if project.get("script", {}).get("scenes"):
        user += "\n\n今の脚本（直すときの元）:\n" + json.dumps(project["script"], ensure_ascii=False)
    user += _instruction_text(instruction)
    return normalize_script(_llm(engine, settings, client, system, user, SCRIPT_SCHEMA), project)


def normalize_script(data: dict, project: dict) -> dict:
    scenes = []
    for i, s in enumerate(data.get("scenes") or []):
        lines = [{"speaker": str(l.get("speaker") or NARRATOR)[:30], "text": str(l.get("text") or "").strip()[:400]}
                 for l in (s.get("lines") or []) if str(l.get("text") or "").strip()]
        scenes.append({"no": i + 1, "place": str(s.get("place") or f"場面{i + 1}")[:60],
                       "summary": str(s.get("summary") or "")[:400], "lines": lines})
    if not scenes:
        raise EngineError("脚本が空でした。アイデアをもう少し詳しく書いてください。")
    return {"title": str(data.get("title") or project.get("title") or "無題")[:80],
            "logline": str(data.get("logline") or "")[:300], "scenes": scenes}


_LINE = re.compile(r"^\s*([^\s:：「」]{1,12})\s*[:：]\s*「?(.+?)」?\s*$|^\s*([^\s:：「」]{1,12})「(.+?)」\s*$")


def _sentences(text: str) -> list[str]:
    """文に分ける。「」の中の 。！？ では切らない。"""
    out, cur, depth = [], "", 0
    for ch in text or "":
        if ch == "\n":
            out.append(cur)
            cur = ""
            depth = 0
            continue
        cur += ch
        if ch in "「『（(":
            depth += 1
        elif ch in "」』）)":
            depth = max(0, depth - 1)
            if depth == 0 and re.match(r"^\s*[^\s:：「」]{1,12}「", cur):
                out.append(cur)  # 「名前「セリフ」」はそこで1文
                cur = ""
        elif ch in "。！？!?" and depth == 0:
            out.append(cur)
            cur = ""
    out.append(cur)
    return [s.strip() for s in out if s and s.strip()]


def simple_script(project: dict) -> dict:
    """AIなし: アイデアの文を1文ずつセリフ（またはナレーション）にして、3つまでの場面に分ける。"""
    sents = _sentences(project.get("idea", ""))
    if not sents:
        raise EngineError("アイデアが空です。")
    lines = []
    for s in sents:
        m = _LINE.match(s)
        if m:
            speaker, text = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            lines.append({"speaker": speaker, "text": text})
        else:
            lines.append({"speaker": NARRATOR, "text": s})
    n = 1 if len(lines) <= 2 else (2 if len(lines) <= 4 else 3)
    size = -(-len(lines) // n)
    names = ["はじまり", "なかほど", "おわり"] if n == 3 else (["はじまり", "おわり"] if n == 2 else ["ひとつめの場面"])
    scenes = []
    for i in range(n):
        chunk = lines[i * size:(i + 1) * size]
        if chunk:
            scenes.append({"no": i + 1, "place": names[i], "summary": chunk[0]["text"][:80], "lines": chunk})
    title = project.get("title") or re.sub(r"[。！？!?].*$", "", sents[0])[:24]
    return {"title": title, "logline": sents[0][:120], "scenes": scenes}


# ── キャラ ───────────────────────────────────────────────────

PALETTE = ["#e07a5f", "#3d85c6", "#81b29a", "#f2cc8f", "#9b72cf", "#e26d9a", "#5aa9a4", "#c98b3b"]


def gen_characters(project: dict, settings: dict, instruction: str = "", existing: list[dict] | None = None,
                   client=None, engine: str | None = None) -> list[dict]:
    engine = engine or resolve_engine(settings, client)
    if engine == "simple":
        items = simple_characters(project)
    else:
        system = ("あなたはアニメのキャラクターデザイナーです。脚本に出てくるキャラ（ナレーションは除く）の見た目と性格を決めます。"
                  "look は絵を描く人が迷わない具体さで（髪型・髪色・目・服・小物・体格）。1キャラ80文字程度。"
                  f"{_RULES}")
        user = _brief(project) + "\n\n脚本:\n" + json.dumps(project.get("script") or {}, ensure_ascii=False)
        if existing:
            user += "\n\n今のキャラ（直すときの元）:\n" + json.dumps(
                [{k: c.get(k, "") for k in ("name", "look", "personality")} for c in existing], ensure_ascii=False)
        user += _instruction_text(instruction)
        data = _llm(engine, settings, client, system, user, CHARACTERS_SCHEMA)
        items = [{"name": str(c.get("name") or "").strip()[:60], "look": str(c.get("look") or "")[:600],
                  "personality": str(c.get("personality") or "")[:400]}
                 for c in data.get("characters") or [] if str(c.get("name") or "").strip()]
        items = [c for c in items if c["name"] != NARRATOR] or simple_characters(project)
    for i, c in enumerate(items):
        c.setdefault("color", PALETTE[i % len(PALETTE)])
    return items


_HONORIFIC = re.compile(r"([一-龥ァ-ヴーA-Za-z]{1,8}|[ぁ-ん]{2,5})(ちゃん|くん|さん|先輩|先生)")


def simple_characters(project: dict) -> list[dict]:
    names: list[str] = []
    for sc in (project.get("script") or {}).get("scenes", []):
        for l in sc.get("lines", []):
            if l["speaker"] != NARRATOR and l["speaker"] not in names:
                names.append(l["speaker"])
    for m in _HONORIFIC.finditer(project.get("idea", "")):
        base = m.group(1)
        # ひらがなの名前は前の助詞（と・や・の…）までくっつくので外す（「ゆうくんとみかちゃん」→「みかちゃん」）
        while len(base) > 2 and re.fullmatch(r"[ぁ-ん]+", base) and base[0] in "とやのがはもにをで":
            base = base[1:]
        n = base + m.group(2)
        if n not in names and base not in names:
            names.append(n)
    if not names:
        names = ["主人公"]
    return [{"name": n, "look": "", "personality": ""} for n in names[:6]]


# ── 場面 ─────────────────────────────────────────────────────

def gen_scenes(project: dict, settings: dict, instruction: str = "", client=None, engine: str | None = None) -> list[dict]:
    engine = engine or resolve_engine(settings, client)
    if engine == "simple":
        items = [{"name": s["place"], "description": s.get("summary", "")} for s in (project.get("script") or {}).get("scenes", [])]
    else:
        system = ("あなたはアニメの美術（背景）担当です。脚本の場面ごとに、背景の絵の説明を書きます。"
                  "時間帯・天気・場所・光・色をはっきり。人物は書かない。1場面60文字程度。" + _RULES)
        user = _brief(project) + "\n\n脚本:\n" + json.dumps(project.get("script") or {}, ensure_ascii=False) + _instruction_text(instruction)
        data = _llm(engine, settings, client, system, user, SCENES_SCHEMA)
        items = [{"name": str(s.get("name") or "").strip()[:60], "description": str(s.get("description") or "")[:600]}
                 for s in data.get("scenes") or [] if str(s.get("name") or "").strip()]
    seen, out = set(), []
    for i, s in enumerate(items):
        if s["name"] in seen:
            continue
        seen.add(s["name"])
        s["color"] = PALETTE[(i + 3) % len(PALETTE)]
        out.append(s)
    if not out:
        raise EngineError("場面が作れませんでした。脚本を確認してください。")
    return out


# ── 絵コンテ ─────────────────────────────────────────────────

CAMERA_CYCLE = ["zoom_in", "pan_right", "still", "zoom_out", "pan_left"]


def gen_storyboard(project: dict, settings: dict, characters: list[dict], scenes: list[dict], instruction: str = "",
                   existing: list[dict] | None = None, client=None, engine: str | None = None) -> list[dict]:
    engine = engine or resolve_engine(settings, client)
    if engine == "simple":
        shots = simple_storyboard(project, characters, scenes)
    else:
        system = ("あなたはアニメの絵コンテ担当です。脚本をカットに割ります。1カット2〜8秒。"
                  f"dialogue は1カット「秒数×{settings.get('chars_per_second') or 8}文字」以内（長いセリフは複数カットに分ける）。"
                  "scene は場面の一覧の名前から選ぶ。characters はキャラ一覧の名前から選ぶ。"
                  "camera は still / zoom_in / zoom_out / pan_left / pan_right。"
                  "image_prompt は英語で、そのカットの絵（構図・人物の見た目・表情・背景・光）を1文〜3文で。"
                  "caption は画面に出す短い文字（不要なら空）。" + _RULES)
        user = (_brief(project) + "\n\n脚本:\n" + json.dumps(project.get("script") or {}, ensure_ascii=False)
                + "\n\nキャラ:\n" + json.dumps([{k: c.get(k, "") for k in ("name", "look")} for c in characters], ensure_ascii=False)
                + "\n\n場面:\n" + json.dumps([{k: s.get(k, "") for k in ("name", "description")} for s in scenes], ensure_ascii=False))
        if existing:
            user += "\n\n今の絵コンテ（直すときの元）:\n" + json.dumps(
                [{k: s.get(k) for k in ("seconds", "camera", "action", "speaker", "dialogue", "caption", "image_prompt")} for s in existing],
                ensure_ascii=False)
        user += _instruction_text(instruction)
        data = _llm(engine, settings, client, system, user, STORYBOARD_SCHEMA, max_tokens=12000)
        shots = data.get("shots") or []
        if not shots:
            raise EngineError("絵コンテが空でした。")
    return normalize_shots(shots, project, characters, scenes)


def simple_storyboard(project: dict, characters: list[dict], scenes: list[dict]) -> list[dict]:
    style_en = STYLES.get(project.get("style"), STYLES["anime"])[2]
    char_names = [c["name"] for c in characters]
    shots, i = [], 0
    for sc in (project.get("script") or {}).get("scenes", []):
        for l in sc.get("lines", []):
            who = [l["speaker"]] if l["speaker"] in char_names else char_names[:1]
            shots.append({
                "seconds": 0, "scene": sc["place"], "characters": who, "camera": CAMERA_CYCLE[i % len(CAMERA_CYCLE)],
                "action": sc.get("summary", ""), "speaker": l["speaker"], "dialogue": l["text"], "caption": "",
                "image_prompt": f"{style_en}, {sc['place']}, {', '.join(who)}, {l['text']}",
            })
            i += 1
    if not shots:
        raise EngineError("脚本にセリフがありません。")
    return shots


def normalize_shots(shots: list[dict], project: dict, characters: list[dict], scenes: list[dict]) -> list[dict]:
    scene_by_name = {s["name"]: s["id"] for s in scenes if s.get("id")}
    first_scene = scenes[0]["id"] if scenes and scenes[0].get("id") else None
    names = {c["name"] for c in characters}
    out = []
    for s in shots:
        try:
            sec = float(s.get("seconds") or 0)
        except (TypeError, ValueError):
            sec = 0
        out.append({
            "seconds": sec,
            "scene_id": scene_by_name.get(str(s.get("scene") or ""), first_scene),
            "characters": [n for n in (s.get("characters") or []) if n in names][:6],
            "camera": s.get("camera") if s.get("camera") in CAMERAS else "still",
            "action": str(s.get("action") or "")[:400],
            "speaker": str(s.get("speaker") or "")[:30],
            "dialogue": str(s.get("dialogue") or "")[:400],
            "caption": str(s.get("caption") or "")[:80],
            "image_prompt": str(s.get("image_prompt") or "")[:1000],
            "image_path": "", "image_source": "", "video_path": "",
        })
    return fit_seconds(out, float(project.get("duration_sec") or 30))


def fit_seconds(shots: list[dict], total: float) -> list[dict]:
    """秒数を合計の尺に合わせる。秒が無いカットはセリフの長さで割り振る（最短1.5秒）。"""
    if not shots:
        return shots
    weights = [s["seconds"] if s["seconds"] > 0 else max(1.0, len(s.get("dialogue", "")) / 8 + 1) for s in shots]
    scale = total / sum(weights)
    for s, w in zip(shots, weights):
        s["seconds"] = round(min(30.0, max(1.5, w * scale)), 1)
    return shots


# ── チェック ─────────────────────────────────────────────────

def check_shots(project: dict, shots: list[dict], settings: dict) -> list[str]:
    warns = []
    for i, s in enumerate(shots, 1):
        limit = max_chars(s["seconds"], settings)
        if len(s.get("dialogue") or "") > limit:
            warns.append(f"カット{i}: セリフが長すぎます（{len(s['dialogue'])}文字 / {s['seconds']}秒なら{limit}文字まで）")
    total = sum(s["seconds"] for s in shots)
    target = float(project.get("duration_sec") or 30)
    if shots and abs(total - target) > target * 0.2:
        warns.append(f"合計の尺が {total:.1f}秒 です（目標 {target:.0f}秒）")
    return warns


# ── 1カットだけ直す（不満: 細かく直せない・全部作り直すとお金と時間がかかる） ─────────

SHOT_SCHEMA = _obj({k: v for k, v in STORYBOARD_SCHEMA["properties"]["shots"]["items"]["properties"].items()})


def rewrite_shot(project: dict, settings: dict, shot: dict, characters: list[dict], scenes: list[dict], instruction: str,
                 client=None, engine: str | None = None) -> dict:
    engine = engine or resolve_engine(settings, client)
    if engine == "simple":
        raise EngineError("AIなしモードでは指示を読めません。カットの欄を直接書き換えてください（設定で Ollama か Claude を選ぶと使えます）。")
    scene_name = next((s["name"] for s in scenes if s.get("id") == shot.get("scene_id")), "")
    system = ("あなたはアニメの絵コンテ担当です。指定された1カットだけを、指示どおりに直します。ほかのカットは変えません。"
              f"dialogue は「秒数×{settings.get('chars_per_second') or 8}文字」以内。scene は場面の一覧から、characters はキャラ一覧から選ぶ。"
              "image_prompt は英語。" + _RULES)
    user = (_brief(project)
            + "\n\nキャラ:\n" + json.dumps([{k: c.get(k, "") for k in ("name", "look")} for c in characters], ensure_ascii=False)
            + "\n\n場面:\n" + json.dumps([s["name"] for s in scenes], ensure_ascii=False)
            + "\n\n直すカット:\n" + json.dumps({"seconds": shot["seconds"], "scene": scene_name, "characters": shot["characters"],
                                                 "camera": shot["camera"], "action": shot["action"], "speaker": shot["speaker"],
                                                 "dialogue": shot["dialogue"], "caption": shot["caption"],
                                                 "image_prompt": shot["image_prompt"]}, ensure_ascii=False)
            + _instruction_text(instruction))
    data = _llm(engine, settings, client, system, user, SHOT_SCHEMA, max_tokens=3000)
    out = normalize_shots([data], dict(project, duration_sec=shot["seconds"]), characters, scenes)[0]
    if float(data.get("seconds") or 0) > 0:
        out["seconds"] = round(min(30.0, max(0.5, float(data["seconds"]))), 1)
    return out


# ── そろっているかのチェック（不満: キャラ・場面がそろわない） ─────────────────────

def consistency_warnings(characters: list[dict], scenes: list[dict], shots: list[dict], image_engine: str) -> list[str]:
    warns = []
    used = {n for s in shots for n in s.get("characters", [])}
    for c in characters:
        if c["name"] not in used:
            continue
        if not c.get("image_path") and not (c.get("look") or "").strip():
            warns.append(f"キャラ「{c['name']}」に画像も見た目の説明もありません。カットごとに見た目がばらつく原因になります")
        elif image_engine == "fal" and not (c.get("look") or "").strip():
            warns.append(f"キャラ「{c['name']}」の見た目の説明が空です。AI画像ではカットごとに顔や服が変わりやすくなります")
    for i, s in enumerate(shots, 1):
        if not s.get("scene_id") and scenes:
            warns.append(f"カット{i}: 場面が「なし」なので、背景が他のカットとそろいません")
    return warns


def similar_ratio(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    a, b = re.sub(r"\s+", "", a or ""), re.sub(r"\s+", "", b or "")
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()
