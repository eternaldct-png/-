"""バックグラウンド処理: 段階ごとの生成（脚本 → キャラ → 場面 → 絵コンテ → 絵と動き → 音 → 書き出し）を1本ずつ順番に行う。"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import art, engine, render
from .store import STAGE_KEYS, STAGE_LABELS, STYLES, Store, new_id

log = logging.getLogger("tsuzuri.worker")

JOB_LABELS = {**STAGE_LABELS, "art_shot": "1カットの絵", "shot_rewrite": "1カットの直し"}

ROLE_OF = {"script": "writer", "characters": "character", "scenes": "scene", "storyboard": "storyboard",
           "art": "animator", "sound": "sound", "render": "editor"}


def project_seed(pid: str) -> int:
    """作品ごとに決まった乱数の種。AI画像の絵柄・顔のばらつきを減らす。"""
    return int(hashlib.sha256(pid.encode()).hexdigest()[:8], 16)


def month_start_iso() -> str:
    local = datetime.now().astimezone()
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat(timespec="seconds")


class Worker:
    def __init__(self, store: Store, data_dir: Path, *, ai_client=None, short_side: int | None = None):
        self.store = store
        self.data_dir = Path(data_dir)
        self.ai_client = ai_client
        self.short_side = short_side  # テストでは小さくして速くする
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.progress: dict[str, str] = {}

    # ── 置き場所 ───────────────────────────────────────────

    def pdir(self, pid: str) -> Path:
        d = self.data_dir / "projects" / pid
        d.mkdir(parents=True, exist_ok=True)
        return d

    def abs(self, pid: str, rel: str) -> Path | None:
        if not rel:
            return None
        p = (self.pdir(pid) / rel).resolve()
        return p if p.is_relative_to(self.pdir(pid).resolve()) and p.exists() else None

    # ── キュー ───────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.store.recover_interrupted()
        self._thread = threading.Thread(target=self._loop, name="tsuzuri-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def enqueue(self, pid: str, kind: str, instruction: str = "") -> dict:
        active = self.store.active_job(pid)
        if active:
            raise ValueError(f"「{JOB_LABELS.get(active['kind'], active['kind'])}」を作っている途中です。終わってから押してください。")
        if kind in STAGE_KEYS:
            self.store.set_stage(pid, kind, "generating", invalidate_after=kind != "render")
        job = self.store.add_job(pid, kind, instruction)
        self._wake.set()
        return job

    def _loop(self) -> None:
        while not self._stop.is_set():
            jobs = self.store.queued_jobs()
            if not jobs:
                self._wake.wait(1.0)
                self._wake.clear()
                continue
            self.run_job(jobs[0])

    def run_job(self, job: dict) -> None:
        pid, kind = job["project_id"], job["kind"]
        self.store.set_job(job["id"], "running")
        try:
            getattr(self, f"do_{kind}")(pid, job.get("instruction") or "")
        except Exception as e:  # noqa: BLE001 — どんな失敗でも画面に理由を出して止める
            log.exception("job failed")
            msg = str(e) or type(e).__name__
            self.store.set_job(job["id"], "failed", msg)
            if self.store.get_project(pid):
                if kind in STAGE_KEYS:
                    self.store.set_stage(pid, kind, "failed")
                self.store.log(pid, "system", f"⚠️ {JOB_LABELS.get(kind, kind)}で失敗しました: {msg}")
            return
        finally:
            self.progress.pop(pid, None)
        p = self.store.get_project(pid)
        if not p:
            self.store.set_job(job["id"], "done")
            return
        if kind not in STAGE_KEYS:  # 1カットだけの仕事は段階を進めない
            self.store.set_job(job["id"], "done")
            return
        # 段階の状態を先に変えてからジョブを「終わり」にする（画面が「作成中」のまま止まらないように）
        self.store.set_stage(pid, kind, "approved" if kind == "render" else "review")
        self.store.set_job(job["id"], "done")
        if kind != "render" and p["auto"]:
            self.approve(pid, kind, by="director")

    def approve(self, pid: str, stage: str, by: str = "me") -> dict | None:
        """段階を承認して、次の段階を作り始める。次のジョブを返す。"""
        self.store.set_stage(pid, stage, "approved")
        if by == "director":
            self.store.log(pid, "director", f"「{STAGE_LABELS[stage]}」はこれで進めます。")
        i = STAGE_KEYS.index(stage)
        if i + 1 >= len(STAGE_KEYS):
            return None
        nxt = STAGE_KEYS[i + 1]
        p = self.store.get_project(pid)
        if p["stages"].get(nxt) in ("todo", "stale", "failed") or nxt == "render":
            return self.enqueue(pid, nxt)
        return None

    def settings(self) -> dict:
        return self.store.settings()

    def for_ai(self, pid: str, s: dict) -> dict:
        """AIに渡す作品の情報。いつもの決まりごと・この作品の決まりごと・前の回のあらすじを足す。"""
        p = self.store.get_project(pid)
        p["house_rules"] = s.get("house_rules", "")
        prev = self.store.get_project(p["sequel_of"]) if p.get("sequel_of") else None
        if prev and prev["script"].get("scenes"):
            sc = prev["script"]
            p["previous"] = f"「{sc.get('title') or prev['title']}」{sc.get('logline', '')}\n" + "\n".join(
                f"- {x['place']}: {x['summary']}" for x in sc["scenes"])
        return p

    def _size(self, p: dict) -> tuple[int, int]:
        return art.frame_size(p["aspect"], self.short_side or 1080)

    # ── 各段階 ───────────────────────────────────────────

    def do_script(self, pid: str, instruction: str) -> None:
        s = self.settings()
        p = self.for_ai(pid, s)
        eng = engine.resolve_engine(s, self.ai_client)
        self.store.log(pid, "writer", f"脚本を書きます（{engine.ENGINE_LABELS[eng]}）。")
        if instruction and eng == "simple":
            self.store.log(pid, "system", "AIなしモードでは指示を読めません。アイデアの文を並べ直しただけです。脚本は直接書き換えられます。")
        script = engine.gen_script(p, s, instruction, client=self.ai_client, engine=eng)
        n_lines = sum(len(sc["lines"]) for sc in script["scenes"])
        self.store.update_project(pid, script=script, title=p["title"] or script["title"])
        self.store.log(pid, "writer", f"「{script['title']}」{len(script['scenes'])}場面・{n_lines}行で書きました。直したいところがあれば教えてください。")

    def do_characters(self, pid: str, instruction: str) -> None:
        s = self.settings()
        p = self.for_ai(pid, s)
        eng = engine.resolve_engine(s, self.ai_client)
        existing = self.store.characters(pid)
        items = engine.gen_characters(p, s, instruction, existing, client=self.ai_client, engine=eng)
        keep = {c["name"]: c for c in existing}
        for it in items:  # 同じ名前のキャラの画像・声・ライブラリ由来はそのまま残す
            old = keep.get(it["name"])
            if old:
                for k in ("image_path", "voice", "color"):
                    if old.get(k):
                        it[k] = old[k]
                if not it.get("look"):
                    it["look"] = old.get("look", "")
        self.store.replace_characters(pid, items)
        names = "、".join(c["name"] for c in items)
        msg = f"キャラは {names} です。"
        if eng == "simple":
            msg += "見た目は空欄なので、書くか画像を入れてください（画像を入れると絵の段階でそのまま使います）。"
        self.store.log(pid, "character", msg)

    def do_scenes(self, pid: str, instruction: str) -> None:
        s = self.settings()
        p = self.for_ai(pid, s)
        eng = engine.resolve_engine(s, self.ai_client)
        old = {sc["name"]: sc for sc in self.store.scenes(pid)}
        items = engine.gen_scenes(p, s, instruction, client=self.ai_client, engine=eng)
        for it in items:
            if it["name"] in old and old[it["name"]].get("image_path"):
                it["image_path"] = old[it["name"]]["image_path"]
        self.store.replace_scenes(pid, items)
        self.store.log(pid, "scene", f"場面は {len(items)} つ: " + "、".join(i["name"] for i in items) + "。背景の画像を入れるとそのまま使います。")

    def do_storyboard(self, pid: str, instruction: str) -> None:
        s = self.settings()
        p = self.for_ai(pid, s)
        eng = engine.resolve_engine(s, self.ai_client)
        chars, scenes = self.store.characters(pid), self.store.scenes(pid)
        shots = engine.gen_storyboard(p, s, chars, scenes, instruction, self.store.shots(pid), client=self.ai_client, engine=eng)
        self.store.replace_shots(pid, shots)
        warns = engine.check_shots(p, self.store.shots(pid), s)
        total = sum(x["seconds"] for x in shots)
        self.store.log(pid, "storyboard", f"{len(shots)}カット・合計{total:.1f}秒に割りました。" + (" 注意: " + " / ".join(warns) if warns else ""))

    def do_art(self, pid: str, instruction: str) -> None:
        """全部のカットの絵を作る。instruction が "missing" なら、絵が無い・失敗したカットだけ作る（お金と時間の節約）。"""
        p, s = self.store.get_project(pid), self.settings()
        shots = self.store.shots(pid)
        if not shots:
            raise ValueError("カットがありません。絵コンテを先に作ってください。")
        only_missing = instruction == "missing"
        targets = [sh for sh in shots if not (sh["image_source"] == "upload" and self.abs(pid, sh["image_path"]))]
        if only_missing:
            targets = [sh for sh in targets if sh["error"] or not self.abs(pid, sh["image_path"])]
        img_engine, vid_engine = s.get("image_engine", "placeholder"), s.get("video_engine", "camera")
        if img_engine == "fal" or vid_engine == "fal":
            self._check_budget(s, targets, img_engine, vid_engine)
        ok, failed = 0, []
        for i, sh in enumerate(targets):
            self.progress[pid] = f"カット {sh['sort'] + 1} の絵（{i + 1}/{len(targets)}）"
            try:
                self._make_shot(pid, p, s, sh)
                ok += 1
            except Exception as e:  # noqa: BLE001 — 1カットの失敗で全部を止めない
                log.warning("shot failed: %s", e)
                self.store.update_shot(sh["id"], error=str(e)[:500])
                failed.append(sh["sort"] + 1)
        kept = len(shots) - len([x for x in shots if x in targets]) if not only_missing else 0
        how = "fal.ai の画像生成" if img_engine == "fal" else "仮の絵（キャラと場面の画像を合成）"
        motion = "AI動画（fal.ai）" if vid_engine == "fal" else "カメラの動き（寄り・引き・パン）"
        msg = f"{ok}カットの絵を{how}で作りました" + (f"（自分の絵 {kept}カットはそのまま）" if kept else "") + f"。動きは{motion}です。"
        if failed:
            msg += f" ⚠️ カット{'・'.join(map(str, failed))}は失敗しました。「絵が無いカットだけ作る」で、そのカットだけやり直せます（できたカットの分はかかりません）。"
        self.store.log(pid, "animator", msg)
        if targets and not ok:
            raise ValueError("全部のカットで失敗しました。理由はカットに表示しています。")

    def _make_shot(self, pid: str, p: dict, s: dict, sh: dict, note: str = "") -> None:
        """1カットの絵（と、設定によっては動画）を作る。fal.ai は通信の失敗なら1回だけやり直す。"""
        size = self._size(p)
        img_engine, vid_engine = s.get("image_engine", "placeholder"), s.get("video_engine", "camera")
        (self.pdir(pid) / "shots").mkdir(exist_ok=True)
        rel = f"shots/{sh['id']}_{new_id()[:8]}.png"
        if img_engine == "fal":
            prompt = self.image_prompt(pid, p, sh, note)
            self._retry(lambda: art.fal_image(s["fal_image_model"], prompt, size, self.pdir(pid) / rel, seed=project_seed(pid)))
            self.store.add_spend(float(s.get("fal_image_yen") or 0), f"画像 {pid[:6]} カット{sh['sort'] + 1}")
            source = "fal"
        else:
            chars = {c["name"]: dict(c, image_abs=str(self.abs(pid, c["image_path"]) or "")) for c in self.store.characters(pid)}
            scene = self.store.get_scene(sh["scene_id"]) if sh["scene_id"] else None
            if scene:
                scene["image_abs"] = str(self.abs(pid, scene["image_path"]) or "")
            cs = [chars[n] for n in sh["characters"] if n in chars]
            art.compose_shot(size, scene, cs, seed=sh["sort"] + 7, camera=sh["camera"]).save(self.pdir(pid) / rel)
            source = "placeholder"
        if sh["image_path"] != rel and sh["image_source"] != "upload":
            self._remove_old(pid, sh["image_path"])
        self.store.update_shot(sh["id"], image_path=rel, image_source=source, error="")
        if vid_engine == "fal":
            still = self.pdir(pid) / rel
            vrel = f"shots/{sh['id']}_{new_id()[:8]}.mp4"
            self._retry(lambda: art.fal_video(s["fal_video_model"], self.image_prompt(pid, p, sh, note), art.data_uri(still),
                                              sh["seconds"], self.pdir(pid) / vrel))
            self.store.add_spend(float(s.get("fal_video_yen_per_sec") or 0) * (10 if sh["seconds"] > 5 else 5), f"動画 {pid[:6]} カット{sh['sort'] + 1}")
            self._remove_old(pid, sh["video_path"])
            self.store.update_shot(sh["id"], video_path=vrel)
        elif sh.get("video_path"):
            self.store.update_shot(sh["id"], video_path="")

    def image_prompt(self, pid: str, p: dict, sh: dict, note: str = "") -> str:
        """AI画像のプロンプト。毎回、絵柄・キャラの見た目・場面の説明を同じ言葉で入れて、カットごとのばらつきを減らす。"""
        style_en = STYLES.get(p["style"], STYLES["anime"])[2]
        chars = {c["name"]: c for c in self.store.characters(pid)}
        looks = [f"{n}: {chars[n]['look']}" for n in sh["characters"] if n in chars and chars[n]["look"].strip()]
        scene = self.store.get_scene(sh["scene_id"]) if sh["scene_id"] else None
        parts = [style_en + ".", sh["image_prompt"] or sh["action"]]
        if looks:
            parts.append("Characters (keep exactly the same design in every shot): " + " / ".join(looks))
        if scene and scene["description"].strip():
            parts.append("Background: " + scene["description"])
        if note:
            parts.append("Change: " + note)
        return " ".join(parts)

    def _retry(self, fn):
        try:
            return fn()
        except art.ArtError as e:
            if "つながりません" not in str(e) and "時間内" not in str(e):
                raise
            time.sleep(2)
            return fn()

    def do_art_shot(self, pid: str, instruction: str) -> None:
        d = json.loads(instruction or "{}")
        sh = self.store.get_shot(d.get("shot_id", ""))
        if not sh or sh["project_id"] != pid:
            raise ValueError("カットが見つかりません。")
        p, s = self.store.get_project(pid), self.settings()
        if s.get("image_engine") == "fal" or s.get("video_engine") == "fal":
            self._check_budget(s, [sh], s.get("image_engine"), s.get("video_engine"))
        if sh["image_source"] == "upload":
            sh["image_source"] = ""  # 「この絵だけ作り直す」は自分の絵より優先する（押した人の意思）
        try:
            self._make_shot(pid, p, s, sh, note=str(d.get("note") or "")[:500])
        except Exception as e:
            self.store.update_shot(sh["id"], error=str(e)[:500])
            raise
        self.store.set_stage(pid, "art", "review" if p["stages"]["art"] != "approved" else "approved", invalidate_after=True)
        self.store.log(pid, "animator", f"カット{sh['sort'] + 1}の絵だけ作り直しました（ほかのカットはそのまま）。")

    def do_shot_rewrite(self, pid: str, instruction: str) -> None:
        d = json.loads(instruction or "{}")
        sh = self.store.get_shot(d.get("shot_id", ""))
        if not sh or sh["project_id"] != pid:
            raise ValueError("カットが見つかりません。")
        s = self.settings()
        p = self.for_ai(pid, s)
        new = engine.rewrite_shot(p, s, sh, self.store.characters(pid), self.store.scenes(pid), str(d.get("note") or ""), client=self.ai_client)
        self.store.update_shot(sh["id"], **{k: new[k] for k in ("seconds", "scene_id", "characters", "camera", "action", "speaker",
                                                                 "dialogue", "caption", "image_prompt")})
        st = p["stages"]["storyboard"]
        self.store.set_stage(pid, "storyboard", st if st in ("review", "approved") else "review", invalidate_after=True)
        self.store.log(pid, "storyboard", f"カット{sh['sort'] + 1}だけ直しました（ほかのカットはそのまま）。")

    def _check_budget(self, s: dict, shots: list[dict], img_engine: str, vid_engine: str) -> None:
        est = 0.0
        n_img = len(shots)
        if img_engine == "fal":
            est += n_img * float(s.get("fal_image_yen") or 0)
        if vid_engine == "fal":
            est += sum((10 if x["seconds"] > 5 else 5) * float(s.get("fal_video_yen_per_sec") or 0) for x in shots)
        budget = float(s.get("monthly_budget_jpy") or 0)
        spent = self.store.spend_since(month_start_iso())
        if budget > 0 and spent + est > budget:
            raise ValueError(f"fal.ai の月の上限（{budget:,.0f}円）を超えるので止めました。今月 約{spent:,.0f}円 + 今回 約{est:,.0f}円。"
                             "設定で上限を上げるか、仮の絵に切り替えてください。")

    def _remove_old(self, pid: str, rel: str) -> None:
        p = self.abs(pid, rel)
        if p and p.parent.name == "shots":
            p.unlink(missing_ok=True)

    def do_sound(self, pid: str, instruction: str) -> None:
        p, s = self.store.get_project(pid), self.settings()
        vdir = self.pdir(pid) / "voice"
        shutil.rmtree(vdir, ignore_errors=True)
        vdir.mkdir()
        chars = {c["name"]: c for c in self.store.characters(pid)}
        n = 0
        if s.get("voice_engine", "say") == "say" and render.say_available():
            shots = self.store.shots(pid)
            for i, sh in enumerate(shots):
                if not sh["dialogue"].strip():
                    continue
                if self.abs(pid, sh["voice_path"]):
                    continue  # 自分で録った声があるカットは読み上げない
                self.progress[pid] = f"カット {i + 1}/{len(shots)} の声"
                ch = chars.get(sh["speaker"]) or {}
                voice = ch.get("voice") or s.get("default_voice") or ""
                if render.make_voice(sh["dialogue"], voice, vdir / f"{sh['id']}.wav", rate=int(ch.get("voice_rate") or 0)):
                    n += 1
            msg = f"{n}カットのセリフを読み上げました（Mac の読み上げ）。"
        elif s.get("voice_engine") == "none":
            msg = "声は付けない設定です（字幕だけ）。"
        else:
            msg = "このPCには読み上げ（say）が無いので、声なし・字幕だけで書き出します。"
        rec = sum(1 for sh in self.store.shots(pid) if self.abs(pid, sh["voice_path"]))
        if rec:
            msg += f" 自分で録った声 {rec}カットはそれを使います。"
        msg += " BGM: " + ("あり" if self.abs(pid, p["bgm_path"]) else "なし（入れるなら下からアップロード）")
        self.store.log(pid, "sound", msg)

    def voice_files(self, pid: str) -> dict:
        """カットごとの声。自分で録った声 > 読み上げ。"""
        vdir = self.pdir(pid) / "voice"
        out = {f.stem: f for f in vdir.glob("*.wav")} if vdir.exists() else {}
        for sh in self.store.shots(pid):
            rec = self.abs(pid, sh["voice_path"])
            if rec:
                out[sh["id"]] = rec
        return out

    def do_render(self, pid: str, instruction: str) -> None:
        p, s = self.store.get_project(pid), self.settings()
        shots = self.store.shots(pid)
        stills, videos = {}, {}
        for sh in shots:
            st = self.abs(pid, sh["image_path"])
            if not st:
                raise ValueError(f"カット{sh['sort'] + 1}に絵がありません。「絵と動き」を作り直してください。")
            stills[sh["id"]] = st
            v = self.abs(pid, sh["video_path"])
            if v:
                videos[sh["id"]] = v
        stale = [STAGE_LABELS[k] for k in STAGE_KEYS[:-1] if p["stages"].get(k) == "stale"]
        rdir = self.pdir(pid) / "render"
        rdir.mkdir(exist_ok=True)
        work = self.pdir(pid) / "work"
        shutil.rmtree(work, ignore_errors=True)
        name = f"render/{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        self.store.log(pid, "editor", f"{len(shots)}カットをつないで書き出します。")

        def prog(i, n):
            self.progress[pid] = f"書き出し {i}/{n} カット"

        warns = render.render_project(shots, self._size(p), work, self.pdir(pid) / name, stills=stills, videos=videos,
                                      voices=self.voice_files(pid), bgm=self.abs(pid, p["bgm_path"]),
                                      bgm_volume=p["bgm_volume"], subtitles=s.get("subtitles", "1") == "1", progress=prog)
        if stale:
            warns.insert(0, "古い段階があります（" + "・".join(stale) + "）。直した内容が反映されていない可能性があります")
        shutil.rmtree(work, ignore_errors=True)
        old = self.abs(pid, p["render_path"])
        render.poster(self.pdir(pid) / name, self.pdir(pid) / "render" / "poster.jpg")
        self.store.update_project(pid, render_path=name, render_warnings=warns)
        if old and old.name != Path(name).name:
            old.unlink(missing_ok=True)  # 前の書き出しは消す（ディスクを食わないように）
        total = sum(x["seconds"] for x in shots)
        self.store.log(pid, "editor", f"1本に綴じました（{total:.1f}秒）。プレーヤーで見て、よければダウンロードしてください。"
                       + (" 注意: " + " / ".join(warns) if warns else ""))
