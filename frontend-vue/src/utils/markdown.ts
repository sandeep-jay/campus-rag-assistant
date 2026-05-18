import MarkdownIt from 'markdown-it'
import { normalizeAssistantContent } from './normalizeAssistantContent'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js/lib/core'

// Tree-shaken: only import languages actually used
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import bash from 'highlight.js/lib/languages/bash'
import sql from 'highlight.js/lib/languages/sql'
import json from 'highlight.js/lib/languages/json'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('shell', bash)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('json', json)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('css', css)

const md = new MarkdownIt({
  html: true, // allow raw HTML from LLM — DOMPurify will sanitize it below
  linkify: true,
  typographer: true,
  highlight: (str: string, lang: string): string => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
        return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`
      } catch {
        // fall through
      }
    }
    return `<pre><code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`
  },
})

/**
 * Renders markdown to sanitized HTML safe for use with v-html.
 *
 * SECURITY CONTRACT:
 * - This is the ONLY function that should ever produce content for v-html.
 * - html: true lets markdown-it pass through raw HTML from LLM output.
 * - DOMPurify then strips ALL dangerous tags, attributes, and protocols.
 * - Only an explicit allowlist of tags and attributes passes through.
 * - LLM output MUST always pass through this function before being rendered.
 */
export function renderMarkdown(raw: string): string {
  const rendered = md.render(normalizeAssistantContent(raw))

  return DOMPurify.sanitize(rendered, {
    ALLOWED_TAGS: [
      'p', 'strong', 'em', 'b', 'i', 'u', 's',
      'ul', 'ol', 'li',
      'code', 'pre',
      'blockquote',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'br', 'hr',
      'span', 'div', 'a',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
    ],
    ALLOWED_ATTR: ['class', 'href', 'rel', 'target'],
    FORBID_ATTR: ['style', 'onerror', 'onclick', 'onload', 'src', 'action'],
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input', 'link', 'meta'],
    ALLOWED_URI_REGEXP: /^https?:/i,
  })
}
