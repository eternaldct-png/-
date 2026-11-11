// 新しい会議: 録音・ファイル・文字起こし
(function () {
  "use strict";
  const { api, toast, withLoading, toLocalInput, localInputToUTC } = window.MN;
  const $ = (id) => document.getElementById(id);

  $("started_at").value = toLocalInput(new Date());

  function metaFields() {
    const meta = new FormData($("meta"));
    return {
      title: meta.get("title") || "",
      started_at: localInputToUTC(meta.get("started_at")),
      participants: meta.get("participants") || "",
      tags: meta.get("tags") || "",
    };
  }
  function baseForm(source) {
    const fd = new FormData();
    fd.append("source", source);
    Object.entries(metaFields()).forEach(([k, v]) => fd.append(k, v));
    return fd;
  }
  function askNotify() {
    // 処理が終わったらデスクトップ通知を出せるように（不満: 失敗に会議の後で気づく）
    try { if ("Notification" in window && Notification.permission === "default") Notification.requestPermission(); } catch (e) {}
  }

  async function send(fd, btn) {
    askNotify();
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
  let recorder = null, chunks = [], streams = [], audioCtx = null, startedAt = 0, elapsed = 0, timer = null,
    recordedBlob = null, mime = "", rid = null, seq = 0, uploadChain = Promise.resolve(), uploadFailed = false,
    pendingParts = [], flushTimer = null, quietSince = 0;
  const status = (msg) => { $("rec-status").textContent = msg; };
  const consentValue = () => (document.querySelector('input[name="consent"]:checked') || {}).value || "";
  $("with-tab").addEventListener("change", () => { $("tab-help").hidden = !$("with-tab").checked; });

  // マイクの一覧（許可前は名前が出ないので、許可後にもう一度読む）
  async function listMics() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
    const sel = $("mic-select"), cur = sel.value;
    const devs = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput" && d.deviceId && d.deviceId !== "default");
    sel.querySelectorAll("option:not(:first-child)").forEach((o) => o.remove());
    devs.forEach((d, i) => sel.add(new Option(d.label || `マイク ${i + 1}`, d.deviceId)));
    sel.value = cur;
  }
  listMics();

  function pickMime() {
    const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
    return types.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || "";
  }
  const extOf = (m) => (m.includes("mp4") ? "m4a" : m.includes("ogg") ? "ogg" : "webm");
  function clock(ms) {
    const s = Math.floor(ms / 1000), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
    const p = (n) => String(n).padStart(2, "0");
    return h ? `${h}:${p(m)}:${p(r)}` : `${p(m)}:${p(r)}`;
  }
  const nowMs = () => elapsed + (recorder && recorder.state === "recording" ? Date.now() - startedAt : 0);
  function tick() { $("rec-time").textContent = clock(nowMs()); }

  // 10秒ごとに音声のかけらをPCへ保存（不満: 録音が消えた）。失敗しても手元には全部残し、保存時にまとめて送る。
  function flushParts() {
    if (!rid || !pendingParts.length) return uploadChain;
    const blob = new Blob(pendingParts, { type: (mime || "audio/webm").split(";")[0] });
    pendingParts = [];
    const n = seq++;
    uploadChain = uploadChain.then(async () => {
      if (uploadFailed) return;
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const res = await fetch(`/api/recordings/${rid}/chunk?seq=${n}`, { method: "POST", headers: { "X-Meeting-Notes": "1" }, body: blob });
          if (res.ok) { $("save-state").textContent = `PCに保存済み: ${clock(nowMs())} まで`; return; }
        } catch (e) { /* 少し待って送り直す */ }
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
      }
      uploadFailed = true;
      $("save-state").textContent = "⚠ 途中保存ができていません（アプリが止まっている？）。録音は続いています。停止後の「保存」でまとめて送ります。";
    });
    return uploadChain;
  }

  async function start() {
    if (!consentValue()) {
      toast("録音の前に「相手に伝えた」か「自分だけのメモ」を選んでください", "error");
      $("consent").querySelector("input").focus();
      return;
    }
    if (!navigator.mediaDevices || !window.MediaRecorder) { toast("このブラウザは録音に対応していません。Chrome か Edge を使ってください。", "error"); return; }
    try {
      const room = $("room-mode").checked;
      const constraints = { echoCancellation: !room, noiseSuppression: !room, autoGainControl: !room };
      if ($("mic-select").value) constraints.deviceId = { exact: $("mic-select").value };
      const mic = await navigator.mediaDevices.getUserMedia({ audio: constraints });
      listMics();
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
      quietSince = Date.now();
      (function meter() {
        if (!audioCtx) return;
        analyser.getByteTimeDomainData(buf);
        let peak = 0; for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
        $("meter").style.width = Math.min(100, (peak / 64) * 100) + "%";
        // 無音が続いたら知らせる（不満: 取れていないことに会議の後で気づく）
        if (recorder && recorder.state === "recording") {
          if (peak > 3) quietSince = Date.now();
          $("silence-warn").hidden = Date.now() - quietSince < 20000;
        }
        requestAnimationFrame(meter);
      })();
      mime = pickMime();
      // PC側の途中保存を始める（失敗しても録音はできる）
      rid = null; seq = 0; uploadFailed = false; pendingParts = []; uploadChain = Promise.resolve();
      try {
        const r = await api("POST", "/api/recordings", { ext: extOf(mime || "audio/webm"), consent: consentValue(), ...metaFields() });
        rid = r.id;
      } catch (e) {
        uploadFailed = true;
        $("save-state").textContent = "⚠ 途中保存を始められませんでした。録音は続けられます。";
      }
      recorder = new MediaRecorder(dest.stream, mime ? { mimeType: mime, audioBitsPerSecond: 64000 } : undefined);
      chunks = [];
      recorder.ondataavailable = (e) => { if (e.data && e.data.size) { chunks.push(e.data); pendingParts.push(e.data); } };
      recorder.onstop = finish;
      recorder.start(1000);
      flushTimer = setInterval(flushParts, 10000);
      startedAt = Date.now(); elapsed = 0;
      timer = setInterval(tick, 250);
      $("consent").disabled = true;
      $("rec-start").hidden = true; $("rec-pause").hidden = false; $("rec-stop").hidden = false; $("rec-review").hidden = true;
      status("録音を開始しました");
    } catch (e) {
      cleanup();
      const msg = e && e.name === "NotAllowedError"
        ? "マイクの使用が許可されていません。アドレスバー左の鍵マークから、マイクを「許可」にしてください。"
        : e && e.name === "OverconstrainedError" ? "選んだマイクが見つかりません。マイクの選択を「いつものマイク」に戻してください。"
        : (e && e.message) || "録音を始められませんでした";
      toast(msg, "error");
    }
  }

  function pause() {
    if (!recorder) return;
    if (recorder.state === "recording") {
      recorder.pause(); elapsed += Date.now() - startedAt; $("rec-pause").textContent = "再開"; status("一時停止しました");
      $("silence-warn").hidden = true;
    } else if (recorder.state === "paused") {
      recorder.resume(); startedAt = Date.now(); quietSince = Date.now(); $("rec-pause").textContent = "一時停止"; status("録音を再開しました");
    }
  }

  function stop() { if (recorder && recorder.state !== "inactive") { if (recorder.state === "recording") elapsed += Date.now() - startedAt; recorder.stop(); } }

  function finish() {
    clearInterval(timer); clearInterval(flushTimer); tick();
    flushParts();
    recordedBlob = new Blob(chunks, { type: (mime || "audio/webm").split(";")[0] });
    cleanup();
    $("silence-warn").hidden = true;
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
  $("rec-redo").addEventListener("click", async () => {
    if (!confirm("いまの録音を消して録り直しますか？")) return;
    await uploadChain;
    if (rid) { try { await api("DELETE", `/api/recordings/${rid}`); } catch (e) { /* もう無い */ } }
    rid = null; recordedBlob = null; recorder = null; $("rec-review").hidden = true; $("rec-start").hidden = false;
    $("consent").disabled = false; $("save-state").textContent = "";
    $("rec-pause").textContent = "一時停止"; $("rec-time").textContent = "00:00";
  });
  $("rec-save").addEventListener("click", (e) => {
    if (!recordedBlob) return;
    askNotify();
    withLoading(e.currentTarget, async () => {
      await uploadChain;
      let data;
      if (rid && !uploadFailed) {
        data = await api("POST", `/api/recordings/${rid}/finish`, { ...metaFields(), consent: consentValue(), duration_sec: String(Math.round(elapsed / 1000)) });
      } else {
        // 途中保存がうまくいかなかったときは、手元の録音をまとめて送る
        const fd = baseForm("record");
        fd.append("consent", consentValue());
        fd.append("audio", recordedBlob, `recording.${extOf(recordedBlob.type)}`);
        fd.append("duration_sec", String(Math.round(elapsed / 1000)));
        data = await api("POST", "/api/meetings", fd);
        if (rid) { try { await api("DELETE", `/api/recordings/${rid}`); } catch (err) { /* 残っていても復旧一覧に出るだけ */ } }
      }
      recordedBlob = null;
      location.href = data.url;
    });
  });
  window.addEventListener("beforeunload", warn);
})();
