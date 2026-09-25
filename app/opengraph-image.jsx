import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#101728", color: "#f8f9ff", padding: "58px 66px", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 20, fontSize: 29, fontWeight: 700 }}><div style={{ width: 52, height: 52, borderRadius: 13, background: "#9d95fa", color: "#101728", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 31 }}>▶</div>YouTube Clipper</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}><div style={{ display: "flex", flexDirection: "column", fontSize: 80, fontWeight: 700, letterSpacing: -4, lineHeight: 1.08 }}><span>Zachowaj najlepszy</span><span style={{ display: "flex" }}>moment<span style={{ color: "#9d95fa" }}>.</span></span></div><div style={{ fontSize: 26, color: "#b9c4de" }}>Wycinaj fragmenty filmów z YouTube. Zapisuj MP4 na Windows.</div></div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "2px solid #33415e", paddingTop: 24, color: "#9d95fa", fontSize: 18, fontWeight: 700 }}><span>DARMOWA APLIKACJA NA WINDOWS</span><span>WERSJA 1.1.6</span></div>
    </div>,
    size
  );
}
