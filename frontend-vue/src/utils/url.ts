/**
 * Validates that a URL uses a safe protocol (http or https only).
 * Protects against javascript:, data:, vbscript: and other dangerous URI schemes.
 * All URLs rendered as <a href> in SourcesPanel must pass this check.
 */
export function isSafeUrl(url: string): boolean {
  if (!url) return false
  return /^https?:\/\//i.test(url)
}
