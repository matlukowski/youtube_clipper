export function parseTime(text) {
  const value = String(text).trim().replace(',', '.');
  if (!/^\d+(?::\d{1,2}){0,2}(?:\.\d{1,3})?$/.test(value)) return NaN;
  const parts = value.split(':').map(Number);
  if (parts.slice(1).some(n => n >= 60)) return NaN;
  return parts.reduce((total, n) => total * 60 + n, 0);
}
export function formatTime(seconds, decimals = true) {
  const centis = Math.max(0, Math.round((Number(seconds) || 0) * 100));
  const h = Math.floor(centis / 360000), m = Math.floor(centis / 6000) % 60, s = Math.floor(centis / 100) % 60;
  return (h ? `${h.toString().padStart(2, '0')}:` : '') + `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}` + (decimals ? `.${(centis % 100).toString().padStart(2, '0')}` : '');
}
export function rangeError(start, end, duration) {
  if (![start, end].every(Number.isFinite)) return 'Wpisz poprawny czas, np. 02:13.50.';
  if (start < 0 || end > duration + 0.001) return 'Fragment musi mieścić się w długości filmu.';
  if (end - start < 0.1 - 1e-8) return 'Koniec musi wypadać co najmniej 0,1 s po początku.';
  if (end - start > 600) return 'Jeden klip może mieć maksymalnie 10 minut.';
  return '';
}
export const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
export function initialStart(url, duration) {
  try {
    const u = new URL(url.startsWith('http') ? url : `https://${url}`);
    const t = u.searchParams.get('t') || u.searchParams.get('start') || '';
    let seconds = Number(t);
    if (!Number.isFinite(seconds)) {
      const m = t.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?$/);
      seconds = m ? Number(m[1] || 0) * 3600 + Number(m[2] || 0) * 60 + Number(m[3] || 0) : 0;
    }
    return clamp(seconds, 0, Math.max(0, duration - 0.1));
  } catch { return 0; }
}
