import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function parseDocumentation(markdown) {
  const lines = (markdown || "").split("\n");
  const blocks = [];
  const sections = [];
  let paragraph = [];
  let listItems = [];
  let codeLines = [];
  let codeLanguage = "";
  let inCodeBlock = false;

  function flushParagraph() {
    if (paragraph.length === 0) {
      return;
    }
    blocks.push({ type: "paragraph", content: paragraph.join(" ").trim() });
    paragraph = [];
  }

  function flushList() {
    if (listItems.length === 0) {
      return;
    }
    blocks.push({ type: "list", items: [...listItems] });
    listItems = [];
  }

  function flushCode() {
    if (!inCodeBlock) {
      return;
    }
    blocks.push({ type: "code", language: codeLanguage || "text", content: codeLines.join("\n") });
    codeLines = [];
    codeLanguage = "";
    inCodeBlock = false;
  }

  for (const rawLine of lines) {
    const line = rawLine.replace(/\r$/, "");

    if (line.startsWith("```")) {
      if (inCodeBlock) {
        flushCode();
      } else {
        flushParagraph();
        flushList();
        inCodeBlock = true;
        codeLanguage = line.slice(3).trim();
        codeLines = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      const level = headingMatch[1].length;
      const title = headingMatch[2].trim();
      const id = slugify(title);
      blocks.push({ type: "heading", level, content: title, id });
      if (level <= 2) {
        sections.push({ id, title, level });
      }
      continue;
    }

    const listMatch = line.match(/^\s*[-*]\s+(.*)$/);
    if (listMatch) {
      flushParagraph();
      listItems.push(listMatch[1].trim());
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }

    paragraph.push(line.trim());
  }

  flushParagraph();
  flushList();
  flushCode();

  return { blocks, sections };
}

function InlineMarkdown({ text }) {
  const parts = [];
  const pattern = /`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    if (match[1] !== undefined) {
      parts.push({ type: "code", value: match[1] });
    } else if (match[2] !== undefined) {
      parts.push({ type: "strong", value: match[2] });
    } else if (match[3] !== undefined) {
      parts.push({ type: "em", value: match[3] });
    }
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }

  return parts.map((part, index) => {
    if (part.type === "code") {
      return <code key={`${index}-${part.value}`}>{part.value}</code>;
    }
    if (part.type === "strong") {
      return <strong key={`${index}-${part.value}`}>{part.value}</strong>;
    }
    if (part.type === "em") {
      return <em key={`${index}-${part.value}`}>{part.value}</em>;
    }
    return <span key={`${index}-${part.value}`}>{part.value}</span>;
  });
}

export default function DocumentationView() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadDocumentation() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(api.developerHandbook);
        if (!response.ok) {
          throw new Error("Documentation could not be loaded.");
        }
        const text = await response.text();
        if (!cancelled) {
          setContent(text);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError.message || "Documentation could not be loaded.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDocumentation();
    return () => {
      cancelled = true;
    };
  }, []);

  const parsed = useMemo(() => parseDocumentation(content), [content]);

  return (
    <div className="documentation-view">
      <section className="documentation-hero panel">
        <div>
          <p className="eyebrow">Developer Reference</p>
          <h1>ISE AI Architecture and Extension Handbook</h1>
          <p className="documentation-lead">
            The canonical system reference for developers and for the agent itself when it needs grounded context
            about architecture, extension points, and self-improvement paths.
          </p>
        </div>
        <div className="documentation-hero-meta">
          <span className="panel-chip">Canonical docs</span>
          <span className="panel-chip">Agent-readable</span>
          <span className="panel-chip">API-oriented</span>
        </div>
      </section>

      {loading ? <div className="empty-state">Loading developer documentation...</div> : null}
      {error ? <div className="panel-error">{error}</div> : null}

      {!loading && !error ? (
        <div className="documentation-layout">
          <aside className="documentation-sidebar panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Contents</p>
                <h2>Sections</h2>
              </div>
            </div>
            <div className="documentation-toc">
              {parsed.sections.map((section) => (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  className={`documentation-toc-link level-${section.level}`}
                >
                  {section.title}
                </a>
              ))}
            </div>
          </aside>

          <section className="documentation-content panel">
            {parsed.blocks.map((block, index) => {
              if (block.type === "heading") {
                if (block.level === 1) {
                  return (
                    <h2 id={block.id} key={`${block.id}-${index}`} className="documentation-heading lead">
                      {block.content}
                    </h2>
                  );
                }
                if (block.level === 2) {
                  return (
                    <h3 id={block.id} key={`${block.id}-${index}`} className="documentation-heading">
                      {block.content}
                    </h3>
                  );
                }
                return (
                  <h4 id={block.id} key={`${block.id}-${index}`} className="documentation-subheading">
                    {block.content}
                  </h4>
                );
              }

              if (block.type === "list") {
                return (
                  <ul key={`list-${index}`} className="documentation-list">
                    {block.items.map((item) => (
                      <li key={item}>
                        <span className="documentation-list-icon">◆</span>
                        <span><InlineMarkdown text={item} /></span>
                      </li>
                    ))}
                  </ul>
                );
              }

              if (block.type === "code") {
                return (
                  <div key={`code-${index}`} className="documentation-code-shell">
                    <div className="documentation-code-header">{block.language}</div>
                    <pre>
                      <code>{block.content}</code>
                    </pre>
                  </div>
                );
              }

              return (
                <p key={`paragraph-${index}`} className="documentation-paragraph">
                  <InlineMarkdown text={block.content} />
                </p>
              );
            })}
          </section>
        </div>
      ) : null}
    </div>
  );
}
