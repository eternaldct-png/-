"""バックグラウンド処理: 段階ごとの生成（脚本 → キャラ → 場面 → 絵コンテ → 絵と動き → 音 → 書き出し）を1本ずつ順番に行う。"""
from __future__ import annotations

import logging
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import art, engine, render
from .store import STAGE_KEYS, STAGE_LABELS, STYLES, Store, new_id

log = logging.getLogger("komadori.worker")

ROLE_OF = {"script": "writer", "characters": "character", "scenes": "scene", "storyboard": "storyboard",
           "art": "animator", "sound": "sound", "render": "editor"}


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
        self._thread = threading.Thread(target=self._loop, name="komadori-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def enqueue(self, pid: str, kind: str, instruction: str = "") -> dict:
        active = self.store.active_job(pid)
        if active:
            raise ValueError(f"「{STAGE_LABELS.get(active['kind'], active['kind'])}」を作っている途中です。終わってから押してください。")
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
                self.store.set_stage(pid, kind, "failed")
                self.store.log(pid, "system", f"⚠️ {STAGE_LABELS.get(kind, kind)}で失敗しました: {msg}")
            return
        finally:
            self.progress.pop(pid, None)
        p = self.store.get_project(pid)
        if not p:
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

    def _size(self, p: dict) -> tuple[int, int]:
        return art.frame_size(p["aspect"], self.short_side or 1080)

    # ── 各段階 ───────────────────────────────────────────

    def do_script(self, pid: str, instruction: str) -> None:
        p, s = self.store.get_project(pid), self.settings()
        eng = engine.resolve_engine(s, self.ai_client)
        self.store.log(pid, "writer", f"脚本を書きます（{engine.ENGINE_LABELS[eng]}）。")
        if instruction and eng == "simple":
            self.store.log(pid, "system", "AIなしモードでは指示を読めません。アイデアの文を並べ直しただけです。脚本は直接書き換えられます。")
        script = engine.gen_script(p, s, instruction, client=self.ai_client, engine=eng)
        n_lines = sum(len(sc["lines"]) for sc in script["scenes"])
        self.store.update_project(pid, script=script, title=p["title"] or script["title"])
        self.store.log(pid, "writer", f"「{script['title']}」{len(script['scenes'])}場面・{n_lines}行で書きました。直したいところがあれば教えてください。")

    def do_characters(self, pid: str, instruction: str) -> None:
        p, s = self.store.get_project(pid), self.settings()
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
        p, s = self.store.get_project(pid), self.settings()
        eng = engine.resolve_engine(s, self.ai_client)
        old = {sc["name"]: sc for sc in self.store.scenes(pid)}
        items = engine.gen_scenes(p, s, instruction, client=self.ai_client, engine=eng)
        for it in items:
            if it["name"] in old and old[it["name"]].get("image_path"):
                it["image_path"] = old[it["name"]]["image_path"]
        self.store.replace_scenes(pid, items)
        self.store.log(pid, "scene", f"場面は {len(items)} つ: " + "、".join(i["name"] for i in items) + "。背景の画像を入れるとそのまま使います。")

    def do_storyboard(self, pid: str, instruction: str) -> None:
        p, s = self.store.get_project(pid), self.settings()
        eng = engine.resolve_engine(s, self.ai_client)
        chars, scenes = self.store.characters(pid), self.store.scenes(pid)
        shots = engine.gen_storyboard(p, s, chars, scenes, instruction, self.store.shots(pid), client=self.ai_client, engine=eng)
        self.store.replace_shots(pid, shots)
        warns = engine.check_shots(p, self.store.shots(pid), s)
        total = sum(x["seconds"] for x in shots)
        self.store.log(pid, "storyboard", f"{len(shots)}カット・合計{total:.1f}秒に割りました。" + (" 注意: " + " / ".join(warns) if warns else ""))

    def do_art(self, pid: str, instruction: str) -> None:
        p, s = self.store.get_project(pid), self.settings()
        size = self._size(p)
        shots = self.store.shots(pid)
        if not shots:
            raise ValueError("カットがありません。絵コンテを先に作ってください。")
        chars = {c["name"]: dict(c, image_abs=str(self.abs(pid, c["image_path"]) or "")) for c in self.store.characters(pid)}
        scenes = {sc["id"]: dict(sc, image_abs=str(self.abs(pid, sc["image_path"]) or "")) for sc in self.store.scenes(pid)}
        img_engine, vid_engine = s.get("image_engine", "placeholder"), s.get("video_engine", "camera")
        if img_engine == "fal" or vid_engine == "fal":
            self._check_budget(s, shots, img_engine, vid_engine)
        out = self.pdir(pid) / "shots"
        out.mkdir(exist_ok=True)
        style_en = STYLES.get(p["style"], STYLES["anime"])[2]
        made = kept = 0
        for i, sh in enumerate(shots):
            self.progress[pid] = f"カット {i + 1}/{len(shots)} の絵"
            if sh["image_source"] == "upload" and self.abs(pid, sh["image_path"]):
                kept += 1
            else:
                rel = f"shots/{sh['id']}_{new_id()[:8]}.png"
                if img_engine == "fal":
                    prompt = f"{style_en}. {sh['image_prompt'] or sh['action']}"
                    art.fal_image(s["fal_image_model"], prompt, size, self.pdir(pid) / rel)
                    self.store.add_spend(float(s.get("fal_image_yen") or 0), f"画像 {pid[:6]} カット{i + 1}")
                    source = "fal"
                else:
                    cs = [chars[n] for n in sh["characters"] if n in chars]
                    art.compose_shot(size, scenes.get(sh["scene_id"]), cs, seed=i + 7).save(self.pdir(pid) / rel)
                    source = "placeholder"
                if sh["image_path"] != rel:
                    self._remove_old(pid, sh["image_path"])
                self.store.update_shot(sh["id"], image_path=rel, image_source=source)
                made += 1
            if vid_engine == "fal":
                sh = self.store.get_shot(sh["id"])
                still = self.abs(pid, sh["image_path"])
                rel = f"shots/{sh['id']}_{new_id()[:8]}.mp4"
                art.fal_video(s["fal_video_model"], sh["image_prompt"] or sh["action"], art.data_uri(still), sh["seconds"], self.pdir(pid) / rel)
                self.store.add_spend(float(s.get("fal_video_yen_per_sec") or 0) * (10 if sh["seconds"] > 5 else 5), f"動画 {pid[:6]} カット{i + 1}")
                self._remove_old(pid, sh["video_path"])
                self.store.update_shot(sh["id"], video_path=rel)
            elif sh.get("video_path"):
                self.store.update_shot(sh["id"], video_path="")
        how = {"placeholder": "仮の絵（キャラと場面の画像を合成）", "fal": "fal.ai の画像生成"}[img_engine if img_engine in ("fal",) else "placeholder"]
        motion = "AI動画（fal.ai）" if vid_engine == "fal" else "カメラの動き（寄り・引き・パン）"
        self.store.log(pid, "animator", f"{made}カットの絵を{how}で作りました" + (f"（自分の画像 {kept}カットはそのまま）" if kept else "")
                       + f"。動きは{motion}で付けます。")

    def _check_budget(self, s: dict, shots: list[dict], img_engine: str, vid_engine: str) -> None:
        est = 0.0
        n_img = sum(1 for x in shots if x["image_source"] != "upload")
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
                self.progress[pid] = f"カット {i + 1}/{len(shots)} の声"
                voice = (chars.get(sh["speaker"]) or {}).get("voice") or s.get("default_voice") or ""
                if render.make_voice(sh["dialogue"], voice, vdir / f"{sh['id']}.wav"):
                    n += 1
            msg = f"{n}カットのセリフを読み上げました（Mac の読み上げ）。"
        elif s.get("voice_engine") == "none":
            msg = "声は付けない設定です（字幕だけ）。"
        else:
            msg = "このPCには読み上げ（say）が無いので、声なし・字幕だけで書き出します。"
        msg += " BGM: " + ("あり" if self.abs(pid, p["bgm_path"]) else "なし（入れるなら下からアップロード）")
        self.store.log(pid, "sound", msg)

    def voice_files(self, pid: str) -> dict:
        vdir = self.pdir(pid) / "voice"
        return {f.stem: f for f in vdir.glob("*.wav")} if vdir.exists() else {}

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
        self.store.log(pid, "editor", f"できました（{total:.1f}秒）。下のプレーヤーで確認して、ダウンロードしてください。"
                       + (" 注意: " + " / ".join(warns) if warns else ""))
