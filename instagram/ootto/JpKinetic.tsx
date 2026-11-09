// Japanese kinetic explainer in ETERNALd.c.t's colours: alternating light / dark beats, one real picture or 3D object per beat,
// a small lead line over a big key line revealed on the voice, a list card, 2-frame flashes at beat starts, a CTA end card.
// Used in the Ootto workspace (/work/project/src/JpKinetic.tsx). Data per reel: src/reels/rN.ts (ReelData).
import React from "react";
import {AbsoluteFill, Audio, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import {loadFont} from "@remotion/google-fonts/NotoSansJP";

const {fontFamily} = loadFont("normal", {weights: ["700", "900"], ignoreTooManyRequestsWarning: true});
const W = 1080, H = 1920;
const C = {light: "#E6FCFF", light2: "#D1E5E8", dark: "#0C1517", ink: "#1C1D1B", inkOnDark: "#F2FBFC", accent: "#00E5FF", accentInk: "#007C8A"};
const cl = {extrapolateLeft: "clamp", extrapolateRight: "clamp"} as const;
const ease = Easing.out(Easing.cubic);

export type Chunk = {t: string; at: number}; // text and the second it is spoken
export type Beat = {
  from: number; to: number; // seconds
  bg: "light" | "dark" | "photo";
  photo?: string; video?: string; videoFit?: "cover" | "contain"; videoH?: number; textTop?: number; icon?: string; icon2?: string;
  lead?: Chunk[]; key?: Chunk[]; key2?: Chunk[]; keyPx?: number;
  card?: {title: string; items: {t: string; at: number; icon?: string}[]};
  cta?: {handle: string; line: string};
  flash?: boolean;
};
export type ReelData = {vo: string; bed: string; bedVol: number; end: number; beats: Beat[]};
export const totalFrames = (d: ReelData) => Math.round(d.end * 30);

const textW = (s: string, px: number) => [...s].reduce((a, ch) => a + (/[\x00-\x7F]/.test(ch) ? 0.58 : 1.0), 0) * px;
const fit = (chunks: Chunk[], px: number, max = 880) => Math.min(px, (px * max) / Math.max(1, textW(chunks.map((c) => c.t).join(""), px)));

const Line: React.FC<{chunks: Chunk[]; t: number; px: number; color: string; key2?: boolean; dark: boolean}> = ({chunks, t, px, color, key2, dark}) => (
  <div style={{display: "flex", justifyContent: "center", flexWrap: "nowrap", whiteSpace: "nowrap", fontSize: px, lineHeight: 1.15, fontWeight: key2 ? 900 : 700, letterSpacing: "-0.02em"}}>
    {chunks.map((c, i) => {
      const p = interpolate(t, [c.at, c.at + 0.18], [0, 1], {...cl, easing: ease});
      const st: React.CSSProperties = {display: "inline-block", color, opacity: c.at <= 0 ? 1 : t < c.at ? 0 : p,
        transform: c.at <= 0 ? undefined : key2 ? `scale(${1.15 - 0.15 * p})` : `translateY(${(1 - p) * px * 0.25}px)`, filter: key2 && c.at > 0 ? `blur(${(1 - p) * 6}px)` : undefined};
      if (key2 && !dark) Object.assign(st, {background: `linear-gradient(transparent 62%, ${C.accent} 62%, ${C.accent} 92%, transparent 92%)`});
      if (key2 && dark) st.textShadow = "0 0 28px rgba(0,229,255,.45)";
      return <span key={i} style={st}>{c.t}</span>;
    })}
  </div>
);

const Icon: React.FC<{src: string; t: number; x: number; y: number; size: number; delay?: number}> = ({src, t, x, y, size, delay = 0}) => {
  const p = interpolate(t, [delay, delay + 0.3], [0, 1], {...cl, easing: Easing.out(Easing.back(1.8))});
  return <Img src={staticFile(src)} style={{position: "absolute", left: x - size / 2, top: y - size / 2 + Math.sin(t * 2.2) * 10, width: size,
    transform: `scale(${delay === 0 ? 0.75 + 0.25 * p : p}) rotate(${(1 - p) * -18 + Math.sin(t * 1.4) * 3}deg)`, filter: "drop-shadow(0 30px 40px rgba(0,0,0,.25))"}} />;
};

const BeatView: React.FC<{b: Beat; s: number}> = ({b, s}) => {
  const t = s; // absolute seconds (chunk times are absolute)
  const lt = s - b.from;
  const dark = b.bg !== "light";
  const ink = dark ? C.inkOnDark : C.ink;
  const keyCol = dark ? C.accent : C.ink;
  return (
    <AbsoluteFill style={{background: b.bg === "light" ? C.light : C.dark, fontFamily}}>
      {b.bg === "light" ? <AbsoluteFill style={{backgroundImage: "linear-gradient(rgba(0,124,138,.08) 2px, transparent 2px), linear-gradient(90deg, rgba(0,124,138,.08) 2px, transparent 2px)", backgroundSize: "72px 72px"}} /> : null}
      {b.bg === "dark" ? <AbsoluteFill style={{background: "radial-gradient(circle at 50% 30%, rgba(0,229,255,.18) 0, rgba(0,0,0,0) 55%)"}} /> : null}
      {b.photo ? (
        <AbsoluteFill>
          <Img src={staticFile(b.photo)} style={{position: "absolute", width: "100%", height: "100%", objectFit: "cover", objectPosition: "38% 50%",
            transform: `scale(${interpolate(lt, [0, b.to - b.from], [1.18, 1.3], cl)}) translateX(${interpolate(lt, [0, b.to - b.from], [0, -30], cl)}px)`}} />
          <AbsoluteFill style={{background: "linear-gradient(180deg, rgba(12,21,23,.15) 0%, rgba(12,21,23,.55) 35%, rgba(12,21,23,.92) 62%, rgba(12,21,23,.95) 100%)"}} />
        </AbsoluteFill>
      ) : null}
      {b.video ? (
        <AbsoluteFill>
          <Sequence from={Math.round(b.from * 30)} layout="none">
            <OffthreadVideo src={staticFile(b.video)} muted style={{position: "absolute", width: "100%", height: b.videoH ? `${b.videoH * 100}%` : b.videoFit === "contain" ? "62%" : "100%", top: 0, objectFit: b.videoFit ?? "cover"}} />
          </Sequence>
          <AbsoluteFill style={{background: b.videoH ? `linear-gradient(180deg, rgba(12,21,23,0) 0%, rgba(12,21,23,0) ${b.videoH * 100 - 4}%, rgba(12,21,23,1) ${b.videoH * 100 + 2}%)` : "linear-gradient(180deg, rgba(12,21,23,0) 0%, rgba(12,21,23,0) 38%, rgba(12,21,23,.85) 55%, rgba(12,21,23,.95) 100%)"}} />
        </AbsoluteFill>
      ) : null}
      {b.icon ? <>
        <Img src={staticFile(b.icon)} style={{position: "absolute", left: 760, top: 120 - lt * 12, width: 420, opacity: 0.55, filter: "blur(10px)", transform: "rotate(18deg)"}} />
        <Img src={staticFile(b.icon2 ?? b.icon)} style={{position: "absolute", left: -120, top: 1350 + lt * 10, width: 480, opacity: 0.5, filter: "blur(10px)", transform: "rotate(-14deg)"}} />
        <Icon src={b.icon} t={lt} x={b.icon2 ? 400 : W / 2} y={520} size={b.icon2 ? 400 : 480} />
      </> : null}
      {b.icon2 ? <Icon src={b.icon2} t={lt} x={720} y={470} size={340} delay={0.25} /> : null}
      {b.card ? (
        <div style={{position: "absolute", left: 90, top: 300, width: 860, borderRadius: 40, background: dark ? "rgba(255,255,255,.07)" : "#fff",
          boxShadow: "0 30px 70px rgba(0,0,0,.18)", padding: "44px 48px", boxSizing: "border-box",
          transform: `translateY(${interpolate(lt, [0, 0.35], [-160, 0], {...cl, easing: Easing.out(Easing.back(1.4))})}px)`}}>
          <div style={{fontSize: 64, fontWeight: 900, color: ink, textAlign: "center", marginBottom: 26}}>{b.card.title}</div>
          <div style={{height: 8, borderRadius: 4, background: C.accent, marginBottom: 40}} />
          {b.card.items.map((it, i) => {
            const q = interpolate(t, [it.at, it.at + 0.2], [0, 1], {...cl, easing: ease});
            return (
              <div key={i} style={{display: "flex", alignItems: "center", gap: 22, marginBottom: 34, opacity: t < it.at ? 0 : q, transform: `translateX(${(1 - q) * 40}px)`}}>
                {it.icon ? <Img src={staticFile(it.icon)} style={{width: 120, height: 120}} /> : null}
                <div style={{fontSize: fit([{t: it.t, at: 0}], 66, 600), fontWeight: 700, color: ink, whiteSpace: "nowrap"}}>{it.t}</div>
              </div>
            );
          })}
        </div>
      ) : null}
      <div style={{position: "absolute", left: 0, width: W, top: b.textTop ?? (b.card ? 1060 : b.photo ? 560 : b.video ? 900 : 820), display: "flex", flexDirection: "column", alignItems: "center", gap: 18}}>
        {b.lead?.length ? <Line chunks={b.lead} t={t} px={fit(b.lead, 76)} color={ink} dark={dark} /> : null}
        {b.key?.length ? <Line chunks={b.key} t={t} px={fit(b.key, b.keyPx ?? 150)} color={keyCol} key2 dark={dark} /> : null}
        {b.key2?.length ? <Line chunks={b.key2} t={t} px={fit(b.key2, b.keyPx ?? 150)} color={keyCol} key2 dark={dark} /> : null}
      </div>
      {b.cta ? (
        <div style={{position: "absolute", left: 90, width: 900, top: 1090, textAlign: "center", opacity: interpolate(lt, [0.3, 0.5], [0, 1], cl)}}>
          <div style={{display: "inline-block", padding: "18px 34px", borderRadius: 999, background: C.dark, color: C.accent, fontSize: 46, fontWeight: 700}}>{b.cta.line}</div>
          <div style={{marginTop: 18, fontSize: 40, fontWeight: 700, color: C.accentInk}}>{b.cta.handle}</div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const JpKinetic: React.FC<{d: ReelData}> = ({d}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = f / fps;
  const b = d.beats.find((x) => s >= x.from && s < x.to) ?? d.beats[d.beats.length - 1];
  const startF = Math.round(b.from * fps);
  const flash = b.flash && f - startF >= 0 && f - startF < 2 ? (f === startF ? 0.8 : 0.4) : 0;
  return (
    <AbsoluteFill style={{background: C.dark}}>
      <BeatView b={b} s={s} />
      {flash ? <AbsoluteFill style={{background: "#fff", opacity: flash}} /> : null}
      <Audio src={staticFile(d.vo)} />
      <Audio src={staticFile(d.bed)} volume={(fr) => d.bedVol * interpolate(fr, [0, 10, totalFrames(d) - 20, totalFrames(d)], [0, 1, 1, 0], cl)} />
    </AbsoluteFill>
  );
};
