import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"

// Component overrides for chat / question-statement markdown. Tuned for
// short prose with frequent inline code, lists, and fenced code blocks.
const COMPONENTS: Components = {
  p: ({ children }) => (
    <p className="my-1.5 first:mt-0 last:mb-0 leading-relaxed">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="my-2 pl-5 list-disc space-y-0.5">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 pl-5 list-decimal space-y-0.5">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => (
    <h3 className="font-heading text-base font-semibold mt-3 mb-1">{children}</h3>
  ),
  h2: ({ children }) => (
    <h3 className="font-heading text-base font-semibold mt-3 mb-1">{children}</h3>
  ),
  h3: ({ children }) => (
    <h3 className="font-heading text-sm font-semibold mt-3 mb-1">{children}</h3>
  ),
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="underline underline-offset-2 hover:no-underline"
    >
      {children}
    </a>
  ),
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  // Pre wraps fenced code blocks. Descendant selector neutralizes the inline
  // pill styling on the inner <code> so we don't double-up backgrounds.
  pre: ({ children }) => (
    <pre className="my-2 p-3 rounded-lg overflow-x-auto bg-zinc-900 text-zinc-100 font-mono text-[12px] leading-relaxed [&_code]:bg-transparent [&_code]:p-0 [&_code]:rounded-none [&_code]:text-inherit">
      {children}
    </pre>
  ),
  code: ({ children, className }) => (
    <code
      className={`font-mono text-[0.92em] px-1 py-0.5 rounded bg-tint border border-line-accent/60 ${className ?? ""}`}
    >
      {children}
    </code>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 pl-3 border-l-2 border-line-accent text-text-muted">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-line" />,
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="text-sm border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-line px-2 py-1 text-left font-semibold">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border border-line px-2 py-1">{children}</td>
  ),
}

export function Markdown({ children }: { children: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTS}>{children}</ReactMarkdown>
}
