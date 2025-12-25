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

  // Render directly under <body> to avoid CSS/stacking-context issues (e.g. backdrop-filter)
  // that can break fixed-position widgets when nested inside containers.
  if (!mounted) return null;
  return createPortal(<elevenlabs-convai agent-id={agentId}></elevenlabs-convai>, document.body);
}



