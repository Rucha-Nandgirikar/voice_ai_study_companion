import React, { useEffect, useMemo, useRef } from "react";

type Props = {
  title: string;
  getData: () => Uint8Array | undefined;
  color: string;
};

function drawBars(ctx: CanvasRenderingContext2D, data: Uint8Array, color: string) {
  const { width, height } = ctx.canvas;
  ctx.clearRect(0, 0, width, height);

  // Background
  ctx.fillStyle = "#0b1220";
  ctx.fillRect(0, 0, width, height);

  const bars = 32;
  const step = Math.floor(data.length / bars) || 1;
  const barW = width / bars;

  ctx.fillStyle = color;
  for (let i = 0; i < bars; i++) {
    const idx = i * step;
    const v = data[idx] / 255; // 0..1
    const h = Math.max(2, v * (height - 16));
    const x = i * barW + 2;
    const y = height - h - 8;
    ctx.fillRect(x, y, barW - 4, h);
  }
}

export function SpectrumCanvas({ title, getData, color }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const loop = () => {
      const d = getData();
      if (d && d.length) {
        drawBars(ctx, d, color);
      } else {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.fillStyle = "#0b1220";
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.fillStyle = "#94a3b8";
        ctx.font = "12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
        ctx.fillText("No data yet", 10, 18);
      }
      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [getData, color]);

  return (
    <div>
      <div style={{ fontSize: 12, fontWeight: 800, marginBottom: 6 }}>{title}</div>
      <canvas
        ref={canvasRef}
        width={360}
        height={90}
        style={{ width: "100%", height: 90, borderRadius: 10, border: "1px solid #e2e8f0" }}
      />
    </div>
  );
}


