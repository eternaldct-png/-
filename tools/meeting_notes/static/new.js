// 新しい会議: 録音・ファイル・文字起こし
(function () {
  "use strict";
  const { api, toast, withLoading, toLocalInput, localInputToUTC } = window.MN;
  const $ = (id) => document.getElementById(id);

  $("started_at").value = toLocalInput(new Date());

  function baseForm(source) {
    const meta = new FormData($("meta"));
    const fd = new FormData();
    fd.append("source", source);
    fd.append("title", meta.get("title") || "");
    fd.append("started_at", localInputToUTC(meta.get("started_at")));
    fd.append("participants", meta.get("participants") || "");
    fd.append("tags", meta.get("tags") || "");
    return fd;
  }

  async function send(fd, btn) {
    const data = await withLoading(btn, () => api("POST", "/api/meetings", fd));
    if (data && data.url) { recordedBlob = null; location.href = data.url; }
  }

  // ── ファイル ──
  $("upload-save").addEventListener("click", (e) => {
    const f = $("audio-file").files[0];
    if (!f) { toast("ファイルを選んでください", "error"); return; }
    const fd = baseForm("upload");
    fd.append("audio", f, f.name);
    send(fd, e.currentTarget);
  });

  // ── 文字起こし ──
  $("text-save").addEventListener("click", (e) => {
    const f = $("transcript-file").files[0];
    const text = $("transcript-text").value;
    if (!f && !text.trim()) { toast("ファイルを選ぶか、文字起こしを貼り付けてください", "error"); return; }
    const fd = baseForm("transcript");
    if (f) fd.append("transcript_file", f, f.name); else fd.append("transcript_text", text);
    send(fd, e.currentTarget);
  });

  // ── 録音 ──
  let recorder = null, chunks = [], streams = [], audioCtx = null, startedAt = 0, elapsed = 0, timer = null, recordedBlob = null, mime = "";
  const status = (msg) => { $("rec-status").textContent = msg; };
  $("with-tab").addEventListener("change", () => { $("tab-help").hidden = !$("with-tab").checked; });

  function pickMime() {
    const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
    return types.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || "";
  }
  function clock(ms) {
    const s = Math.floor(ms / 1000), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
    const p = (n) => String(n).padStart(2, "0");
    return h ? `${h}:${p(m)}:${p(r)}` : `${p(m)}:${p(r)}`;
  }
  function tick() { $("rec-time").textContent = clock(elapsed + (recorder && recorder.state === "recording" ? Date.now() - startedAt : 0)); }

  async function start() {
    if (!navigator.mediaDevices || !window.MediaRecorder) { toast("このブラウザは録音に対応していません。Chrome か Edge を使ってください。", "error"); return; }
    try {
      const mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      streams = [mic];
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const dest = audioCtx.createMediaStreamDestination();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      audioCtx.createMediaStreamSource(mic).connect(dest);
      audioCtx.createMediaStreamSource(mic).connect(analyser);
      if ($("with-tab").checked) {
        let disp;
        try {
          disp = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
        } catch (e) {
          throw new Error("画面の共有がキャンセルされました。相手の声を録らない場合はチェックを外してください。");
        }
        streams.push(disp);
        if (!disp.getAudioTracks().length) {
          toast("共有した画面に音声がありません。「タブの音声も共有」をオンにしてやり直すと相手の声も録れます。マイクだけで録音を続けます。", "error");
        } else {
          const tabAudio = new MediaStream(disp.getAudioTracks());
          audioCtx.createMediaStreamSource(tabAudio).connect(dest);
          audioCtx.createMediaStreamSource(tabAudio).connect(analyser);
        }
        disp.getVideoTracks().forEach((t) => (t.onended = () => { if (recorder && recorder.state !== "inactive") stop(); }));
      }
      const buf = new Uint8Array(analyser.frequencyBinCount);
      (function meter() {
        if (!audioCtx) return;
        analyser.getByteTimeDomainData(buf);
        let peak = 0; for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
        $("meter").style.width = Math.min(100, (peak / 64) * 100) + "%";
        requestAnimationFrame(meter);
      })();
      mime = pickMime();
      recorder = new MediaRecorder(dest.stream, mime ? { mimeType: mime, audioBitsPerSecond: 64000 } : undefined);
      chunks = [];
      recorder.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
      recorder.onstop = finish;
      recorder.start(1000);
      startedAt = Date.now(); elapsed = 0;
      timer = setInterval(tick, 250);
      $("rec-start").hidden = true; $("rec-pause").hidden = false; $("rec-stop").hidden = false; $("rec-review").hidden = true;
      status("録音を開始しました");
    } catch (e) {
      cleanup();
      const msg = e && e.name === "NotAllowedError"
        ? "マイクの使用が許可されていません。アドレスバー左の鍵マークから、マイクを「許可」にしてください。"
        : (e && e.message) || "録音を始められませんでした";
      toast(msg, "error");
    }
  }

  function pause() {
    if (!recorder) return;
    if (recorder.state === "recording") {
      recorder.pause(); elapsed += Date.now() - startedAt; $("rec-pause").textContent = "再開"; status("一時停止しました");
    } else if (recorder.state === "paused") {
      recorder.resume(); startedAt = Date.now(); $("rec-pause").textContent = "一時停止"; status("録音を再開しました");
    }
  }

  function stop() { if (recorder && recorder.state !== "inactive") { if (recorder.state === "recording") elapsed += Date.now() - startedAt; recorder.stop(); } }

  function finish() {
    clearInterval(timer); tick();
    recordedBlob = new Blob(chunks, { type: (mime || "audio/webm").split(";")[0] });
    cleanup();
    $("rec-preview").src = URL.createObjectURL(recordedBlob);
    $("rec-pause").hidden = true; $("rec-stop").hidden = true; $("rec-review").hidden = false;
    status(`録音を停止しました。長さ ${clock(elapsed)}`);
  }

  function cleanup() {
    streams.forEach((s) => s.getTracks().forEach((t) => t.stop()));
    streams = [];
    if (audioCtx) { audioCtx.close(); audioCtx = null; }
    $("meter").style.width = "0";
  }

  function warn(e) { if ((recorder && recorder.state !== "inactive") || recordedBlob) { e.preventDefault(); e.returnValue = ""; } }

  $("rec-start").addEventListener("click", start);
  $("rec-pause").addEventListener("click", pause);
  $("rec-stop").addEventListener("click", stop);
  $("rec-redo").addEventListener("click", () => {
    if (!confirm("いまの録音を消して録り直しますか？")) return;
    recordedBlob = null; recorder = null; $("rec-review").hidden = true; $("rec-start").hidden = false;
    $("rec-pause").textContent = "一時停止"; $("rec-time").textContent = "00:00";
  });
  $("rec-save").addEventListener("click", (e) => {
    if (!recordedBlob) return;
    const fd = baseForm("record");
    const ext = recordedBlob.type.includes("mp4") ? "m4a" : recordedBlob.type.includes("ogg") ? "ogg" : "webm";
    fd.append("audio", recordedBlob, `recording.${ext}`);
    fd.append("duration_sec", String(Math.round(elapsed / 1000)));
    send(fd, e.currentTarget);
  });
  window.addEventListener("beforeunload", warn);
})();
