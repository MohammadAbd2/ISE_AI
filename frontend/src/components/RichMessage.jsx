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

  return (
    <div className="code-shell">
      <div className="code-shell-header">
        <div className="code-shell-lights">
          <span />
          <span />
          <span />
        </div>
        <div className="code-shell-language">{language || "text"}</div>
      </div>
      <pre className="code-shell-body">
        <code>
          {lines.map((line, index) => (
            <span key={`${index}-${line}`} className="code-line">
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
            </span>
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

  return paragraphs.map((paragraph, index) => (
    <p key={`${index}-${paragraph.slice(0, 16)}`} className="rich-paragraph">
      {paragraph.split("\n").map((line, lineIndex) => (
        <span key={`${lineIndex}-${line}`}>
          {line}
          {lineIndex < paragraph.split("\n").length - 1 ? <br /> : null}
        </span>
      ))}
    </p>
  ));
}

export default function RichMessage({ content }) {
  const segments = [];
  const regex = /```(\w+)?\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push({
        type: "text",
        content: content.slice(lastIndex, match.index),
      });
    }
    segments.push({
      type: "code",
      language: match[1] || "text",
      content: match[2],
    });
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < content.length) {
    segments.push({
      type: "text",
      content: content.slice(lastIndex),
    });
  }

  return (
    <div className="rich-message">
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
