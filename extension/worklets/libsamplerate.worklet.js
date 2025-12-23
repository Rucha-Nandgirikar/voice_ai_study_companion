// Minimal LibSampleRate shim for extension environments.
// ElevenLabs SDK conditionally loads libsamplerate.worklet.js from a CDN when
// sampleRate constraints are unavailable. Chrome extension CSP can block that
// network fetch, causing the voice session to disconnect.
//
// This shim provides the API surface the SDK worklet expects:
//   globalThis.LibSampleRate.create(channels, inRate, outRate) -> { full(samples) }
//
// For hackathon MVP, we use an identity "resampler" (no-op). Audio quality may
// be slightly impacted if input sample rates differ, but it prevents disconnects.

globalThis.LibSampleRate = {
  // eslint-disable-next-line no-unused-vars
  create: async (channels, inRate, outRate) => {
    return {
      // eslint-disable-next-line no-unused-vars
      full: (samples) => samples
    };
  }
};


