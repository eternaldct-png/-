// TOP（案②）: 黒背景に浮かぶガラス状オブジェクト。スクロールで事業ごとに形と色が変わる。
// 画像カードは WebGL 面に貼ってホバーで歪ませる（2D+3D の混在）
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { caps, hasWebGL, loader, initCommon, placeholderCanvas, lerp, clamp } from './common.js';
import { noise3 } from './noise.js';

initCommon();

// ── セクションごとの見た目（ここを触ると各事業の"表情"が変わる） ──
//   amp: 表面の揺らぎの強さ / freq: 揺らぎの細かさ / speed: 動く速さ
//   scale: 大きさ / x,y: 位置 / tint: 差し色（点光源の色） / ring: リングの傾き / rough: 表面の曇り
const STATES = [
  { amp: 0.16, freq: 1.1, speed: 0.30, scale: 1.00, x:  1.9, y:  0.1, tint: 0xffffff, ring: 1.10, rough: 0.04 }, // 00 hero
  { amp: 0.42, freq: 1.9, speed: 0.55, scale: 0.62, x:  3.3, y:  1.25, tint: 0xff7aa8, ring: 0.60, rough: 0.05 }, // 01 liver
  { amp: 0.10, freq: 3.2, speed: 0.20, scale: 0.62, x: -3.3, y:  1.25, tint: 0x6fd6ff, ring: 1.35, rough: 0.02 }, // 02 ai
  { amp: 0.30, freq: 1.3, speed: 0.90, scale: 0.62, x:  3.3, y:  1.25, tint: 0xb48cff, ring: 0.95, rough: 0.08 }, // 03 music
  { amp: 0.06, freq: 2.4, speed: 0.15, scale: 0.58, x: -3.3, y:  1.25, tint: 0xffc46b, ring: 1.60, rough: 0.12 }, // 04 goods
  { amp: 0.22, freq: 1.0, speed: 0.35, scale: 1.05, x:  2.1, y:  0.0, tint: 0xffffff, ring: 1.10, rough: 0.03 }, // 05 contact
];

if (!hasWebGL()) {
  document.querySelectorAll('.gl-img').forEach(el => el.classList.add('fallback'));
  loader.done();
} else {
  boot();
}

function boot() {
  const canvas = document.getElementById('gl');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: caps.quality > 0, alpha: false, powerPreference: 'high-performance' });
  renderer.setPixelRatio(caps.dpr);
  renderer.setSize(innerWidth, innerHeight, false);
  renderer.setClearColor(0x050505, 1);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x050505, 0.045);
  const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 100);
  camera.position.set(0, 0, 7.5);

  // 反射用の環境（HDRIファイル不要の内蔵スタジオ）
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  // ── lights ──
  scene.add(new THREE.AmbientLight(0xffffff, 0.15));
  const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(3, 4, 5); scene.add(key);
  const rim = new THREE.DirectionalLight(0xffffff, 0.8); rim.position.set(-4, -2, -3); scene.add(rim);
  const tintLight = new THREE.PointLight(0xffffff, 40, 20, 2); tintLight.position.set(-3, -2.5, 3); scene.add(tintLight);

  // ── glass core ──
  const detail = caps.quality === 2 ? 5 : caps.quality === 1 ? 4 : 3;
  const geo = mergeVertices(new THREE.IcosahedronGeometry(1.45, detail)); // 頂点を共有させて滑らかな法線にする
  const base = geo.attributes.position.array.slice();
  const pos = geo.attributes.position;
  const glassMat = caps.quality >= 1
    ? new THREE.MeshPhysicalMaterial({
        color: 0xffffff, metalness: 0, roughness: 0.04, transmission: 1, thickness: 1.6, ior: 1.45,
        clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 1.4, attenuationColor: new THREE.Color(0xdde4ff), attenuationDistance: 2.5,
      })
    : new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 1, roughness: 0.12, envMapIntensity: 1.2 });
  const core = new THREE.Mesh(geo, glassMat);
  const group = new THREE.Group();
  group.add(core);
  scene.add(group);

  // ring + satellites（ロゴの3Dデータが来たら core をロゴ形状に差し替える想定）
  const ring = new THREE.Mesh(new THREE.TorusGeometry(2.35, 0.018, 12, 220), new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 1, roughness: 0.25 }));
  group.add(ring);
  const satMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 1, roughness: 0.15 });
  const sats = [0, 1, 2].map(i => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.07 + i * 0.02, 24, 24), satMat); group.add(m); return m; });

  // ── stars ──
  const starN = caps.quality === 2 ? 1800 : caps.quality === 1 ? 900 : 400;
  const sp = new Float32Array(starN * 3);
  for (let i = 0; i < starN; i++) {
    const r = 8 + Math.random() * 26, th = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
    sp[i * 3] = r * Math.sin(ph) * Math.cos(th); sp[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th); sp[i * 3 + 2] = r * Math.cos(ph) - 6;
  }
  const starGeo = new THREE.BufferGeometry(); starGeo.setAttribute('position', new THREE.BufferAttribute(sp, 3));
  const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.035, transparent: true, opacity: 0.55, sizeAttenuation: true, depthWrite: false }));
  scene.add(stars);

  // ── 2D+3D: hover-distortion image planes ──
  const ortho = new THREE.OrthographicCamera(-innerWidth / 2, innerWidth / 2, innerHeight / 2, -innerHeight / 2, -10, 10);
  const uiScene = new THREE.Scene();
  const manager = new THREE.LoadingManager();
  const texLoader = new THREE.TextureLoader(manager);
  const planeGeo = new THREE.PlaneGeometry(1, 1, 1, 1);
  const cards = [];
  const cardEls = [...document.querySelectorAll('.gl-img')];
  cardEls.forEach((el, i) => {
    let tex;
    if (el.dataset.src) {
      tex = texLoader.load(el.dataset.src);
    } else {
      const [label, sub] = (el.dataset.placeholder || 'ETERNAL|').split('|');
      tex = new THREE.CanvasTexture(placeholderCanvas(label, sub, 1024, 1280, Number(el.dataset.seed || i + 1)));
    }
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.minFilter = THREE.LinearFilter; tex.generateMipmaps = false;
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        uTex: { value: tex }, uHover: { value: 0 }, uMouse: { value: new THREE.Vector2(0.5, 0.5) },
        uTime: { value: 0 }, uRatio: { value: new THREE.Vector2(1, 1) }, uReveal: { value: 0 },
      },
      vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `
        uniform sampler2D uTex; uniform float uHover, uTime, uReveal; uniform vec2 uMouse, uRatio;
        varying vec2 vUv;
        void main(){
          vec2 uv = (vUv - 0.5) * uRatio + 0.5;               // cover fit
          uv = (uv - 0.5) * (1.0 - 0.06 * uHover) + 0.5;       // hover zoom
          vec2 d = uv - uMouse; float dist = length(d);
          float bulge = smoothstep(0.55, 0.0, dist) * uHover;
          uv -= normalize(d + 1e-5) * bulge * 0.09;            // マウス方向に引き寄せ
          float wave = sin(uv.y * 14.0 + uTime * 1.6) * 0.004 + sin(uv.x * 9.0 - uTime) * 0.003;
          uv.x += wave * (1.0 + 4.0 * uHover);
          float split = 0.012 * uHover;
          float r = texture2D(uTex, uv + vec2(split, 0.0)).r;
          float g = texture2D(uTex, uv).g;
          float b = texture2D(uTex, uv - vec2(split, 0.0)).b;
          vec3 col = vec3(r, g, b);
          col = mix(vec3(dot(col, vec3(0.299, 0.587, 0.114))), col, 0.35 + 0.65 * uHover); // 通常はほぼモノクロ、ホバーで色が戻る
          float edge = smoothstep(0.0, 0.08, vUv.x) * smoothstep(0.0, 0.08, 1.0 - vUv.x);
          float rev = smoothstep(vUv.y - 0.15, vUv.y + 0.15, uReveal * 1.3);
          gl_FragColor = vec4(col * (0.85 + 0.15 * uHover), rev);
        }`,
      transparent: true, depthTest: false,
    });
    const mesh = new THREE.Mesh(planeGeo, mat);
    uiScene.add(mesh);
    const card = { el, mesh, mat, hover: 0, reveal: 0, imgW: 1024, imgH: 1280 };
    if (tex.image && tex.image.width) { card.imgW = tex.image.width; card.imgH = tex.image.height; }
    else tex.addEventListener?.('update', () => {});
    el.addEventListener('pointerenter', () => card.target = 1);
    el.addEventListener('pointerleave', () => card.target = 0);
    el.addEventListener('pointermove', e => {
      const r = el.getBoundingClientRect();
      mat.uniforms.uMouse.value.set((e.clientX - r.left) / r.width, 1 - (e.clientY - r.top) / r.height);
    });
    card.target = 0;
    cards.push(card);
  });

  // ── scroll → state ──
  const sectionEls = [...document.querySelectorAll('.section[data-state]')];
  const cur = { amp: 0.16, freq: 1.1, speed: 0.3, scale: 0.0001, x: 0, y: 0, ring: 1.1, rough: 0.04 };
  const curTint = new THREE.Color(0xffffff);
  const targetTint = new THREE.Color(0xffffff);
  const target = { ...STATES[0] };
  let scrollY = window.scrollY;
  addEventListener('scroll', () => { scrollY = window.scrollY; }, { passive: true });

  function updateTarget() {
    const mid = scrollY + innerHeight * 0.5;
    let idx = 0, t = 0;
    for (let i = 0; i < sectionEls.length; i++) {
      const el = sectionEls[i];
      const top = el.offsetTop, h = el.offsetHeight;
      if (mid >= top + h) { idx = i; t = 1; continue; }
      if (mid >= top) {
        idx = i; const local = (mid - top) / h;
        t = clamp((local - 0.5) / 0.5, 0, 1); // 後半で次の状態へ滑らかに遷移
        break;
      }
    }
    const a = STATES[Math.min(idx, STATES.length - 1)], b = STATES[Math.min(idx + 1, STATES.length - 1)];
    const s = t * t * (3 - 2 * t);
    for (const k of ['amp', 'freq', 'speed', 'scale', 'x', 'y', 'ring', 'rough']) target[k] = lerp(a[k], b[k], s);
    targetTint.set(a.tint).lerp(new THREE.Color(b.tint), s);
    const halfW = 7.5 * Math.tan(THREE.MathUtils.degToRad(19)) * (innerWidth / innerHeight); // z=0 での可視半幅
    target.x = target.x * clamp(halfW / 4.1, 0.6, 1.1);
    if (caps.mobile || innerWidth < 900) { const big = idx === 0 || idx >= 5; target.x = 0; target.y = big ? 2.0 : 1.9; target.scale *= big ? 0.45 : 0.42; }
  }

  // ── pointer parallax ──
  const mouse = new THREE.Vector2(0, 0), mouseT = new THREE.Vector2(0, 0);
  addEventListener('pointermove', e => { mouseT.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1); }, { passive: true });

  // ── resize ──
  function resize() {
    renderer.setSize(innerWidth, innerHeight, false);
    camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    ortho.left = -innerWidth / 2; ortho.right = innerWidth / 2; ortho.top = innerHeight / 2; ortho.bottom = -innerHeight / 2; ortho.updateProjectionMatrix();
  }
  addEventListener('resize', resize);

  // ── surface displacement (CPU, noise) ──
  const tmp = new THREE.Vector3();
  function deform(time) {
    const f = cur.freq, a = cur.amp, t = time * cur.speed;
    for (let i = 0; i < pos.count; i++) {
      tmp.set(base[i * 3], base[i * 3 + 1], base[i * 3 + 2]);
      const n1 = noise3(tmp.x * f + t, tmp.y * f + t * 0.7, tmp.z * f - t * 0.4);
      const n2 = noise3(tmp.x * f * 3.1 - t * 0.6, tmp.y * f * 3.1 + t, tmp.z * f * 3.1) * 0.25;
      const d = 1 + (n1 + n2) * a;
      pos.setXYZ(i, tmp.x * d, tmp.y * d, tmp.z * d);
    }
    pos.needsUpdate = true;
    geo.computeVertexNormals();
  }

  // ── loop ──
  const clock = new THREE.Clock();
  let running = true, time = 0, lastDeform = -1;
  document.addEventListener('visibilitychange', () => { running = !document.hidden; if (running) loop(); });

  function loop() {
    if (!running) return;
    requestAnimationFrame(loop);
    const dt = Math.min(clock.getDelta(), 0.1);
    if (!caps.reduced) time += dt;
    updateTarget();

    const k = 1 - Math.pow(0.001, dt); // フレームレート非依存の追従
    for (const key of ['amp', 'freq', 'speed', 'scale', 'x', 'y', 'ring', 'rough']) cur[key] = lerp(cur[key], target[key], k * 0.55);
    curTint.lerp(targetTint, k * 0.5);
    tintLight.color.copy(curTint);
    if (glassMat.roughness !== undefined) glassMat.roughness = cur.rough;

    mouse.lerp(mouseT, k * 0.6);
    group.position.set(cur.x + mouse.x * 0.15, cur.y + mouse.y * 0.1, 0);
    group.scale.setScalar(cur.scale);
    core.rotation.y = time * 0.12 + mouse.x * 0.35;
    core.rotation.x = Math.sin(time * 0.2) * 0.2 + mouse.y * 0.25;
    ring.rotation.x = cur.ring + Math.sin(time * 0.3) * 0.08;
    ring.rotation.z = time * 0.08;
    sats.forEach((m, i) => {
      const ang = time * (0.35 + i * 0.12) + i * 2.1;
      m.position.set(Math.cos(ang) * 2.35, Math.sin(ang * 0.8) * 0.4, Math.sin(ang) * 2.35);
      m.position.applyAxisAngle(new THREE.Vector3(1, 0, 0), cur.ring);
    });
    stars.rotation.y = time * 0.012 + mouse.x * 0.03;
    stars.rotation.x = mouse.y * 0.02;
    camera.position.x = mouse.x * 0.25; camera.position.y = mouse.y * 0.18;
    camera.lookAt(0, 0, 0);

    // 変形は重いので、動きが止まっている（reduced motion）なら一度だけ
    if (!caps.reduced || lastDeform < 0 || Math.abs(cur.amp - lastDeform) > 0.005) { deform(time); lastDeform = cur.amp; }

    renderer.autoClear = true;
    renderer.render(scene, camera);

    // overlay planes
    renderer.autoClear = false; renderer.clearDepth();
    for (const c of cards) {
      const r = c.el.getBoundingClientRect();
      const visible = r.bottom > 0 && r.top < innerHeight;
      c.mesh.visible = visible;
      if (!visible) continue;
      c.mesh.position.set(r.left + r.width / 2 - innerWidth / 2, -(r.top + r.height / 2) + innerHeight / 2, 0);
      c.mesh.scale.set(r.width, r.height, 1);
      c.hover = lerp(c.hover, c.target, k * 0.7);
      c.reveal = lerp(c.reveal, c.el.classList.contains('in') ? 1 : 0, k * 0.35);
      const img = c.mat.uniforms.uTex.value.image;
      const iw = img && img.width || 1024, ih = img && img.height || 1280;
      const pa = r.width / r.height, ia = iw / ih;
      c.mat.uniforms.uRatio.value.set(pa > ia ? 1 : pa / ia, pa > ia ? ia / pa : 1);
      c.mat.uniforms.uHover.value = c.hover;
      c.mat.uniforms.uReveal.value = c.reveal;
      c.mat.uniforms.uTime.value = time;
    }
    renderer.render(uiScene, ortho);
  }

  // ── start ──
  let progress = 0;
  manager.onProgress = (u, l, tot) => { progress = l / tot; loader.set(0.3 + progress * 0.6); };
  loader.set(0.3);
  let started = false;
  const start = () => { if (started) return; started = true; resize(); loop(); loader.done(); };
  if (cardEls.some(el => el.dataset.src)) { manager.onLoad = start; setTimeout(start, 4000); }
  else start();
}
