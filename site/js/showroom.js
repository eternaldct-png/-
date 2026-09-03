// SHOWROOM（案③）: 商品を3Dで回す。GLBがあれば読み込み、なければ簡易モデルを生成する
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { caps, hasWebGL, loader, initCommon, lerp } from './common.js';

initCommon();

// カラー名 → 実際の色。新しいカラーを増やしたらここに追加
const COLOR_MAP = { 'チャコール': 0x3a3a3c, 'ホワイト': 0xf4f4f2, '黒': 0x141414, 'ブラック': 0x141414, 'ネイビー': 0x1c2540 };
const PRINT_COLOR = { 'チャコール': '#f2f2f2', 'ホワイト': '#151515', '黒': '#f2f2f2', 'ブラック': '#f2f2f2', 'ネイビー': '#f2f2f2' };

if (!hasWebGL()) { loader.done(); } else { boot(); }

async function boot() {
  const data = await fetch('data/products.json').then(r => r.json());
  const products = data.products;

  const canvas = document.getElementById('gl');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(caps.dpr);
  renderer.setSize(innerWidth, innerHeight, false);
  renderer.setClearColor(0x050505, 1);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, innerWidth / innerHeight, 0.1, 50);
  camera.position.set(0.6, 1.2, 6);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true; controls.enablePan = false;
  controls.minDistance = 3; controls.maxDistance = 9; controls.maxPolarAngle = 1.6;
  controls.autoRotate = !caps.reduced; controls.autoRotateSpeed = 1.2;
  controls.target.set(0, 0.9, 0);

  // studio lights
  scene.add(new THREE.AmbientLight(0xffffff, 0.25));
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(3, 6, 4); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 6; key.shadow.camera.left = key.shadow.camera.bottom = -3; key.shadow.camera.right = key.shadow.camera.top = 3;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.6); fill.position.set(-4, 2, -2); scene.add(fill);
  // floor: 影だけ受ける
  const floor = new THREE.Mesh(new THREE.CircleGeometry(6, 64), new THREE.ShadowMaterial({ opacity: 0.45 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const ring = new THREE.Mesh(new THREE.RingGeometry(2.2, 2.215, 128), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.25, side: THREE.DoubleSide }));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.002; scene.add(ring);

  const holder = new THREE.Group(); scene.add(holder);
  const gltf = new GLTFLoader();

  // ── プリント（chaco ロゴの仮テクスチャ。ロゴ画像が来たら assets/img/print.png 等に差し替え） ──
  function printTexture(color, small) {
    const c = document.createElement('canvas'); c.width = 1024; c.height = 1024; const g = c.getContext('2d');
    g.clearRect(0, 0, 1024, 1024);
    g.fillStyle = color; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = `200 ${small ? 120 : 300}px Inter, Helvetica, Arial, sans-serif`;
    g.fillText('chaco', 512, small ? 480 : 470);
    g.font = `400 ${small ? 28 : 44}px Inter, Helvetica, Arial, sans-serif`;
    g.letterSpacing = '0.4em';
    g.fillText('ETERNAL d.c.t', 512 + (small ? 8 : 12), small ? 570 : 690);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
  }

  // ── 簡易Tシャツ（輪郭を押し出し） ──
  function tshirtMesh(color) {
    const s = new THREE.Shape();
    s.moveTo(-0.55, 1.65); s.lineTo(-0.2, 1.78); s.quadraticCurveTo(0, 1.62, 0.2, 1.78); s.lineTo(0.55, 1.65);
    s.lineTo(1.05, 1.35); s.lineTo(0.85, 0.95); s.lineTo(0.6, 1.05); s.lineTo(0.62, 0.05); s.lineTo(-0.62, 0.05);
    s.lineTo(-0.6, 1.05); s.lineTo(-0.85, 0.95); s.lineTo(-1.05, 1.35); s.closePath();
    const geo = new THREE.ExtrudeGeometry(s, { depth: 0.22, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.06, bevelSegments: 6, curveSegments: 12 });
    geo.center(); geo.translate(0, 0.95, 0);
    const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.92, metalness: 0 });
    const m = new THREE.Mesh(geo, mat); m.castShadow = true;
    const g = new THREE.Group(); g.add(m);
    const print = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshStandardMaterial({ transparent: true, roughness: 0.9, polygonOffset: true, polygonOffsetFactor: -2 }));
    print.position.set(0, 0.95, 0.19 + 0.06); g.add(print);
    g.userData = { body: m, print, kind: 'tshirt' };
    return g;
  }
  // ── 簡易マグ（筒 + 取っ手） ──
  function mugMesh(color) {
    const g = new THREE.Group();
    const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.25, metalness: 0 });
    const outer = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.56, 1.5, 64, 1, true), mat); outer.position.y = 0.75; outer.castShadow = true; outer.material.side = THREE.DoubleSide;
    const bottom = new THREE.Mesh(new THREE.CircleGeometry(0.56, 64), mat); bottom.rotation.x = -Math.PI / 2; bottom.position.y = 0.02;
    const lip = new THREE.Mesh(new THREE.TorusGeometry(0.61, 0.025, 12, 64), mat); lip.rotation.x = Math.PI / 2; lip.position.y = 1.5;
    const inner = new THREE.Mesh(new THREE.CircleGeometry(0.56, 64), new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.4 })); inner.rotation.x = -Math.PI / 2; inner.position.y = 0.15;
    const handle = new THREE.Mesh(new THREE.TorusGeometry(0.36, 0.07, 16, 48, Math.PI), mat); handle.position.set(0.6, 0.78, 0); handle.rotation.z = -Math.PI / 2; handle.castShadow = true;
    g.add(outer, bottom, lip, inner, handle);
    // 側面に巻き付くプリント
    const print = new THREE.Mesh(new THREE.CylinderGeometry(0.625, 0.57, 1.0, 64, 1, true, Math.PI * 0.95, Math.PI * 1.1),
      new THREE.MeshStandardMaterial({ transparent: true, roughness: 0.3, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2 }));
    print.position.y = 0.8; print.rotation.y = Math.PI * 0.55; g.add(print);
    g.userData = { body: outer, print, kind: 'mug', parts: [outer, bottom, lip, handle] };
    return g;
  }

  // ── state ──
  const ui = { name: document.getElementById('pName'), price: document.getElementById('pPrice'), desc: document.getElementById('pDesc'), opts: document.getElementById('opts'), buy: document.getElementById('buy'), list: document.getElementById('products'), photo: document.getElementById('photo'), photoImg: document.getElementById('photoImg') };
  let product = null, sel = {}, model = null, fadeIn = 0;

  function currentPrice() {
    if (product.price) return product.price;
    const sizes = product.variants?.size || [];
    const hit = sizes.find(s => s.label === sel.size) || sizes[0];
    return hit ? hit.price : null;
  }
  function updatePanel() {
    ui.name.textContent = product.name;
    const p = currentPrice(); ui.price.textContent = p ? `¥${p.toLocaleString()}` : '—';
    ui.desc.textContent = product.description || '';
    ui.buy.href = `https://kazuto-post-generator.onrender.com/goods#${product.id}`;
    const img = (product.images || []).find(i => (!i.color || i.color === sel.color) && (!i.design || i.design === sel.design)) || (product.images || [])[0];
    ui.photo.hidden = !img; if (img) ui.photoImg.src = img.path;
  }
  function applyLook() {
    if (!model) return;
    const col = COLOR_MAP[sel.color] ?? (product.kind === 'mug' ? 0xf4f4f2 : 0x3a3a3c);
    const pc = PRINT_COLOR[sel.color] ?? (product.kind === 'mug' ? '#151515' : '#f2f2f2');
    const small = sel.design === 'スモール';
    const u = model.userData;
    if (u.body) (u.parts || [u.body]).forEach(m => m.material.color.set(col));
    if (u.print) {
      u.print.material.map = printTexture(pc, small); u.print.material.needsUpdate = true;
      if (u.kind === 'tshirt') { u.print.scale.setScalar(small ? 0.42 : 1.0); u.print.position.x = small ? -0.3 : 0; u.print.position.y = small ? 1.28 : 0.95; }
    }
  }
  function buildOpts() {
    ui.opts.innerHTML = '';
    const v = product.variants || {};
    const labels = { size: 'Size', color: 'Color', design: 'Design' };
    for (const key of ['color', 'design', 'size']) {
      if (!v[key]) continue;
      const wrap = document.createElement('div'); wrap.className = 'opt';
      wrap.innerHTML = `<div class="lbl">${labels[key]}</div><div class="vals"></div>`;
      const vals = wrap.querySelector('.vals');
      v[key].forEach(o => {
        const b = document.createElement('button');
        if (key === 'color') { b.className = 'sw'; b.title = o.label; b.style.background = '#' + (COLOR_MAP[o.label] ?? 0x888888).toString(16).padStart(6, '0'); }
        else b.textContent = o.label;
        b.classList.toggle('on', sel[key] === o.label);
        b.addEventListener('click', () => { sel[key] = o.label; buildOpts(); updatePanel(); applyLook(); });
        vals.appendChild(b);
      });
      ui.opts.appendChild(wrap);
    }
  }
  async function loadModel() {
    if (model) { holder.remove(model); model = null; }
    let m = null;
    try {
      const ok = await fetch(product.model, { method: 'HEAD' }).then(r => r.ok && /model|octet|gltf/.test(r.headers.get('content-type') || 'octet')).catch(() => false);
      if (ok) {
        const g = await gltf.loadAsync(product.model);
        m = g.scene; m.traverse(o => { if (o.isMesh) { o.castShadow = true; } });
        const box = new THREE.Box3().setFromObject(m); const size = box.getSize(new THREE.Vector3()); const s = 1.8 / Math.max(size.x, size.y, size.z);
        m.scale.setScalar(s); box.setFromObject(m); m.position.y -= box.min.y; m.position.x -= (box.min.x + box.max.x) / 2; m.position.z -= (box.min.z + box.max.z) / 2;
        m.userData = { kind: product.kind, glb: true };
      }
    } catch (e) { m = null; }
    if (!m) m = product.kind === 'mug' ? mugMesh(0xf4f4f2) : tshirtMesh(0x3a3a3c);
    model = m; holder.add(m); fadeIn = 0; applyLook();
  }
  function select(p) {
    product = p;
    sel = {};
    for (const k of ['size', 'color', 'design']) if (p.variants?.[k]?.length) sel[k] = p.variants[k][0].label;
    [...ui.list.children].forEach(b => b.classList.toggle('on', b.dataset.id === p.id));
    buildOpts(); updatePanel(); loadModel();
  }
  products.forEach(p => {
    const b = document.createElement('button'); b.className = 'pill'; b.dataset.id = p.id; b.textContent = p.name;
    b.addEventListener('click', () => select(p)); ui.list.appendChild(b);
  });
  const hash = location.hash.replace('#', '');
  select(products.find(p => p.id === hash) || products[0]);

  function resize() { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
  addEventListener('resize', resize);
  const clock = new THREE.Clock(); let running = true;
  document.addEventListener('visibilitychange', () => { running = !document.hidden; if (running) loop(); });
  function loop() {
    if (!running) return;
    requestAnimationFrame(loop);
    const dt = Math.min(clock.getDelta(), 0.05);
    if (model) { fadeIn = Math.min(1, fadeIn + dt * 1.6); const e = 1 - Math.pow(1 - fadeIn, 3); model.scale.setScalar((model.userData.glb ? model.scale.x : 1) * (model.userData.glb ? 1 : e)); model.position.y = model.userData.glb ? model.position.y : (1 - e) * 0.4; }
    controls.update();
    renderer.render(scene, camera);
  }
  resize(); loop(); loader.done();
}
