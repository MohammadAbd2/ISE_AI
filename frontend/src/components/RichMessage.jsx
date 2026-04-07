import { useState } from "react";

function tokenizeLine(line) {
  const pattern =
    /(#[^\n]*|\/\/[^\n]*|"(?:\\.|[^"])*"|'(?:\\.|[^'])*'|`(?:\\.|[^`])*`|\b(?:const|let|var|function|return|if|else|for|while|switch|case|break|continue|try|catch|finally|class|new|import|from|export|default|async|await|def|pass|raise|yield|lambda|None|True|False|null|true|false|public|private|protected|static|using|namespace|string|int|bool|void|Console|print)\b|\b\d+(?:\.\d+)?\b)/g;

  const pieces = [];
  let lastIndex = 0;
  let match;
  while ((match = pattern.exec(line)) !== null) {
    if (match.index > lastIndex) {
      pieces.push({ type: "plain", value: line.slice(lastIndex, match.index) });
    }
    const token = match[0];
    let type = "plain";
    if (token.startsWith("#") || token.startsWith("//")) {
      type = "comment";
    } else if (
      token.startsWith("\"") ||
      token.startsWith("'") ||
      token.startsWith("`")
    ) {
      type = "string";
    } else if (/^\d/.test(token)) {
      type = "number";
    } else {
      type = "keyword";
    }
    pieces.push({ type, value: token });
    lastIndex = pattern.lastIndex;
  }
  if (lastIndex < line.length) {
    pieces.push({ type: "plain", value: line.slice(lastIndex) });
  }
  return pieces;
}

function CodeBlock({ language, code }) {
  const lines = code.replace(/\n$/, "").split("\n");
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = code;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="code-shell">
      <div className="code-shell-header">
        <div className="code-shell-lights">
          <span />
          <span />
          <span />
        </div>
        <div className="code-shell-language">{language || "text"}</div>
        <button
          type="button"
          className="code-copy-button"
          onClick={handleCopy}
          title="Copy code"
        >
          {copied ? "✓ Copied" : "📋 Copy"}
        </button>
      </div>
      <pre className="code-shell-body">
        <code>
          {lines.map((line, index) => (
            <div key={`${index}-${line}`} className="code-line">
              <span className="code-line-number">{index + 1}</span>
              <span className="code-line-content">
                {tokenizeLine(line).map((piece, pieceIndex) => (
                  <span
                    key={`${pieceIndex}-${piece.value}`}
                    className={`token-${piece.type}`}
                  >
                    {piece.value}
                  </span>
                ))}
              </span>
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
}

function TextBlock({ content }) {
  const paragraphs = content
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  // Parse markdown images and links
  function parseMarkdown(text) {
    const parts = [];
    const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const boldRegex = /\*\*([^*]+)\*\*/g;
    const italicRegex = /\*([^*]+)\*/g;
    
    let lastIndex = 0;
    let match;
    const tempRegex = /!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
    
    while ((match = tempRegex.exec(text)) !== null) {
      // Add text before match
      if (match.index > lastIndex) {
        parts.push({ type: 'text', value: text.slice(lastIndex, match.index) });
      }
      
      // Image match
      if (match[1] !== undefined) {
        parts.push({ type: 'image', alt: match[1], src: match[2] });
      }
      // Link match
      else if (match[3] !== undefined) {
        parts.push({ type: 'link', text: match[3], href: match[4] });
      }
      // Bold match
      else if (match[5] !== undefined) {
        parts.push({ type: 'bold', value: match[5] });
      }
      // Italic match
      else if (match[6] !== undefined) {
        parts.push({ type: 'italic', value: match[6] });
      }
      
      lastIndex = tempRegex.lastIndex;
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
      parts.push({ type: 'text', value: text.slice(lastIndex) });
    }
    
    return parts;
  }

  return paragraphs.map((paragraph, index) => {
    const lines = paragraph.split("\n");
    const hasImage = /!\[([^\]]*)\]\(([^)]+)\)/.test(lines[0]);
    
    if (hasImage) {
      // If first line has an image, render it specially
      const firstLine = lines[0];
      const match = firstLine.match(/!\[([^\]]*)\]\(([^)]+)\)/);
      if (match) {
        return (
          <div key={`${index}-img`} className="rich-paragraph-with-image">
            <img 
              src={match[2]} 
              alt={match[1]} 
              className="inline-image"
              style={{ maxWidth: '100%', maxHeight: '400px', borderRadius: '8px', margin: '10px 0' }}
            />
            <p className="rich-paragraph">
              {lines.map((line, lineIndex) => {
                if (lineIndex === 0) {
                  // Skip the image markdown on first line, show remaining text
                  const remaining = line.replace(/!\[([^\]]*)\]\(([^)]+)\)/, '').trim();
                  return remaining ? (
                    <span key={`${lineIndex}-${remaining}`}>
                      {remaining}
                      {lineIndex < lines.length - 1 ? <br /> : null}
                    </span>
                  ) : null;
                }
                return (
                  <span key={`${lineIndex}-${line}`}>
                    {line}
                    {lineIndex < lines.length - 1 ? <br /> : null}
                  </span>
                );
              })}
            </p>
          </div>
        );
      }
    }
    
    // Regular text block
    return (
      <p key={`${index}-${paragraph.slice(0, 16)}`} className="rich-paragraph">
        {lines.map((line, lineIndex) => {
          const parts = parseMarkdown(line);
          return (
            <span key={`${lineIndex}-${line}`}>
              {parts.map((part, partIndex) => {
                if (part.type === 'text') {
                  return <span key={`${partIndex}-text`}>{part.value}</span>;
                } else if (part.type === 'image') {
                  return (
                    <img 
                      key={`${partIndex}-img`}
                      src={part.src} 
                      alt={part.alt}
                      className="inline-image"
                      style={{ maxWidth: '100%', maxHeight: '300px', borderRadius: '8px', margin: '5px 0' }}
                    />
                  );
                } else if (part.type === 'link') {
                  return (
                    <a key={`${partIndex}-link`} href={part.href} target="_blank" rel="noopener noreferrer">
                      {part.text}
                    </a>
                  );
                } else if (part.type === 'bold') {
                  return <strong key={`${partIndex}-bold`}>{part.value}</strong>;
                } else if (part.type === 'italic') {
                  return <em key={`${partIndex}-italic`}>{part.value}</em>;
                }
                return null;
              })}
              {lineIndex < lines.length - 1 ? <br /> : null}
            </span>
          );
        })}
      </p>
    );
  });
}

function GeneratedImage({ imageBase64, prompt, width, height }) {
  const imageUrl = `data:image/png;base64,${imageBase64}`;
  const [showPreview, setShowPreview] = useState(false);

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = imageUrl;
    link.download = `generated-image-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleOpenPreview = () => {
    setShowPreview(true);
  };

  const handleClosePreview = () => {
    setShowPreview(false);
  };

  return (
    <div className="generated-image-container">
      <div className="generated-image-card">
        <div className="generated-image-header">
          <span className="generated-image-badge">🎨 Generated Image</span>
          <span className="generated-image-info">{width}×{height}</span>
        </div>
        <div className="generated-image-wrapper">
          <img
            src={imageUrl}
            alt={prompt || "Generated image"}
            className="generated-image"
            loading="lazy"
          />
        </div>
        <div className="generated-image-actions">
          <button
            type="button"
            className="image-action-button preview"
            onClick={handleOpenPreview}
          >
            👁 Preview
          </button>
          <button
            type="button"
            className="image-action-button download"
            onClick={handleDownload}
          >
            ⬇ Download
          </button>
        </div>
        {prompt ? (
          <p className="generated-image-prompt">
            <strong>Prompt:</strong> {prompt}
          </p>
        ) : null}
      </div>

      {showPreview && (
        <div className="image-preview-overlay" onClick={handleClosePreview}>
          <div className="image-preview-modal" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="image-preview-close"
              onClick={handleClosePreview}
            >
              ✕
            </button>
            <img
              src={imageUrl}
              alt="Preview"
              className="image-preview-full"
            />
            <div className="image-preview-actions">
              <button
                type="button"
                className="image-action-button download"
                onClick={handleDownload}
              >
                ⬇ Download Full Size
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RichMessage({ content }) {
  const segments = [];
  const regex = /```(\w+)?\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  // Check for generated image metadata in the content
  // Format: [IMAGE_DATA:base64|width:512|height:512|prompt:text]
  const imageRegex = /\[IMAGE_DATA:([A-Za-z0-9+/=]+)\|width:(\d+)\|height:(\d+)\|prompt:([^\]]*)\]/;
  const imageMatch = content.match(imageRegex);
  
  // Remove image metadata from content for display
  const textContent = imageMatch ? content.replace(imageMatch[0], "").trim() : content;

  while ((match = regex.exec(textContent)) !== null) {
    if (match.index > lastIndex) {
      segments.push({
        type: "text",
        content: textContent.slice(lastIndex, match.index),
      });
    }
    segments.push({
      type: "code",
      language: match[1] || "text",
      content: match[2],
    });
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < textContent.length) {
    segments.push({
      type: "text",
      content: textContent.slice(lastIndex),
    });
  }

  return (
    <div className="rich-message">
      {imageMatch ? (
        <GeneratedImage
          imageBase64={imageMatch[1]}
          width={parseInt(imageMatch[2], 10)}
          height={parseInt(imageMatch[3], 10)}
          prompt={imageMatch[4]}
        />
      ) : null}
      {segments.length === 0 ? (
        <TextBlock content={content} />
      ) : (
        segments.map((segment, index) =>
          segment.type === "code" ? (
            <CodeBlock
              key={`${index}-${segment.language}`}
              language={segment.language}
              code={segment.content}
            />
          ) : (
            <TextBlock key={`${index}-${segment.content.slice(0, 16)}`} content={segment.content} />
          ),
        )
      )}
    </div>
  );
}
