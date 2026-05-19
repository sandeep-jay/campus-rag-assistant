/**
 * Light cleanup of assistant markdown before render (no structural rewriting).
 */

const MAX_LEAKED_QUESTION_WORDS = 35

/** Drop leading condensed question echoed before the real answer. */
function stripLeadingCondensedQuestion(text: string): string {
  const stripped = text.trim()
  if (!stripped) return stripped

  const dashMatch = stripped.match(/^(.+\?)\s*[\u2014\u2013-]+\s*([\s\S]+)$/u)
  if (dashMatch && dashMatch[1].split(/\s+/).length <= MAX_LEAKED_QUESTION_WORDS) {
    return dashMatch[2].trim()
  }

  const capMatch = stripped.match(/^(.+\?)\s+([A-Z][\s\S]+)$/)
  if (capMatch && capMatch[1].split(/\s+/).length <= MAX_LEAKED_QUESTION_WORDS) {
    return capMatch[2].trim()
  }

  const parts = stripped.split(/(?<=[.!?])\s+/)
  if (parts.length >= 2 && parts[0].trim().endsWith('?')) {
    const first = parts[0].trim()
    if (first.split(/\s+/).length <= MAX_LEAKED_QUESTION_WORDS) {
      return parts.slice(1).join(' ').trim()
    }
  }
  return stripped
}

function dropLine(line: string): boolean {
  const s = line.trim()
  if (!s) return false
  return (
    /^\s*Human\b/i.test(s) ||
    /^\s*Assistant\b/i.test(s) ||
    /^\s*Question\s*:/i.test(s) ||
    /^\s*Standalone Question/i.test(s) ||
    /^\s*Input\s*:/i.test(s) ||
    /^\s*Output\s*:/i.test(s) ||
    /^\s*Human the\s*:/i.test(s) ||
    /^\s*kb_url\s*:/i.test(s) ||
    /^\s*kb_number\s*:/i.test(s) ||
    /^\s*References\s*:/i.test(s) ||
    /^\s*\*\*References/i.test(s) ||
    /^\s*\[URL:/i.test(s) ||
    /^\s*\*\*Article\s*:\*\*\s*KB/i.test(s) ||
    /^\s*Article\s*:\s*KB/i.test(s) ||
    /^\[.*'.*'.*\]\s*$/.test(s) ||
    /^\['/.test(s) ||
    /^\[\s*'/.test(s)
  )
}

function promoteBoldHeadings(text: string): string {
  return text
    .split('\n')
    .map((line) => {
      const stripped = line.trim()
      const m = stripped.match(/^\*\*(.+)\*\*\s*$/)
      if (!m) return line
      const inner = m[1].trim()
      if (inner.endsWith(':')) return line
      return `## ${inner}`
    })
    .join('\n')
}

export function normalizeAssistantContent(raw: string): string {
  if (!raw) return raw

  let text = stripLeadingCondensedQuestion(raw)
    .split('\n')
    .filter((line) => !dropLine(line))
    .join('\n')
    .trim()

  text = text.replace(/(?<!\n)(\d+)\.\s+/g, '\n$1. ')
  text = promoteBoldHeadings(text.replace(/^\n+/, ''))

  return text.replace(/\n{3,}/g, '\n\n').trim()
}
