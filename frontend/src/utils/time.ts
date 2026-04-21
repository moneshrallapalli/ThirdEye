/**
 * Parse a UTC timestamp string into a Date object.
 * The backend stores timestamps via datetime.utcnow() but without a trailing
 * "Z", so JavaScript's Date constructor treats them as local time.  This
 * helper appends "Z" when needed so the browser correctly interprets the
 * value as UTC and auto-converts to the user's local timezone.
 */
export function utcToDate(ts: string): Date {
  if (!ts) return new Date();
  // Already has timezone info — leave it alone
  if (ts.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(ts)) return new Date(ts);
  return new Date(ts + 'Z');
}
