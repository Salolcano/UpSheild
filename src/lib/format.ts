export const PROVIDERS = ["github", "cloudflare", "discord", "vercel"] as const;
export const NAMES: Record<string, string> = { github: "GitHub", cloudflare: "Cloudflare", discord: "Discord", vercel: "Vercel" };
export const TAGS: Record<string, string> = { github: "Code hosting", cloudflare: "Network", discord: "Community", vercel: "Hosting" };

export const toWei = (gen: string): bigint => {
  const [w, f = ""] = gen.trim().split(".");
  return BigInt(w || "0") * 10n ** 18n + BigInt((f + "0".repeat(18)).slice(0, 18));
};
export const fromWei = (wei: bigint | string | number): string => {
  const n = BigInt(wei);
  const whole = n / 10n ** 18n;
  const frac = (n % 10n ** 18n).toString().padStart(18, "0").slice(0, 4).replace(/0+$/, "");
  return frac ? `${whole}.${frac}` : `${whole}`;
};
/** JSON.parse loses precision on wei-sized integers, so pull exact numbers out of the raw text. */
export const bigField = (raw: string, key: string): bigint => {
  const m = new RegExp(`"${key}":\\s*(\\d+)`).exec(raw);
  return m ? BigInt(m[1]) : 0n;
};
/** Renders a stored condition as readable text, e.g. "GitHub outage of 60+ minutes (single incident)". */
export const formatThreshold = (provider: string, minutes: number): string =>
  `${NAMES[provider] ?? provider} outage of ${minutes}+ minutes (single incident)`;

export type Quote = {
  id: string; requester: string; provider: string; threshold_minutes: number;
  coverage_start: string; coverage_end: string; risk_band: string; rationale: string;
  consumed: boolean; qualifying_incidents: number; history_span_days: number;
  start_ts: number; end_ts: number; quoted_at: number; valid_until: number;
  requested_payout: bigint; required_premium: bigint;
};
export type Policy = {
  id: string; quote_id: string; holder: string; provider: string; threshold_minutes: number;
  coverage_start: string; coverage_end: string; status: string; evidence_note: string;
  resolved_outage_minutes: number; premium: bigint; payout_amount: bigint; start_ts: number; end_ts: number;
};
export const parseQuote = (raw: string): Quote | null =>
  raw ? { ...JSON.parse(raw), requested_payout: bigField(raw, "requested_payout"), required_premium: bigField(raw, "required_premium") } : null;
export const parsePolicy = (raw: string): Policy | null =>
  raw ? { ...JSON.parse(raw), premium: bigField(raw, "premium"), payout_amount: bigField(raw, "payout_amount") } : null;
