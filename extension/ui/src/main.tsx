import React from "react";
import ReactDOM from "react-dom/client";
import { SidePanelApp } from "./sidepanel/SidePanelApp";
import "./styles.css";

// Chrome MV3 extension pages disallow blob: in script-src, which breaks SDKs that
// create inline AudioWorklet modules via Blob URLs. Instead of intercepting all
// JS blobs (too broad), we ONLY intercept AudioWorklet.addModule(blob:...).
(() => {
  const workletUrl = chrome?.runtime?.getURL?.("worklets/elevenlabs-worklets.js");
  if (!workletUrl) return;
  const libsamplerateUrl = chrome?.runtime?.getURL?.("worklets/libsamplerate.worklet.js");
  const originalAddModule = AudioWorklet.prototype.addModule;
  // eslint-disable-next-line no-extend-native
  AudioWorklet.prototype.addModule = function (moduleURL: any, options?: any) {
    try {
      if (typeof moduleURL === "string" && moduleURL.startsWith("blob:")) {
        return originalAddModule.call(this, workletUrl, options);
      }
      // ElevenLabs SDK sometimes loads this from a CDN; extension CSP can block it.
      if (
        typeof moduleURL === "string" &&
        moduleURL.includes("@alexanderolsen/libsamplerate-js") &&
        libsamplerateUrl
      ) {
        return originalAddModule.call(this, libsamplerateUrl, options);
      }
    } catch {
      // ignore and fall back to original
    }
    return originalAddModule.call(this, moduleURL, options);
  };
})();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <SidePanelApp />
  </React.StrictMode>
);


