'use strict';
/* ================================================================
   アマテラス MV — 描画エンジン
   ・背景: WebGL2 のフラグメントシェーダー（太陽・コロナ・岩戸・水平線）を 960x540 で描く
   ・レイヤー: Canvas2D 1920x1080（文字・キャラ・図形・粒子）
   ・仕上げ: 合成 → ブルーム → 色収差・粒状感・周辺減光・フラッシュ
   すべて「時刻 t の純粋な関数」。同じ t なら必ず同じ絵になる（並列レンダリング可）。
   ================================================================ */
const W = 1920, H = 1080, CX = W / 2, CY = H / 2;

// ---------- 数学 ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const sat = x => clamp(x, 0, 1);
const lerp = (a, b, t) => a + (b - a) * t;
const prog = (t, a, b) => sat((t - a) / (b - a));
const smooth = x => { x = sat(x); return x * x * (3 - 2 * x); };
const TAU = Math.PI * 2;
const E = {
  lin: x => x,
  inQuad: x => x * x, outQuad: x => 1 - (1 - x) * (1 - x),
  inCubic: x => x * x * x, outCubic: x => 1 - Math.pow(1 - x, 3),
  inOutCubic: x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2,
  inQuint: x => Math.pow(x, 5), outQuint: x => 1 - Math.pow(1 - x, 5),
  inOutQuint: x => x < .5 ? 16 * Math.pow(x, 5) : 1 - Math.pow(-2 * x + 2, 5) / 2,
  inExpo: x => x <= 0 ? 0 : Math.pow(2, 10 * x - 10), outExpo: x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x),
  inOutExpo: x => x <= 0 ? 0 : x >= 1 ? 1 : x < .5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2,
  outBack: x => { const c = 1.70158; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
  inBack: x => { const c = 1.70158; return (c + 1) * x * x * x - c * x * x; },
  outElastic: x => x <= 0 ? 0 : x >= 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - .75) * TAU / 3) + 1,
  inOutSine: x => -(Math.cos(Math.PI * x) - 1) / 2,
};
const ez = (t, a, b, e = E.outCubic) => e(prog(t, a, b));
const rnd = (i, s = 0) => { const x = Math.sin(i * 127.1 + s * 311.7 + 0.123) * 43758.5453; return x - Math.floor(x); };
const rs = (i, s = 0) => rnd(i, s) * 2 - 1;
function noise1(x, s = 0) { const i = Math.floor(x), f = x - i; const u = f * f * (3 - 2 * f); return lerp(rnd(i, s), rnd(i + 1, s), u); }
const sn1 = (x, s = 0) => noise1(x, s) * 2 - 1;

// ---------- キーフレーム・トラック ----------
// track([[t, v, ease?], ...]) → f(t)。ease は「その点へ向かう区間」のイージング
function track(keys) {
  return t => {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      if (t < keys[i][0]) { const a = keys[i - 1], b = keys[i]; const e = b[2] || E.inOutCubic; return lerp(a[1], b[1], e((t - a[0]) / (b[0] - a[0]))); }
    }
    return keys[keys.length - 1][1];
  };
}

// ---------- 音の同期データ ----------
let SYNC = null, P = 0.3375, OFF = 0.142, DUR = 266.34;
const ENV = {};
function initSync(s) {
  SYNC = s; P = s.P; OFF = s.OFF; DUR = s.dur;
  const n = s.low.length, F = s.F;
  const mk = (list, decay, minS = 0) => {
    const a = new Float32Array(n); let j = 0, cur = 0, last = -9;
    for (let i = 0; i < n; i++) {
      const t = i / F;
      while (j < list.length && list[j][0] <= t) { if (list[j][1] >= minS) { const v = Math.min(1, list[j][1]); cur = Math.max(v, cur * Math.exp(-(list[j][0] - last) / decay)); last = list[j][0]; } j++; }
      a[i] = cur * Math.exp(-(t - last) / decay);
    }
    return a;
  };
  ENV.kick = mk(s.kicks, 0.16, 0.35); ENV.snare = mk(s.snares, 0.12, 0.4); ENV.hit = mk(s.hits, 0.25, 0.75);
  for (const k of ['low', 'mid', 'high', 'all']) ENV[k] = Float32Array.from(s[k]);
}
function env(name, t) { const a = ENV[name]; const x = t * SYNC.F; const i = Math.floor(x); if (i < 0) return 0; if (i >= a.length - 1) return 0; return lerp(a[i], a[i + 1], x - i); }
const kick = t => env('kick', t), snare = t => env('snare', t);
const beatOf = t => (t - OFF) / P;           // 拍（1拍=0.3375秒）
const B = k => OFF + k * P * 4;                // 小節 k の頭の時刻
const bt = b => OFF + b * P;                   // 拍 b の時刻
// 拍ごとの減衰パルス（div=1:毎拍, 2:2拍ごと）
function pulse(t, div = 1, decay = 5) { const b = beatOf(t) / div; const f = b - Math.floor(b); return Math.exp(-f * decay); }

// ---------- WebGL ----------
let gl, glc, lay, ctx, acc, actx;
const VS = `#version 300 es
in vec2 a; out vec2 v; void main(){ v=a*.5+.5; gl_Position=vec4(a,0.,1.); }`;
const NOISE = `
float h21(vec2 p){ p=fract(p*vec2(123.34,456.21)); p+=dot(p,p+45.32); return fract(p.x*p.y); }
float vn(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
  return mix(mix(h21(i),h21(i+vec2(1,0)),f.x), mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),f.x), f.y); }
float fbm(vec2 p){ float s=0., a=.5; for(int i=0;i<5;i++){ s+=a*vn(p); p=p*2.03+vec2(17.1,9.2); a*=.5; } return s; }
float fbm3(vec2 p){ float s=0., a=.5; for(int i=0;i<3;i++){ s+=a*vn(p); p=p*2.03+vec2(17.1,9.2); a*=.5; } return s; }
`;
const FS_BG = `#version 300 es
precision highp float;
in vec2 v; out vec4 o;
uniform vec2 uRes; uniform float uT;
uniform vec3 uSun; uniform float uSunI,uCorona,uRays,uFog,uStars,uSurf;
uniform float uDoor,uDoorOn,uSeam,uBright,uCold,uHor,uHorOn,uRingR,uRingA,uEclipse,uDim;
uniform vec3 uNightA,uNightB;
${NOISE}
vec3 ramp(float x){
  x=clamp(x,0.,1.6);
  vec3 c=vec3(0.);
  c=mix(c,vec3(.32,.012,.03),smoothstep(0.,.22,x));
  c=mix(c,vec3(.93,.13,.05),smoothstep(.16,.46,x));
  c=mix(c,vec3(1.,.47,.07),smoothstep(.4,.7,x));
  c=mix(c,vec3(1.,.8,.33),smoothstep(.62,.9,x));
  c=mix(c,vec3(1.,.97,.86),smoothstep(.86,1.15,x));
  return c*(1.+max(0.,x-1.)*.6);
}
vec3 scene(vec2 p){
  vec2 q=p-uSun.xy; float d=length(q); float r=uSun.z; vec2 dir=q/max(d,1e-4);
  // 夜の群青
  float gy=p.y+.5;
  vec3 night=mix(uNightA,uNightB,smoothstep(0.,1.,gy));
  float f=fbm(p*1.6+vec2(uT*.02,-uT*.012));
  float f2=fbm(p*3.1-vec2(uT*.03,0.)+f);
  night+=uFog*vec3(.05,.1,.42)*pow(f2,2.2)*1.6;
  night+=uFog*vec3(.02,.03,.16)*f;
  // 星
  vec2 sg=p*90.; vec2 si=floor(sg); float sh=h21(si);
  float st=step(.992,sh)*smoothstep(.35,.0,length(fract(sg)-.5-(vec2(h21(si+3.),h21(si+7.))-.5)*.5));
  night+=uStars*st*(.5+.5*sin(uT*2.+sh*90.))*vec3(.7,.8,1.);
  // 太陽
  float heat=0.;
  float rr=d/max(r,1e-4);
  float ir=1./max(rr,1.);
  float glow=.6*pow(ir,3.2)+.26*pow(ir,1.25)+.1*pow(ir,.55);
  float lr=log(max(rr,.2));
  float cn=fbm(dir*2.6+vec2(lr*1.3-uT*.11, uT*.03));
  float cn2=fbm(dir*6.5-vec2(lr*2.0-uT*.2));
  float corona=pow(cn,2.2)*exp(-max(rr-1.,0.)/1.5)*1.1 + pow(cn2,3.)*exp(-max(rr-1.,0.)/.55)*1.0;
  float ray=pow(fbm3(dir*4.+uT*.03),3.)*2.2*exp(-max(rr-1.,0.)*.4)*smoothstep(1.,1.5,rr);
  heat+=uSunI*(glow+uCorona*corona*.42+uRays*ray*.3);
  if(rr<1.){
    float mu=sqrt(max(0.,1.-rr*rr));
    float g=fbm(q/r*4.+vec2(uT*.12,-uT*.07)); float g2=fbm(q/r*9.-vec2(uT*.2)+g*2.);
    float surf=.86+.3*mu+uSurf*((g-.5)*.5+(g2-.5)*.35);
    heat=mix(heat,uSunI*surf, smoothstep(1.,.985,rr));
    heat=mix(heat, heat*.02, uEclipse*smoothstep(1.,.97,rr));
  }
  // 衝撃波リング
  heat+=uRingA*exp(-pow((d-uRingR)/(.012+uRingR*.03),2.));
  vec3 sun=ramp(heat);
  vec3 col=night*(1.-clamp(heat*.9,0.,1.))+sun;
  return col;
}
void main(){
  vec2 p=(v-.5)*vec2(uRes.x/uRes.y,1.);
  vec2 ps=p; float refl=0.;
  if(uHorOn>.5 && p.y<uHor){
    float dy=uHor-p.y; refl=1.;
    float rip=(vn(vec2(p.x*7.,dy*60.-uT*1.4))-.5)*.05*(dy+.06)+(vn(vec2(p.x*40.,dy*220.-uT*3.))-.5)*.012;
    ps=vec2(p.x+rip*1.4, uHor+dy*1.0+rip);
  }
  vec3 col=scene(ps);
  if(refl>.5){ float dy=uHor-p.y; col*=mix(.75,.25,smoothstep(0.,.5,dy)); col+=vec3(.01,.015,.05)*smoothstep(.0,.4,dy); }
  if(uHorOn>.5){ col+=ramp(uSunI*.5)*exp(-abs(p.y-uHor)/.0035)*.5*exp(-abs(p.x-uSun.x)*1.2); }
  // 冷色へ反転
  col=mix(col, col.bgr*vec3(.75,.95,1.15), uCold);
  // 白い朝
  if(uBright>0.){
    vec2 q=p-uSun.xy; float d=length(q);
    vec3 sky=mix(vec3(1.,.93,.8),vec3(.99,.975,.94),smoothstep(-.5,.5,p.y));
    sky=mix(sky,vec3(1.,.82,.5),.35*exp(-d*1.6));
    float disc=smoothstep(uSun.z,uSun.z-.004,d);
    sky=mix(sky,vec3(1.,.99,.95),disc*.95);
    sky+=vec3(.06,.04,.0)*exp(-max(d-uSun.z,0.)*9.);
    col=mix(col,sky,uBright);
  }
  // 天の岩戸
  if(uDoorOn>.5){
    float jag=(fbm(vec2(p.y*2.6,3.))-.5)*.11+(vn(vec2(p.y*31.,9.))-.5)*.014;
    float ax=abs(p.x-jag*(.35+uDoor*.3));
    float side=sign(p.x-jag*(.35+uDoor*.3));
    float e=ax-uDoor;
    if(e>0.){
      vec2 rp=vec2(p.x-side*uDoor, p.y);
      float n=fbm(rp*vec2(5.,2.5)+side*4.); float n2=fbm(rp*vec2(22.,9.)+n*2.);
      float n3=fbm(rp*vec2(22.,9.)+n*2.+vec2(-side*.03,0.));
      float relief=(n2-n3)*9.;
      vec3 rock=vec3(.012,.014,.026)+vec3(.02,.024,.05)*n*n2*1.5;
      float spill=exp(-e/.05)*.9+exp(-e/.3)*.22;
      float lit=(uSeam+uSunI*smoothstep(0.,.03,uDoor))*spill*(.55+relief+n2*.6);
      vec3 rc=rock+ramp(clamp(lit,0.,1.05))*.95;
      float edge=smoothstep(0.,.0025,e);
      col=mix(col,rc,edge);
    }
    col+=ramp(1.1)*uSeam*exp(-abs(ax-uDoor*.0)/.0016)*step(uDoor,.0005)*(.7+.3*vn(vec2(p.y*30.,uT*3.)));
  }
  col*=uDim;
  o=vec4(col,1.);
}`;
const FS_COMP = `#version 300 es
precision highp float; in vec2 v; out vec4 o;
uniform sampler2D tBg,tLay; uniform vec2 uShake; uniform float uZoom,uRot,uBgZoom;
void main(){
  vec2 c=v-.5; c.x*=16./9.;
  float cs=cos(uRot), sn=sin(uRot); c=mat2(cs,-sn,sn,cs)*c; c/=uZoom; c.x/=16./9.;
  vec2 uv=c+.5+uShake;
  vec3 bg=texture(tBg,(uv-.5)/uBgZoom+.5).rgb;
  vec4 l=texture(tLay,uv);
  if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.) l=vec4(0.);
  o=vec4(bg*(1.-l.a)+l.rgb,1.);
}`;
const FS_BRIGHT = `#version 300 es
precision highp float; in vec2 v; out vec4 o; uniform sampler2D tex; uniform float uThr;
void main(){ vec3 c=texture(tex,v).rgb; float l=max(c.r,max(c.g,c.b)); o=vec4(c*smoothstep(uThr,uThr+.35,l),1.); }`;
const FS_BLUR = `#version 300 es
precision highp float; in vec2 v; out vec4 o; uniform sampler2D tex; uniform vec2 uDir;
void main(){ vec3 c=texture(tex,v).rgb*.227;
  c+=(texture(tex,v+uDir*1.385).rgb+texture(tex,v-uDir*1.385).rgb)*.316;
  c+=(texture(tex,v+uDir*3.231).rgb+texture(tex,v-uDir*3.231).rgb)*.0703; o=vec4(c,1.); }`;
const FS_FINAL = `#version 300 es
precision highp float; in vec2 v; out vec4 o;
uniform sampler2D tex,tB1,tB2; uniform float uT,uCA,uGrain,uVig,uFlash,uFade,uInvert,uBloom,uBars,uSatu,uWarm;
${NOISE}
void main(){
  vec2 c=v-.5; float r2=dot(c,c);
  vec2 off=c*uCA*(.6+r2*2.);
  vec3 col=vec3(texture(tex,v-off).r, texture(tex,v).g, texture(tex,v+off).b);
  vec3 bl=texture(tB1,v).rgb*.55+texture(tB2,v).rgb*.75;
  col+=bl*uBloom;
  float l=dot(col,vec3(.299,.587,.114));
  col=mix(vec3(l),col,uSatu);
  col=mix(col,1.-col,uInvert);
  col*=mix(1.,smoothstep(.95,.25,sqrt(r2)*1.15),uVig);
  col=col/(1.+max(vec3(0.),col-1.)*.5);
  col=mix(col,vec3(1.,.97,.9),clamp(uFlash,0.,1.));
  float g=h21(v*vec2(1920.,1080.)+fract(uT*7.13)*311.)-.5;
  col+=g*uGrain*(1.-l*.5);
  col*=uFade;
  float bar=step(abs(c.y),.5-uBars);
  col*=bar;
  o=vec4(clamp(col,0.,1.),1.);
}`;
const G = { prog: {}, fb: {} };
function mkProg(fs) {
  const p = gl.createProgram();
  for (const [type, src] of [[gl.VERTEX_SHADER, VS], [gl.FRAGMENT_SHADER, fs]]) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) + '\n' + src.split('\n').map((l, i) => (i + 1) + ': ' + l).join('\n'));
    gl.attachShader(p, s);
  }
  gl.bindAttribLocation(p, 0, 'a'); gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const inf = gl.getActiveUniform(p, i); u[inf.name] = { loc: gl.getUniformLocation(p, inf.name), type: inf.type }; }
  return { p, u };
}
function mkFB(w, h) {
  const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  return { fb, tex, w, h };
}
function pass(prog, target, uniforms, textures) {
  gl.bindFramebuffer(gl.FRAMEBUFFER, target ? target.fb : null);
  gl.viewport(0, 0, target ? target.w : W, target ? target.h : H);
  gl.useProgram(prog.p);
  let unit = 0;
  for (const k in textures) { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, textures[k]); if (prog.u[k]) gl.uniform1i(prog.u[k].loc, unit); unit++; }
  for (const k in uniforms) {
    const u = prog.u[k]; if (!u) continue; const val = uniforms[k];
    if (typeof val === 'number') gl.uniform1f(u.loc, val);
    else if (val.length === 2) gl.uniform2f(u.loc, val[0], val[1]);
    else if (val.length === 3) gl.uniform3f(u.loc, val[0], val[1], val[2]);
  }
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}
function initGL() {
  glc = document.getElementById('out'); glc.width = W; glc.height = H;
  gl = glc.getContext('webgl2', { preserveDrawingBuffer: true, antialias: false, alpha: false });
  const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  G.prog.bg = mkProg(FS_BG); G.prog.comp = mkProg(FS_COMP); G.prog.bright = mkProg(FS_BRIGHT); G.prog.blur = mkProg(FS_BLUR); G.prog.fin = mkProg(FS_FINAL);
  G.fb.bg = mkFB(960, 540); G.fb.comp = mkFB(W, H);
  G.fb.b1a = mkFB(480, 270); G.fb.b1b = mkFB(480, 270); G.fb.b2a = mkFB(160, 90); G.fb.b2b = mkFB(160, 90);
  G.layTex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, G.layTex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  lay = document.createElement('canvas'); lay.width = W; lay.height = H; ctx = lay.getContext('2d');
  acc = document.createElement('canvas'); acc.width = W; acc.height = H; actx = acc.getContext('2d');
}
// 画面px → シェーダー座標
const px2p = (x, y) => [(x - CX) / H, (CY - y) / H];

// ---------- 文字 ----------
const F_MIN = '"Shippori Mincho B1"', F_GOTH = '"Dela Gothic One"', F_LAT = '"Cinzel"';
const fnt = (fam, size, w) => `${w || (fam === F_GOTH ? 400 : fam === F_LAT ? 700 : 800)} ${size}px ${fam}`;
const _mc = new Map(); let _mctx = null;
function measure(ch, fam, w) {
  const k = ch + fam + (w || ''); let m = _mc.get(k);
  if (m === undefined) { if (!_mctx) _mctx = document.createElement('canvas').getContext('2d'); _mctx.font = fnt(fam, 100, w); m = _mctx.measureText(ch).width / 100; _mc.set(k, m); }
  return m;
}
const SMALL = 'ぁぃぅぇぉっゃゅょァィゥェォッャュョ', ROT = 'ー〜—―…';
// レイアウト: 原点中心。glyph の x,y は字の中心
function layout(str, o = {}) {
  const fam = o.fam || F_MIN, size = o.size || 100, tr = (o.track || 0) * size, vert = !!o.vert;
  const gs = []; let pos = 0;
  const chars = [...str];
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i];
    if (ch === ' ' || ch === '　') { pos += size * (o.space === undefined ? .5 : o.space); continue; }
    const w = vert ? size : measure(ch, fam, o.w) * size;
    gs.push({ ch, i: gs.length, p: pos + w / 2, w });
    pos += w + tr;
  }
  const total = pos - tr;
  for (const g of gs) { const c = g.p - total / 2; if (vert) { g.x = 0; g.y = c; } else { g.x = c; g.y = 0; } }
  return { gs, n: gs.length, len: total, fam, size, vert, w: o.w, fontStr: fnt(fam, size, o.w) };
}
function glyph(c, L, g) {
  if (L.vert) {
    if (ROT.includes(g.ch)) { c.save(); c.translate(g.x, g.y); c.rotate(Math.PI / 2); c.fillText(g.ch, 0, 0); c.restore(); return; }
    if (SMALL.includes(g.ch)) { c.fillText(g.ch, g.x + L.size * .11, g.y - L.size * .11); return; }
  }
  c.fillText(g.ch, g.x, g.y);
}
// fn(g,i,n) → null か {a,dx,dy,s,sx,sy,rot,col}。色は fillStyle を先に設定しておく
function drawText(c, L, x, y, fn, o = {}) {
  c.save(); c.translate(x, y); if (o.rot) c.rotate(o.rot); if (o.scale) c.scale(o.scale, o.scale);
  c.font = L.fontStr; c.textAlign = 'center'; c.textBaseline = 'middle';
  const base = c.globalAlpha;
  for (const g of L.gs) {
    const r = fn ? fn(g, g.i, L.n) : {}; if (!r) continue;
    const a = r.a === undefined ? 1 : r.a; if (a <= 0.003) continue;
    c.globalAlpha = base * sat(a);
    if (r.col) c.fillStyle = r.col;
    if (r.dx || r.dy || r.s !== undefined || r.rot || r.sx !== undefined || r.sy !== undefined) {
      c.save(); c.translate(g.x + (r.dx || 0), g.y + (r.dy || 0)); if (r.rot) c.rotate(r.rot);
      const s = r.s === undefined ? 1 : r.s; c.scale(s * (r.sx === undefined ? 1 : r.sx), s * (r.sy === undefined ? 1 : r.sy));
      glyph(c, L, { ch: g.ch, x: 0, y: 0 }); c.restore();
    } else glyph(c, L, g);
  }
  c.restore();
}
// よく使う登場: 1字ずつ下から浮かび上がる
const rise = (t, t0, o = {}) => (g, i, n) => {
  const d = o.stag === undefined ? .045 : o.stag, du = o.dur || .5; const k = E.outQuint(prog(t, t0 + i * d, t0 + i * d + du));
  const out = o.out === undefined ? 0 : E.inCubic(prog(t, o.out + i * (o.ostag || .015), o.out + i * (o.ostag || .015) + (o.odur || .3)));
  const ax = o.vert ? 0 : 1;
  return { a: k * (1 - out), dy: (ax ? (1 - k) * (o.dist || 40) : 0) - out * (ax ? 30 : 0), dx: (ax ? 0 : (1 - k) * (o.dist || 40)) , s: o.pop ? lerp(o.pop, 1, k) : 1 };
};

// ---------- 3D カメラ ----------
function camera(o) { return Object.assign({ x: 0, y: 0, z: 0, yaw: 0, pitch: 0, roll: 0, f: 1100 }, o); }
function proj(cam, x, y, z) {
  let dx = x - cam.x, dy = y - cam.y, dz = z - cam.z;
  let c = Math.cos(-cam.yaw), s = Math.sin(-cam.yaw); let x1 = dx * c + dz * s, z1 = -dx * s + dz * c;
  c = Math.cos(-cam.pitch); s = Math.sin(-cam.pitch); let y1 = dy * c - z1 * s, z2 = dy * s + z1 * c;
  c = Math.cos(-cam.roll); s = Math.sin(-cam.roll); const x2 = x1 * c - y1 * s, y2 = x1 * s + y1 * c;
  if (z2 < 1) return null;
  const k = cam.f / z2; return { x: CX + x2 * k, y: CY + y2 * k, s: k, z: z2 };
}
// 平面上の字: 中心 c と基底 U,V(3D) から 2D アフィンを作る
function planeTransform(c2d, cam, cx, cy, cz, U, V) {
  const p0 = proj(cam, cx, cy, cz); if (!p0) return null;
  const pu = proj(cam, cx + U[0], cy + U[1], cz + U[2]), pv = proj(cam, cx + V[0], cy + V[1], cz + V[2]); if (!pu || !pv) return null;
  c2d.setTransform(pu.x - p0.x, pu.y - p0.y, pv.x - p0.x, pv.y - p0.y, p0.x, p0.y); return p0;
}

// ---------- 画像 ----------
const IMG = {};
function loadImg(name, src) { return new Promise((res, rej) => { const i = new Image(); i.onload = () => { IMG[name] = i; res(i); }; i.onerror = rej; i.src = src; }); }
const _vc = new Map();
function variant(key, w, h, draw) { let c = _vc.get(key); if (!c) { c = document.createElement('canvas'); c.width = Math.ceil(w); c.height = Math.ceil(h); draw(c.getContext('2d'), c); _vc.set(key, c); } return c; }
// シルエット（単色）
function silhouette(name, color) { const im = IMG[name]; return variant('sil' + name + color, im.width, im.height, c => { c.drawImage(im, 0, 0); c.globalCompositeOperation = 'source-in'; c.fillStyle = color; c.fillRect(0, 0, im.width, im.height); }); }
// 光の当たる側のふち（リムライト）。dx,dy は光の来る向き（px）
function rim(name, dx, dy, color, soft = 0) {
  const im = IMG[name]; return variant('rim' + name + dx + ',' + dy + color + soft, im.width, im.height, (c, cv) => {
    c.drawImage(im, 0, 0); c.globalCompositeOperation = 'destination-out';
    if (soft) c.filter = `blur(${soft}px)`;
    c.drawImage(im, -dx, -dy); c.filter = 'none';
    c.globalCompositeOperation = 'source-in'; c.fillStyle = color; c.fillRect(0, 0, cv.width, cv.height);
  });
}
// 色をかぶせた版（暗い場面用のグレーディング）
function graded(name, mulColor, amt) {
  const im = IMG[name]; return variant('gr' + name + mulColor + amt, im.width, im.height, (c, cv) => {
    c.drawImage(im, 0, 0); c.globalCompositeOperation = 'multiply'; c.fillStyle = mulColor; c.globalAlpha = amt; c.fillRect(0, 0, cv.width, cv.height);
    c.globalAlpha = 1; c.globalCompositeOperation = 'destination-in'; c.drawImage(im, 0, 0);
  });
}
// 髪のある高さ（画像の上から何pxまでを風で揺らすか）。顔の行は揺らさない
const HAIR = { back: 430, side: 185, face: 360, front: 60 };
// 生きている感じ: 髪が風でなびき、呼吸でわずかに伸び縮みする（横の帯に分けてずらして描く）
const _live = new WeakMap(), LPAD = 40;
function liveCanvas(img, name, t) {
  // 元の解像度のまま、髪の行だけを1pxずつ横にずらして別キャンバスに描く（継ぎ目が出ない）
  let cv = _live.get(img); if (!cv) { cv = document.createElement('canvas'); cv.width = img.width + LPAD * 2; cv.height = img.height; _live.set(img, cv); }
  const x = cv.getContext('2d'), ih = img.height, iw = img.width, hair = Math.min(ih, HAIR[name] || ih * .3), amp = iw * .022;
  x.clearRect(0, 0, cv.width, cv.height);
  const gust = .35 * sn1(t * .6, 5);
  for (let y = 0; y < hair; y++) {
    const wgt = Math.pow(1 - y / hair, 1.4);
    const dx = wgt * amp * (Math.sin(t * 1.9 + y * .013) + .45 * Math.sin(t * 3.7 - y * .031) + gust);
    x.drawImage(img, 0, y, iw, 1, LPAD + dx, y, iw, 1);
  }
  if (hair < ih) x.drawImage(img, 0, hair, iw, ih - hair, LPAD, hair, iw, ih - hair);
  return cv;
}
// キャラを描く: 足元(または指定アンカー)を x,y に、高さ h。o.live に時刻を渡すと髪と呼吸が動く
function drawChar(c, name, x, y, h, o = {}) {
  const im = IMG[name]; const s = h / im.height; const w = im.width * s;
  const ax = o.ax === undefined ? .5 : o.ax, ay = o.ay === undefined ? 1 : o.ay;
  const live = o.live !== undefined, t = o.live || 0;
  c.save(); c.translate(x, y); if (o.rot) c.rotate(o.rot); if (o.flip) c.scale(-1, 1);
  if (live) { const br = Math.sin(t * 1.55); c.scale(1 - br * .0035, 1 + br * .006); c.rotate(Math.sin(t * .7) * .006); }
  const X = -w * ax, Y = -h * ay;
  const a0 = c.globalAlpha;
  const put = img => { if (!live) return c.drawImage(img, X, Y, w, h); const cv = liveCanvas(img, name, t); c.drawImage(cv, X - LPAD * s, Y, cv.width * s, h); };
  if (o.sil) put(silhouette(name, o.sil));
  else if (o.grade) put(graded(name, o.grade, o.gamt === undefined ? .7 : o.gamt));
  else put(im);
  if (o.rim) { c.globalCompositeOperation = 'lighter'; c.globalAlpha = a0 * (o.rimA === undefined ? 1 : o.rimA); put(rim(name, o.rim[0], o.rim[1], o.rimCol || '#ffb347', o.rimSoft || 0)); c.globalCompositeOperation = 'source-over'; c.globalAlpha = a0; }
  c.restore();
}

// ---------- フレーム描画 ----------
const BG_DEF = { uSun: [0, 0, .2], uSunI: 0, uCorona: 1, uRays: .5, uFog: 1, uStars: 0, uSurf: 1, uDoor: 0, uDoorOn: 0, uSeam: 0, uBright: 0, uCold: 0, uHor: -.2, uHorOn: 0, uRingR: 0, uRingA: 0, uEclipse: 0, uDim: 1, uNightA: [.004, .006, .02], uNightB: [.012, .02, .075] };
const POST_DEF = { shake: [0, 0], zoom: 1, rot: 0, bgZoom: 1, ca: 0.0015, grain: .055, vig: .8, flash: 0, fade: 1, invert: 0, bloom: .62, thr: .7, bars: 0, satu: 1, mb: 1, shutter: .5 };
let TIMELINE = null; // { bg(t)→部分, post(t)→部分, draw(ctx,t) } を scenes.js が設定
function renderFrame(t) {
  const bg = Object.assign({}, BG_DEF, TIMELINE.bg(t));
  const po = Object.assign({}, POST_DEF, TIMELINE.post(t));
  // レイヤー（必要ならサブフレームを重ねてモーションブラー）
  const n = Math.max(1, Math.round(po.mb));
  if (n === 1) { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.clearRect(0, 0, W, H); TIMELINE.draw(ctx, t); }
  else {
    actx.setTransform(1, 0, 0, 1, 0, 0); actx.clearRect(0, 0, W, H);
    for (let i = 0; i < n; i++) {
      const ts = t + ((i + .5) / n - .5) * po.shutter / 30;
      ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.clearRect(0, 0, W, H); TIMELINE.draw(ctx, ts);
      actx.globalCompositeOperation = 'lighter'; actx.globalAlpha = 1 / n; actx.drawImage(lay, 0, 0);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'copy'; ctx.drawImage(acc, 0, 0); ctx.globalCompositeOperation = 'source-over';
  }
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, G.layTex);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, lay);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  bg.uRes = [960, 540]; bg.uT = t;
  pass(G.prog.bg, G.fb.bg, bg, {});
  pass(G.prog.comp, G.fb.comp, { uShake: [po.shake[0] / W, po.shake[1] / H], uZoom: po.zoom, uRot: po.rot, uBgZoom: po.bgZoom }, { tBg: G.fb.bg.tex, tLay: G.layTex });
  pass(G.prog.bright, G.fb.b1a, { uThr: po.thr }, { tex: G.fb.comp.tex });
  pass(G.prog.blur, G.fb.b1b, { uDir: [1 / 480, 0] }, { tex: G.fb.b1a.tex });
  pass(G.prog.blur, G.fb.b1a, { uDir: [0, 1 / 270] }, { tex: G.fb.b1b.tex });
  pass(G.prog.blur, G.fb.b2a, { uDir: [1.5 / 480, 0] }, { tex: G.fb.b1a.tex });
  pass(G.prog.blur, G.fb.b2b, { uDir: [0, 1 / 90] }, { tex: G.fb.b2a.tex });
  pass(G.prog.blur, G.fb.b2a, { uDir: [1 / 160, 0] }, { tex: G.fb.b2b.tex });
  pass(G.prog.blur, G.fb.b2b, { uDir: [0, 1.5 / 90] }, { tex: G.fb.b2a.tex });
  pass(G.prog.fin, null, { uT: t, uCA: po.ca, uGrain: po.grain, uVig: po.vig, uFlash: po.flash, uFade: po.fade, uInvert: po.invert, uBloom: po.bloom, uBars: po.bars, uSatu: po.satu }, { tex: G.fb.comp.tex, tB1: G.fb.b1a.tex, tB2: G.fb.b2b.tex });
}
