// Estilo Dra. Aline Albuquerque (Harmonizacao Facial em Santos / Metodo Fenix).
// Paleta do config/marca.json do projeto dela: preto quente, nude rose, rose gold e o coral "fenix".
// Titulos em Cormorant Garamond (italico nos ganchos), texto e legenda em Manrope 800.
// Mesma logica de cortes, legenda e desvio do rosto do ShortPAB. Serve 9:16 (1080x1920) e 4:5 (1080x1350).
import { Caption, createTikTokStyleCaptions, TikTokPage } from "@remotion/captions";
import React, { useMemo } from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  interpolate,
  OffthreadVideo,
  Sequence,
  Series,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as loadSerif } from "@remotion/google-fonts/CormorantGaramond";
import { loadFont as loadSans } from "@remotion/google-fonts/Manrope";

const { fontFamily: SERIF } = loadSerif("italic", { weights: ["600", "700"], subsets: ["latin", "latin-ext"] });
loadSerif("normal", { weights: ["600", "700"], subsets: ["latin", "latin-ext"] });
const { fontFamily: SANS } = loadSans("normal", { weights: ["500", "600", "700", "800"], subsets: ["latin", "latin-ext"] });

const C = {
  dark: "#100c0b",
  dark2: "#1d1614",
  rose: "#d9a596",
  roseLight: "#f2c2b3",
  roseGold: "#b87a6a",
  fenix: "#e8603c",
  cream: "#f6ece6",
  ink: "#2a1a16",
};
const GRAD = `linear-gradient(90deg, ${C.rose}, ${C.fenix})`;

type Range = { fromMs: number; toMs: number };
type Face = { ms: number; eye: number | null; mouth: number | null; top: number | null; bottom: number | null };

export type ShortAlineProps = {
  video: string;
  captions: string;
  ranges: Range[];
  hook: { kicker: string; text: string; seconds: number } | null; // *palavra* = destaque rose/coral
  callouts: { text: string; atMs: number; seconds?: number; top?: boolean }[];
  etapas?: { text: string; atMs: number }[]; // chips do Metodo Fenix (opcional)
  lowerThird?: { nome: string; linha: string; registro?: string; atMs?: number; seconds?: number } | null;
  assinatura?: string | null; // @ discreto no canto depois da apresentacao
  aviso?: string | null; // faixa legal no rodape (CFBM/CFO/CFM)
  endCard: { title: string; subtitle: string; instagram?: string; whatsapp?: string; registro?: string; seconds: number } | null;
  zoom?: boolean; // punch-in leve alternado a cada corte
  showCaptions?: boolean;
  faces?: string;
  faceData?: Face[];
  words?: Caption[];
};

const FPS = 30;
const toFrame = (ms: number) => Math.round((ms / 1000) * FPS);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// faces.json vem em coordenadas 1080x1920. No 4:5 o corte fica mais para cima (20%) para nao comer a cabeca.
const posY = (H: number) => (H < 1900 ? 0.2 : 0.5);
const faceMap = (H: number) => {
  const scale = Math.max(1, H / 1920);
  const off = (1920 * scale - H) * posY(H);
  return (y: number) => y * scale - off;
};

const faceIn = (data: Face[], a: number, b: number, H: number) => {
  const m = faceMap(H);
  const xs = data.filter((f) => f.ms >= a - 150 && f.ms <= b + 150 && f.eye !== null && f.mouth !== null);
  if (!xs.length) return null;
  const brow = Math.min(...xs.map((f) => m(f.eye as number) - 0.45 * Math.max(20, (f.mouth as number) - (f.eye as number))));
  const lip = Math.max(...xs.map((f) => m(f.mouth as number) + 0.3 * Math.max(20, (f.mouth as number) - (f.eye as number))));
  return { brow, lip };
};

const overlaps = (f: { brow: number; lip: number }, y0: number, y1: number) => y0 < f.lip && y1 > f.brow;

// Onde a legenda cabe sem cobrir olhos e boca. Limite de baixo respeita a faixa de aviso.
const captionSlot = (data: Face[], a: number, b: number, H: number, aviso: boolean) => {
  const floor = H - (aviso ? 150 : 90);
  const base = Math.round(H * 0.615);
  const h = Math.round(H * 0.12);
  const f = faceIn(data, a, b, H);
  if (!f || !overlaps(f, base, base + h)) return { top: base, height: Math.min(h, floor - base) };
  const below = Math.max(base, Math.round(f.lip + 20));
  if (below + 110 <= floor) return { top: below, height: floor - below };
  const hi = Math.round(H * 0.13);
  if (!overlaps(f, hi, hi + 190)) return { top: hi, height: 190 };
  return { top: floor - 110, height: 110 };
};

const fade = (f: number, frames: number) =>
  frames < 6 ? 1 : interpolate(f, [0, 2, frames - 3, frames - 1], [0, 1, 1, 0], clamp);

const layout = (ranges: Range[]) => {
  let at = 0;
  return ranges.map((r) => {
    const from = toFrame(r.fromMs);
    const frames = Math.max(1, toFrame(r.toMs) - from);
    const part = { ...r, from, frames, at, shiftMs: ((at - from) / FPS) * 1000 };
    at += frames;
    return part;
  });
};

const toOutputMs = (ms: number, parts: ReturnType<typeof layout>) => {
  const p = parts.find((p) => ms >= p.fromMs && ms < p.toMs);
  return p ? ms + p.shiftMs : null;
};

export const calculateShortAlineMetadata: CalculateMetadataFunction<ShortAlineProps> = async ({ props }) => {
  const parts = layout(props.ranges);
  const raw = (await (await fetch(staticFile(props.captions))).json()) as Caption[];
  const faceData = props.faces ? ((await (await fetch(staticFile(props.faces))).json()) as Face[]) : [];
  const words = raw.flatMap((w) => {
    const p = parts.find((p) => w.startMs >= p.fromMs && w.startMs < p.toMs);
    if (!p) return [];
    const end = Math.min(w.endMs, p.toMs);
    return [{ ...w, startMs: w.startMs + p.shiftMs, endMs: end + p.shiftMs, timestampMs: null }];
  });
  const videoFrames = parts.reduce((n, p) => n + p.frames, 0);
  const endFrames = props.endCard ? toFrame(props.endCard.seconds * 1000) : 0;
  return { fps: FPS, durationInFrames: Math.max(1, videoFrames + endFrames), props: { ...props, words, faceData } };
};

// texto com *destaque* em gradiente rose -> coral
const Rich: React.FC<{ text: string }> = ({ text }) => (
  <>
    {text.split(/(\*[^*]+\*)/).filter(Boolean).map((part, i) =>
      part.startsWith("*") ? (
        <span key={i} style={{ background: GRAD, WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>
          {part.slice(1, -1)}
        </span>
      ) : (
        <span key={i}>{part}</span>
      ),
    )}
  </>
);

export const ShortAline: React.FC<ShortAlineProps> = ({
  video,
  ranges,
  hook,
  callouts,
  etapas = [],
  lowerThird = null,
  assinatura = null,
  aviso = null,
  endCard,
  zoom = true,
  showCaptions = true,
  words = [],
  faceData = [],
}) => {
  const { height: H } = useVideoConfig();
  const parts = useMemo(() => layout(ranges), [ranges]);
  const videoFrames = parts.reduce((n, p) => n + p.frames, 0);
  const { pages } = useMemo(() => createTikTokStyleCaptions({ captions: words, combineTokensWithinMilliseconds: 700 }), [words]);
  const hookFrames = hook ? toFrame(hook.seconds * 1000) : 0;
  const ltFrom = lowerThird ? toFrame(lowerThird.atMs ?? (hook ? hook.seconds * 1000 + 300 : 600)) : 0;
  const ltFrames = lowerThird ? toFrame((lowerThird.seconds ?? 4) * 1000) : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: C.dark }}>
      <Series>
        {parts.map((p, i) => (
          <Series.Sequence key={i} durationInFrames={p.frames}>
            <Clip video={video} from={p.from} frames={p.frames} punch={zoom && parts.length > 1 && i % 2 === 1} />
          </Series.Sequence>
        ))}
      </Series>

      {/* grade quente leve + vinheta embaixo para a legenda respirar */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(232,96,60,0.05), rgba(217,165,150,0.04))", mixBlendMode: "soft-light" }} />
      <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(16,12,11,0.35) 0%, rgba(16,12,11,0) 16%, rgba(16,12,11,0) 52%, rgba(16,12,11,0.62) 100%)` }} />

      {(showCaptions ? pages : []).map((page, i) => {
        const next = pages[i + 1];
        const from = toFrame(page.startMs);
        const until = Math.min(videoFrames, toFrame(next ? next.startMs : page.startMs + page.durationMs));
        if (until <= from) return null;
        return (
          <Sequence key={i} from={from} durationInFrames={until - from}>
            <CaptionPage page={page} slot={captionSlot(faceData, page.startMs, next ? next.startMs : page.startMs + page.durationMs, H, !!aviso)} />
          </Sequence>
        );
      })}

      {callouts.map((c, i) => {
        const at = toOutputMs(c.atMs, parts);
        if (at === null) return null;
        const secs = c.seconds ?? 2.4;
        const frames = toFrame(secs * 1000);
        const base = Math.round(H * 0.615);
        // logo acima da legenda; se a trilha de etapas estiver embaixo nesse momento, sobe mais um degrau
        const ets = etapas.map((e) => toOutputMs(e.atMs, parts)).filter((x): x is number => x !== null);
        const fe = ets.length ? faceIn(faceData, ets[0], ets[ets.length - 1] + 3500, H) : null;
        const etapasBaixas = ets.length > 0 && fe !== null && overlaps(fe, Math.round(H * 0.095), Math.round(H * 0.095) + 100);
        const durante = ets.length > 0 && at + secs * 1000 >= ets[0] && at <= ets[ets.length - 1] + 3500;
        const low = base - (etapasBaixas && durante ? 250 : 130);
        const high = Math.round(H * 0.17);
        const f = faceIn(faceData, at, at + secs * 1000, H);
        const up = c.top ?? (f !== null && overlaps(f, low, low + 110) && !overlaps(f, high, high + 110));
        return (
          <Sequence key={i} from={toFrame(at)} durationInFrames={frames}>
            <Callout text={c.text} frames={frames} y={up ? high : low} />
          </Sequence>
        );
      })}

      {etapas.length ? (
        (() => {
          const ts = etapas.map((e) => toOutputMs(e.atMs, parts)).filter((x): x is number => x !== null);
          if (!ts.length) return null;
          const start = toFrame(ts[0]);
          const end = Math.min(videoFrames, toFrame(ts[ts.length - 1] + 3500));
          // no alto por padrao; se o rosto estiver ali, a trilha desce para logo acima da legenda
          const topo = Math.round(H * 0.095);
          const f = faceIn(faceData, ts[0], ts[ts.length - 1] + 3500, H);
          const y = f && overlaps(f, topo, topo + 100) ? Math.round(H * 0.615) - 130 : topo;
          return (
            <Sequence from={start} durationInFrames={Math.max(1, end - start)}>
              <Etapas etapas={etapas.map((e, k) => ({ text: e.text, at: toFrame((ts[k] ?? ts[0]) - ts[0]) }))} frames={end - start} y={y} />
            </Sequence>
          );
        })()
      ) : null}

      {lowerThird ? (
        <Sequence from={ltFrom} durationInFrames={ltFrames}>
          <LowerThird {...lowerThird} frames={ltFrames} />
        </Sequence>
      ) : null}

      {assinatura ? (
        (() => {
          const from = lowerThird ? ltFrom + ltFrames : hookFrames;
          // some enquanto a trilha de etapas estiver na tela (mesmo lugar)
          const ts = etapas.map((e) => toOutputMs(e.atMs, parts)).filter((x): x is number => x !== null);
          const esconde = ts.length ? [toFrame(ts[0]) - from, toFrame(ts[ts.length - 1] + 3500) - from] : null;
          return (
            <Sequence from={from} durationInFrames={Math.max(1, videoFrames - from)}>
              <Assinatura text={assinatura} esconde={esconde} />
            </Sequence>
          );
        })()
      ) : null}

      {hook ? (
        <Sequence durationInFrames={hookFrames}>
          <HookCard
            kicker={hook.kicker}
            text={hook.text}
            frames={hookFrames}
            y={(() => {
              // no alto por padrao; se o rosto estiver ali, desce para logo abaixo da boca
              const topo = Math.round(H * 0.12);
              const f = faceIn(faceData, 0, hook.seconds * 1000, H);
              if (!f || !overlaps(f, topo, topo + 330)) return topo;
              return Math.min(Math.round(H * 0.615) - 350, Math.max(Math.round(f.lip + 40), Math.round(H * 0.3)));
            })()}
          />
        </Sequence>
      ) : null}

      {aviso ? (
        <Sequence durationInFrames={videoFrames}>
          <Aviso text={aviso} />
        </Sequence>
      ) : null}

      {endCard ? (
        <Sequence from={videoFrames} durationInFrames={toFrame(endCard.seconds * 1000)}>
          <EndCard {...endCard} />
        </Sequence>
      ) : null}

      <ProgressBar />
    </AbsoluteFill>
  );
};

const Clip: React.FC<{ video: string; from: number; frames: number; punch: boolean }> = ({ video, from, frames, punch }) => {
  const frame = useCurrentFrame();
  const { height: H } = useVideoConfig();
  // punch-in leve (1.06) nos cortes impares, com deriva lenta: da ritmo sem parecer efeito
  const s = punch ? 1.06 + interpolate(frame, [0, frames], [0, 0.012], clamp) : 1 + interpolate(frame, [0, frames], [0, 0.015], clamp);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <OffthreadVideo
        src={staticFile(video)}
        trimBefore={from}
        volume={(f) => fade(f, frames)}
        style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: `50% ${posY(H) * 100}%`, transform: `scale(${s})`, transformOrigin: "50% 38%" }}
      />
    </AbsoluteFill>
  );
};

const CaptionPage: React.FC<{ page: TikTokPage; slot: { top: number; height: number } }> = ({ page, slot }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const now = page.startMs + (frame / fps) * 1000;
  const pop = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 5 });
  const n = page.text.trim().length;
  const fontSize = Math.max(40, Math.min(74, Math.floor(880 / (n * 0.6)), Math.floor(slot.height * 0.55)));
  return (
    <AbsoluteFill style={{ top: slot.top, left: 70, width: 940, height: slot.height, justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize,
          lineHeight: 1.12,
          maxWidth: "100%",
          textAlign: "center",
          letterSpacing: "-0.01em",
          color: C.cream,
          padding: "14px 30px 16px",
          borderRadius: 999,
          background: "rgba(16,12,11,0.34)",
          backdropFilter: "blur(10px)",
          textShadow: "0 3px 14px rgba(0,0,0,0.55)",
          opacity: pop,
          transform: `translateY(${(1 - pop) * 10}px) scale(${0.94 + 0.06 * pop})`,
        }}
      >
        {page.tokens.map((t, i) => {
          const on = now >= t.fromMs && now < t.toMs;
          return (
            <span key={i} style={{ whiteSpace: "pre", color: on ? C.roseLight : C.cream, textShadow: on ? `0 0 22px rgba(232,96,60,0.55), 0 3px 14px rgba(0,0,0,0.55)` : undefined }}>
              {t.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const HookCard: React.FC<{ kicker: string; text: string; frames: number; y: number }> = ({ kicker, text, frames, y }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 18 }, durationInFrames: 14 });
  const exit = interpolate(frame, [frames - 8, frames], [1, 0], clamp);
  const line = interpolate(frame, [5, 20], [0, 1], clamp);
  const size = text.replace(/\*/g, "").length > 46 ? 64 : 76;
  return (
    <AbsoluteFill style={{ top: y, bottom: undefined, height: "auto", alignItems: "center" }}>
      <div
        style={{
          background: "rgba(16,12,11,0.74)",
          backdropFilter: "blur(14px)",
          border: `1.5px solid rgba(217,165,150,0.45)`,
          maxWidth: "86%",
          padding: "30px 48px 38px",
          borderRadius: 30,
          boxShadow: "0 24px 60px rgba(0,0,0,0.40)",
          transform: `translateY(${(1 - enter) * -36}px) scale(${0.96 + 0.04 * enter})`,
          opacity: Math.min(enter, exit),
          textAlign: "center",
        }}
      >
        <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 24, letterSpacing: "0.26em", color: C.rose, textTransform: "uppercase" }}>{kicker}</div>
        <div style={{ height: 3, borderRadius: 2, background: GRAD, width: `${line * 130}px`, margin: "16px auto 14px" }} />
        <div style={{ fontFamily: SERIF, fontStyle: "italic", fontWeight: 700, fontSize: size, lineHeight: 1.06, color: C.cream }}>
          <Rich text={text} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Callout: React.FC<{ text: string; frames: number; y: number }> = ({ text, frames, y }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 20 }, durationInFrames: 12 });
  const exit = interpolate(frame, [frames - 7, frames], [1, 0], clamp);
  const fontSize = Math.min(50, Math.floor(760 / (text.length * 0.56)));
  return (
    <AbsoluteFill style={{ top: y, left: 64, width: 900, bottom: undefined, height: "auto", alignItems: "flex-start" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          background: "rgba(246,236,230,0.96)",
          color: C.ink,
          borderRadius: 999,
          padding: "18px 34px 18px 22px",
          boxShadow: "0 16px 44px rgba(0,0,0,0.32)",
          transform: `translateX(${(1 - enter) * -50}px)`,
          opacity: Math.min(enter, exit),
        }}
      >
        <div style={{ width: 18, height: 18, borderRadius: 9, background: GRAD, boxShadow: `0 0 14px ${C.fenix}` }} />
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize, lineHeight: 1.1, letterSpacing: "-0.01em" }}>{text}</div>
      </div>
    </AbsoluteFill>
  );
};

// Etapas do Metodo Fenix: trilha de chips, a etapa atual acende em gradiente
const Etapas: React.FC<{ etapas: { text: string; at: number }[]; frames: number; y: number }> = ({ etapas, frames, y }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const o = Math.min(interpolate(frame, [0, 10], [0, 1], clamp), interpolate(frame, [frames - 8, frames], [1, 0], clamp));
  let ativa = 0;
  etapas.forEach((e, k) => {
    if (frame >= e.at) ativa = k;
  });
  return (
    <AbsoluteFill style={{ top: y, left: 50, width: 980, bottom: undefined, height: "auto", opacity: o }}>
      <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 19, letterSpacing: "0.3em", color: C.rose, textTransform: "uppercase", marginBottom: 10, textShadow: "0 2px 8px rgba(0,0,0,0.6)" }}>
        Método Fênix
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", width: 980 }}>
        {etapas.map((e, k) => {
          const on = k === ativa;
          const vis = spring({ frame: frame - e.at, fps, config: { damping: 18 }, durationInFrames: 10 });
          return (
            <div
              key={k}
              style={{
                fontFamily: SANS,
                fontWeight: 800,
                fontSize: Math.max(19, Math.min(26, Math.floor(820 / Math.max(1, etapas.reduce((n, x) => n + x.text.length + 4, 0)) * 1.7))),
                padding: "10px 16px",
                whiteSpace: "nowrap",
                borderRadius: 999,
                color: on ? C.dark : C.cream,
                background: on ? GRAD : "rgba(16,12,11,0.55)",
                border: on ? "none" : "1.5px solid rgba(217,165,150,0.4)",
                opacity: frame >= e.at ? vis : 0.35,
                transform: `scale(${on ? 1.04 : 1})`,
              }}
            >
              {String(k + 1).padStart(2, "0")} {e.text}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const LowerThird: React.FC<{ nome: string; linha: string; registro?: string; frames: number }> = ({ nome, linha, registro, frames }) => {
  const frame = useCurrentFrame();
  const { fps, height: H } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 20 }, durationInFrames: 14 });
  const exit = interpolate(frame, [frames - 8, frames], [1, 0], clamp);
  const bar = interpolate(frame, [4, 18], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ top: Math.round(H * 0.105), left: 60, bottom: undefined, height: "auto", alignItems: "flex-start", opacity: Math.min(enter, exit) }}>
      <div style={{ display: "flex", gap: 18, alignItems: "stretch", transform: `translateX(${(1 - enter) * -40}px)` }}>
        <div style={{ width: 4, borderRadius: 2, background: GRAD, transform: `scaleY(${bar})`, transformOrigin: "top" }} />
        <div style={{ background: "rgba(16,12,11,0.62)", backdropFilter: "blur(10px)", borderRadius: 18, padding: "16px 26px 18px" }}>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 50, color: C.cream, lineHeight: 1 }}>{nome}</div>
          <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 24, color: C.rose, letterSpacing: "0.08em", marginTop: 8 }}>{linha}</div>
          {registro ? <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 20, color: "rgba(246,236,230,0.75)", marginTop: 6 }}>{registro}</div> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Assinatura: React.FC<{ text: string; esconde?: number[] | null }> = ({ text, esconde }) => {
  const frame = useCurrentFrame();
  const { height: H } = useVideoConfig();
  let o = interpolate(frame, [0, 15], [0, 0.9], clamp);
  if (esconde) {
    const [a, b] = esconde;
    o *= Math.min(1, Math.max(interpolate(frame, [a - 8, a], [1, 0], clamp), interpolate(frame, [b, b + 10], [0, 1], clamp)));
  }
  return (
    <div style={{ position: "absolute", top: Math.round(H * 0.105), left: 60, display: "flex", alignItems: "center", gap: 12, opacity: o }}>
      <div
        style={{
          width: 50,
          height: 50,
          borderRadius: 25,
          border: `1.5px solid ${C.rose}`,
          display: "grid",
          placeItems: "center",
          fontFamily: SERIF,
          fontWeight: 700,
          fontSize: 22,
          color: C.rose,
          background: "rgba(16,12,11,0.45)",
        }}
      >
        AA
      </div>
      <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 22, color: C.cream, letterSpacing: "0.04em", textShadow: "0 2px 8px rgba(0,0,0,0.6)" }}>{text}</div>
    </div>
  );
};

const Aviso: React.FC<{ text: string }> = ({ text }) => {
  const { height: H } = useVideoConfig();
  return (
    <div
      style={{
        position: "absolute",
        left: 40,
        right: 40,
        top: H - 128,
        padding: "12px 22px",
        borderRadius: 14,
        background: "rgba(16,12,11,0.62)",
        fontFamily: SANS,
        fontWeight: 500,
        fontSize: 21,
        lineHeight: 1.3,
        color: "rgba(246,236,230,0.92)",
        textAlign: "center",
      }}
    >
      {text}
    </div>
  );
};

const EndCard: React.FC<{ title: string; subtitle: string; instagram?: string; whatsapp?: string; registro?: string }> = ({
  title,
  subtitle,
  instagram,
  whatsapp,
  registro,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const bg = interpolate(frame, [0, 10], [0, 1], clamp);
  const mark = spring({ frame: frame - 4, fps, config: { damping: 16 }, durationInFrames: 16 });
  const txt = interpolate(frame, [14, 26], [0, 1], clamp);
  const chip = spring({ frame: frame - 22, fps, config: { damping: 16 }, durationInFrames: 14 });
  const line = interpolate(frame, [10, 28], [0, 1], clamp);
  return (
    <AbsoluteFill
      style={{
        opacity: bg,
        justifyContent: "center",
        alignItems: "center",
        background: `radial-gradient(ellipse 80% 55% at 50% 38%, rgba(217,165,150,0.22), rgba(16,12,11,0) 70%), radial-gradient(ellipse 70% 40% at 50% 100%, rgba(232,96,60,0.18), rgba(16,12,11,0) 70%), ${C.dark}`,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: -60 }}>
        <div
          style={{
            width: 170,
            height: 170,
            borderRadius: 85,
            border: `2px solid ${C.rose}`,
            display: "grid",
            placeItems: "center",
            fontFamily: SERIF,
            fontWeight: 700,
            fontSize: 74,
            color: C.rose,
            opacity: mark,
            transform: `scale(${0.85 + 0.15 * mark})`,
            boxShadow: `0 0 60px rgba(217,165,150,0.25)`,
          }}
        >
          AA
        </div>
        <div style={{ height: 3, borderRadius: 2, background: GRAD, width: line * 170, margin: "40px 0 30px" }} />
        <div style={{ fontFamily: SERIF, fontStyle: "italic", fontWeight: 700, fontSize: 84, color: C.cream, textAlign: "center", lineHeight: 1.04, maxWidth: 900, opacity: txt }}>
          <Rich text={title} />
        </div>
        <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 32, color: C.rose, textAlign: "center", marginTop: 22, maxWidth: 820, opacity: txt }}>{subtitle}</div>
        {instagram || whatsapp ? (
          <div style={{ display: "flex", gap: 14, marginTop: 40, opacity: chip, transform: `translateY(${(1 - chip) * 20}px)`, flexWrap: "wrap", justifyContent: "center" }}>
            {whatsapp ? (
              <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 32, color: C.dark, background: GRAD, padding: "16px 30px", borderRadius: 999 }}>WhatsApp {whatsapp}</div>
            ) : null}
            {instagram ? (
              <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, color: C.cream, border: `1.5px solid ${C.rose}`, padding: "15px 28px", borderRadius: 999 }}>@{instagram}</div>
            ) : null}
          </div>
        ) : null}
        {registro ? <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 22, color: "rgba(246,236,230,0.6)", marginTop: 34, opacity: txt }}>{registro}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        height: 7,
        borderRadius: "0 4px 4px 0",
        width: `${(frame / Math.max(1, durationInFrames - 1)) * 100}%`,
        background: GRAD,
        boxShadow: `0 0 12px rgba(232,96,60,0.5)`,
      }}
    />
  );
};
