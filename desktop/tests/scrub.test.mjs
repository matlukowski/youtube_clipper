import test from 'node:test';
import assert from 'node:assert/strict';
import {createScrubPreview} from '../web/scrub.mjs';

function playerFixture(muted = false) {
  const calls = [];
  const player = {
    mute() { muted = true; calls.push(['mute']); },
    unMute() { muted = false; calls.push(['unMute']); },
    isMuted() { return muted; },
    playVideo() { calls.push(['play']); },
    pauseVideo() { calls.push(['pause']); },
    seekTo(time, fetch) { calls.push(['seek', time, fetch]); },
  };
  return {player, calls};
}

test('first slider movement loads a frame without a preceding user play', () => {
  const {player, calls} = playerFixture();
  const scrub = createScrubPreview(player);
  scrub.seek(111.36, false);
  assert.ok(calls.some(c => c[0] === 'play'), 'cued video must be primed to decode frames');
  assert.deepEqual(calls.find(c => c[0] === 'seek'), ['seek', 111.36, true]);
  assert.equal(player.isMuted(), true, 'initialization must be silent');
  assert.equal(calls.some(c => c[0] === 'pause'), false, 'do not pause before a frame can load');
  scrub.onStateChange(1);
  assert.ok(calls.some(c => c[0] === 'pause'), 'stop as soon as the frame is available');
  assert.equal(player.isMuted(), false, 'restore previous sound preference');
  scrub.cancel();
});

test('dragging during startup keeps the newest target, without restarting playback', () => {
  const {player, calls} = playerFixture(true);
  const scrub = createScrubPreview(player);
  scrub.seek(10, false); scrub.seek(20, false); scrub.seek(30, true);
  scrub.onStateChange(1);
  assert.equal(calls.filter(c => c[0] === 'play').length, 1);
  assert.deepEqual(calls.filter(c => c[0] === 'seek').at(-1), ['seek', 30, true]);
  assert.equal(player.isMuted(), true);
  scrub.cancel();
});

test('after playback, scrubbing fetches unbuffered frames while remaining paused', () => {
  const {player, calls} = playerFixture();
  const scrub = createScrubPreview(player);
  scrub.onStateChange(1);
  scrub.seek(140, false);
  assert.deepEqual(calls.find(c => c[0] === 'seek'), ['seek', 140, true]);
  assert.ok(calls.some(c => c[0] === 'pause'));
  assert.equal(calls.some(c => c[0] === 'play'), false);
  scrub.cancel();
});

test('release flushes the latest target and cancels an older scheduled seek', async () => {
  const {player, calls} = playerFixture();
  const scrub = createScrubPreview(player);
  scrub.onStateChange(1);
  scrub.seek(10, false); scrub.seek(20, false); scrub.seek(30, true);
  assert.deepEqual(calls.filter(c => c[0] === 'seek').map(c => c[1]), [10, 30]);
  await new Promise(resolve => setTimeout(resolve, 150));
  assert.deepEqual(calls.filter(c => c[0] === 'seek').map(c => c[1]), [10, 30]);
  scrub.cancel();
});

test('explicit playback cancels initialization and restores sound without a late pause', () => {
  const {player, calls} = playerFixture();
  const scrub = createScrubPreview(player);
  scrub.seek(40); scrub.cancel();
  assert.equal(player.isMuted(), false);
  const before = calls.length;
  scrub.onStateChange(1);
  assert.equal(calls.length, before);
  assert.equal(scrub.pending, false);
});
