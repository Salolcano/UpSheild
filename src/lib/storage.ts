// Safe localStorage helpers: storage can be empty or blocked, so every call is guarded.
export const store = {
  get(key: string): string | null {
    try { return localStorage.getItem(key); } catch { return null; }
  },
  set(key: string, value: string): void {
    try { localStorage.setItem(key, value); } catch { /* ignore */ }
  },
  del(key: string): void {
    try { localStorage.removeItem(key); } catch { /* ignore */ }
  },
};
export const KEYS = { localKey: "upshield.localKey", mode: "upshield.walletMode", theme: "theme" };
