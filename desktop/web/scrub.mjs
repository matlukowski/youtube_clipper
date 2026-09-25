// Adapter for paused frame previews, independently testable from DOM rendering.
export function createScrubPreview(player, {onBlocked = () => {}} = {}) {
  let primed = false, priming = false, target = 0, wasMuted = true;
  let timer = null, timeout = null, lastSeek = -Infinity;
  function restoreSound() { if (!wasMuted) player.unMute(); }
  function flush() {
    clearTimeout(timer); timer = null;
    player.pauseVideo();
    // true is necessary for live preview outside the already buffered range.
    player.seekTo(target, true);
    lastSeek = Date.now();
  }
  function cancel() {
    clearTimeout(timer); clearTimeout(timeout); timer = timeout = null;
    if (priming) { priming = false; player.pauseVideo(); restoreSound(); }
  }
  return {
    seek(time, final = true) {
      target = time;
      if (priming) return; // Decode once, then show the newest requested frame.
      if (!primed) {
        priming = true;
        wasMuted = player.isMuted();
        player.mute();
        player.seekTo(target, true);
        player.playVideo();
        timeout = setTimeout(() => { cancel(); onBlocked(); }, 12000);
        return;
      }
      const delay = 120 - (Date.now() - lastSeek);
      if (final || delay <= 0) flush();
      else if (timer === null) timer = setTimeout(flush, delay);
    },
    onStateChange(value) {
      if (value === 1) { // PLAYING confirms the decoder has started.
        primed = true;
        if (priming) {
          priming = false; clearTimeout(timeout); timeout = null;
          flush(); restoreSound();
        }
      } else if (value === 5 && !priming) primed = false;
    },
    cancel,
    get pending() { return priming || timer !== null; },
  };
}
