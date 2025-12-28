import React, { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

type Props = {
  agentId: string;
};

export function ElevenLabsConvaiPortal({ agentId }: Props) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  // Prefer a dedicated mount point (lets us "center" the widget in the UI).
  // Fall back to <body> to avoid CSS/stacking-context issues when needed.
  const root = document.getElementById("convai-root") ?? document.body;
  return createPortal(<elevenlabs-convai agent-id={agentId}></elevenlabs-convai>, root);
}






