// STAGE（案①）: 暗転したステージ + スポットライト + ライバー50人の光の球 + 音に反応するパーティクル
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { caps, hasWebGL, loader, initCommon, lerp, clamp } from './common.js';

initCommon();
const GENRE_COLOR = { '歌': 0xff7aa8, 'トーク': 0x6fd6ff, '弾き語り': 0xb48cff, 'ASMR': 0xffc46b, 'ゲーム': 0x7dffb0 };
const AUDIO_SRC = 'assets/audio/theme.mp3'; // ここに自社楽曲を置くと Sound demo がその曲になる

if (!hasWebGL()) { loader.done(); } else { boot(); }

async function boot() {
  const res = await fetch('data/livers.json').then(r => r.json()).catch(() => ({ livers: [] }));
  const livers = res.livers || [];
  document.getElementById('count').textContent = livers.length;

  const canvas = document.getElementById('gl');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: caps.quality > 0, powerPreference: 'high-performance' });
  renderer.setPixelRatio(caps.dpr);
  renderer.setSize(innerWidth, innerHeight, false);
  renderer.setClearColor(0x030303, 1);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  renderer.shadowMap.enabled = caps.quality === 2;

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x030303, 0.05);
  const camera = new THREE.PerspectiveCamera(42, innerWidth / innerHeight, 0.1, 100);
  camera.position.set(0, 3.2, 11);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true; controls.dampingFactor = 0.05;
  controls.enablePan = false; controls.minDistance = 5; controls.maxDistance = 16;
  controls.minPolarAngle = 0.6; controls.maxPolarAngle = 1.45;
  controls.autoRotate = !caps.reduced; controls.autoRotateSpeed = 0.5;
  controls.target.set(0, 1.2, 0);

  // ── stage floor（反射する黒い床） ──
  const floor = new THREE.Mesh(new THREE.CircleGeometry(9, 96), new THREE.MeshStandardMaterial({ color: 0x0a0a0a, metalness: 0.9, roughness: 0.35, envMapIntensity: 0.6 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const rim = new THREE.Mesh(new THREE.RingGeometry(8.9, 9.0, 128), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35, side: THREE.DoubleSide }));
  rim.rotation.x = -Math.PI / 2; rim.position.y = 0.005; scene.add(rim);
  // 床のグリッド線（うっすら）
  const grid = new THREE.PolarGridHelper(9, 16, 6, 96, 0x222222, 0x151515); grid.position.y = 0.003; scene.add(grid);

  // ── spotlights + 見えるライトの円錐 ──
  scene.add(new THREE.AmbientLight(0xffffff, 0.08));
  const spots = [];
  const coneMat = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(0xffffff) }, uPower: { value: 1 } },
    vertexShader: `varying vec2 vUv; varying vec3 vPos; void main(){ vUv = uv; vPos = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `uniform vec3 uColor; uniform float uPower; varying vec2 vUv; varying vec3 vPos;
      void main(){ float a = pow(vUv.y, 2.2) * 0.32 * uPower; gl_FragColor = vec4(uColor, a); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  });
  const colors = [0xffffff, 0xff7aa8, 0x6fd6ff];
  colors.forEach((c, i) => {
    const ang = (i / colors.length) * Math.PI * 2 + 0.6;
    const x = Math.cos(ang) * 4.5, z = Math.sin(ang) * 4.5;
    const light = new THREE.SpotLight(c, 260, 22, 0.42, 0.55, 1.6);
    light.position.set(x, 8.5, z); light.target.position.set(-x * 0.2, 0, -z * 0.2);
    light.castShadow = caps.quality === 2; scene.add(light); scene.add(light.target);
    const cone = new THREE.Mesh(new THREE.ConeGeometry(2.9, 8.5, 48, 1, true), coneMat.clone());
    cone.material.uniforms.uColor.value = new THREE.Color(c);
    cone.position.copy(light.position).add(light.target.position).multiplyScalar(0.5);
    cone.lookAt(light.target.position); cone.rotateX(-Math.PI / 2);
    scene.add(cone);
    spots.push({ light, cone, base: 260, phase: i * 2.1 });
  });

  // ── livers as glowing orbs ──
  const orbGroup = new THREE.Group(); scene.add(orbGroup);
  const orbGeo = new THREE.SphereGeometry(0.16, 24, 24);
  const haloGeo = new THREE.PlaneGeometry(1, 1);
  const haloTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
    const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c);
  })();
  const orbs = livers.map((lv, i) => {
    const col = new THREE.Color(GENRE_COLOR[lv.genre] || 0xffffff);
    const mat = new THREE.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 1.6, roughness: 0.3, metalness: 0.2 });
    const m = new THREE.Mesh(orbGeo, mat);
    // 2重の螺旋リングに配置
    const ringIdx = i % 2, n = livers.length;
    const ang = (i / n) * Math.PI * 2 * 2 + ringIdx * 0.5;
    const r = 3.0 + ringIdx * 1.9 + (i % 3) * 0.25;
    const y = 0.9 + (i % 5) * 0.55 + ringIdx * 0.3;
    m.position.set(Math.cos(ang) * r, y, Math.sin(ang) * r);
    m.userData = { liver: lv, baseY: y, phase: i * 0.7, col };
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, color: col, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }));
    halo.scale.setScalar(1.1); m.add(halo); m.userData.halo = halo;
    orbGroup.add(m);
    return m;
  });

  // ── particles（音に反応） ──
  const pN = caps.quality === 2 ? 3000 : caps.quality === 1 ? 1400 : 600;
  const pp = new Float32Array(pN * 3), pv = new Float32Array(pN);
  for (let i = 0; i < pN; i++) {
    const r = Math.sqrt(Math.random()) * 8.5, a = Math.random() * Math.PI * 2;
    pp[i * 3] = Math.cos(a) * r; pp[i * 3 + 1] = Math.random() * 7; pp[i * 3 + 2] = Math.sin(a) * r; pv[i] = 0.2 + Math.random() * 0.8;
  }
  const pGeo = new THREE.BufferGeometry(); pGeo.setAttribute('position', new THREE.BufferAttribute(pp, 3));
  const pMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.035, map: haloTex, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false });
  const particles = new THREE.Points(pGeo, pMat); scene.add(particles);

  // ── audio (WebAudio)：ファイルがあればそれを、なければ合成音のデモループ ──
  const audio = { ctx: null, analyser: null, data: null, on: false, level: 0, nodes: [] };
  const soundBtn = document.getElementById('soundBtn'), soundLabel = document.getElementById('soundLabel');
  async function toggleSound() {
    if (!audio.ctx) {
      audio.ctx = new (window.AudioContext || window.webkitAudioContext)();
      audio.analyser = audio.ctx.createAnalyser(); audio.analyser.fftSize = 256; audio.analyser.smoothingTimeConstant = 0.85;
      audio.data = new Uint8Array(audio.analyser.frequencyBinCount);
      const master = audio.ctx.createGain(); master.gain.value = 0.5; master.connect(audio.analyser); audio.analyser.connect(audio.ctx.destination);
      audio.master = master;
      const ok = await fetch(AUDIO_SRC, { method: 'HEAD' }).then(r => r.ok).catch(() => false);
      if (ok) {
        const el = new Audio(AUDIO_SRC); el.loop = true; el.crossOrigin = 'anonymous';
        audio.ctx.createMediaElementSource(el).connect(master); audio.el = el;
      } else {
        synthLoop(audio.ctx, master); // 権利フリーの生成音
      }
    }
    audio.on = !audio.on;
    if (audio.on) { await audio.ctx.resume(); audio.el && audio.el.play(); }
    else { audio.el ? audio.el.pause() : await audio.ctx.suspend(); }
    soundBtn.classList.toggle('on', audio.on);
    soundLabel.textContent = audio.on ? 'Sound on' : 'Sound demo';
  }
  soundBtn.addEventListener('click', toggleSound);
  function synthLoop(ctx, out) {
    // 4 和音のアルペジオ + キック。楽曲データを持たない状態でも「音に反応する」体験を確認できる
    const chords = [[220, 277.2, 329.6, 415.3], [174.6, 220, 261.6, 329.6], [196, 246.9, 293.7, 349.2], [164.8, 207.7, 246.9, 311.1]];
    const bpm = 96, beat = 60 / bpm; let step = 0;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1800; lp.connect(out);
    function tick() {
      if (!audio.on) { setTimeout(tick, 200); return; }
      const t = ctx.currentTime + 0.05;
      const chord = chords[Math.floor(step / 8) % chords.length];
      const f = chord[step % chord.length] * (step % 8 >= 4 ? 2 : 1);
      const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.value = f;
      const g = ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.35, t + 0.02); g.gain.exponentialRampToValueAtTime(0.001, t + beat * 0.9);
      o.connect(g); g.connect(lp); o.start(t); o.stop(t + beat);
      if (step % 4 === 0) { // kick
        const k = ctx.createOscillator(); const kg = ctx.createGain();
        k.frequency.setValueAtTime(140, t); k.frequency.exponentialRampToValueAtTime(40, t + 0.25);
        kg.gain.setValueAtTime(0.9, t); kg.gain.exponentialRampToValueAtTime(0.001, t + 0.3);
        k.connect(kg); kg.connect(out); k.start(t); k.stop(t + 0.32);
      }
      step++; setTimeout(tick, beat * 500);
    }
    tick();
  }
  document.getElementById('autoBtn').addEventListener('click', e => { controls.autoRotate = !controls.autoRotate; e.currentTarget.classList.toggle('on', controls.autoRotate); });
  document.getElementById('autoBtn').classList.toggle('on', controls.autoRotate);

  // ── hover / click ──
  const ray = new THREE.Raycaster(); ray.params.Points.threshold = 0;
  const ptr = new THREE.Vector2(-9, -9); let hovered = null;
  const tip = document.getElementById('tip'), tipName = document.getElementById('tipName');
  addEventListener('pointermove', e => { ptr.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1); tip.style.left = e.clientX + 'px'; tip.style.top = e.clientY + 'px'; }, { passive: true });
  canvas.addEventListener('click', () => { if (hovered && hovered.userData.liver.url && hovered.userData.liver.url !== '#') window.open(hovered.userData.liver.url, '_blank', 'noopener'); });
  canvas.addEventListener('pointerdown', e => { if (caps.coarse) ptr.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1); });

  function resize() { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
  addEventListener('resize', resize);

  const clock = new THREE.Clock(); let time = 0, running = true;
  document.addEventListener('visibilitychange', () => { running = !document.hidden; if (running) loop(); });
  function loop() {
    if (!running) return;
    requestAnimationFrame(loop);
    const dt = Math.min(clock.getDelta(), 0.05);
    if (!caps.reduced) time += dt;

    // audio level
    let level = 0;
    if (audio.on && audio.analyser) {
      audio.analyser.getByteFrequencyData(audio.data);
      let s = 0; for (let i = 2; i < 40; i++) s += audio.data[i]; level = s / (38 * 255);
    }
    audio.level = lerp(audio.level, level, 0.2);
    const L = audio.level;

    // hover
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObjects(orbs, false)[0];
    const h = hit ? hit.object : null;
    if (h !== hovered) {
      hovered = h; tip.classList.toggle('on', !!h);
      if (h) tipName.textContent = `${h.userData.liver.name} — ${h.userData.liver.genre}`;
      canvas.style.cursor = h ? 'pointer' : '';
    }

    orbs.forEach((m, i) => {
      const u = m.userData;
      m.position.y = u.baseY + Math.sin(time * 0.8 + u.phase) * 0.18 + L * 0.5;
      const s = (m === hovered ? 1.8 : 1) + L * 1.2;
      m.scale.setScalar(lerp(m.scale.x, s, 0.15));
      u.halo.material.opacity = 0.45 + L * 0.5 + (m === hovered ? 0.4 : 0);
      m.material.emissiveIntensity = 1.3 + L * 2.5 + (m === hovered ? 1.5 : 0);
    });
    orbGroup.rotation.y = time * 0.03;
    particles.rotation.y = -time * 0.02;
    pMat.size = 0.035 + L * 0.08;
    pMat.opacity = 0.55 + L * 0.45;
    spots.forEach((s, i) => {
      const pulse = 0.75 + 0.25 * Math.sin(time * 0.9 + s.phase) + L * 1.2;
      s.light.intensity = s.base * pulse;
      s.cone.material.uniforms.uPower.value = pulse;
      s.light.position.x = Math.cos(time * 0.15 + s.phase) * 4.5; s.light.position.z = Math.sin(time * 0.15 + s.phase) * 4.5;
      s.cone.position.copy(s.light.position).add(s.light.target.position).multiplyScalar(0.5);
      s.cone.lookAt(s.light.target.position); s.cone.rotateX(-Math.PI / 2);
    });
    controls.update();
    renderer.render(scene, camera);
  }
  resize(); loop(); loader.done();
}
