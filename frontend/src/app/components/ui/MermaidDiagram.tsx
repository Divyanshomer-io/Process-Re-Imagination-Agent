import { useState, useMemo, useEffect } from "react";
import mermaid from "mermaid";

function sanitizeMermaidCode(raw: string): string {
  let code = raw.trim();
  if (code.startsWith("<") && code.includes("<![CDATA[")) {
    const match = code.match(/<!\[CDATA\[([\s\S]*?)\]\]>/);
    if (match) code = match[1].trim();
  }
  code = code.replace(/^```(?:mermaid)?\s*/i, "").replace(/\s*```$/, "");
  code = code.replace(/<!\[CDATA\[/g, "").replace(/\]\]>/g, "");
  code = code.replace(/\{\{([^}]*)\}[\])](?!\})/g, "{{$1}}");
  code = code.replace(/\[\[([^\]]*)\][\}>)]/g, "[[$1]]");
  code = code.replace(/\[\[([^\]]*?\([^\]]*?)\]\]/g, (_m, content) => {
    const c = content.replace(/^"|"$/g, "");
    return `[["${c}"]]`;
  });
  code = code.replace(/\{\{([^}]*?\([^}]*?)\}\}/g, (_m, content) => {
    const c = content.replace(/^"|"$/g, "");
    return `{{"${c}"}}`;
  });
  code = code.replace(/\|([^|]*?)&([^|]*?)\|/g, (_m, a, b) => `|${a} and ${b}|`);
  code = code.replace(/&/g, " and ");
  // Fix malformed }}] (stray ] after diamond)
  code = code.replace(/\}\}\]/g, "}}");
  // Fix missing arrow: node]    NodeId or node}}    NodeId -> insert -->
  code = code.replace(/([\]\}])\s{2,}([A-Za-z_][A-Za-z0-9_]*)/g, "$1 --> $2");
  return code;
}

let mermaidInitialized = false;
function ensureMermaid() {
  if (mermaidInitialized) return;
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: "default",
    flowchart: { useMaxWidth: true, htmlLabels: true },
    maxTextSize: 500000,
    maxEdges: 5000,
  });
  mermaidInitialized = true;
}

export function MermaidDiagram({ code }: { code: string }) {
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string | null>(null);

  const sanitized = useMemo(() => sanitizeMermaidCode(code), [code]);

  useEffect(() => {
    setError(null);
    setSvg(null);
    if (!code?.trim()) return;
    // #region agent log
    const _log=(msg: string, d: Record<string, unknown>)=>{fetch('http://127.0.0.1:7619/ingest/0f8b9f3f-e807-4ec2-85bf-777064a112f6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'d79ac4'},body:JSON.stringify({sessionId:'d79ac4',location:'MermaidDiagram.tsx',message:msg,data:d,hypothesisId:'H3,H4',timestamp:Date.now()})}).catch(()=>{});};
    _log('MermaidDiagram mount',{codeLen:code?.length,sanitizedLen:sanitized?.length,codePreview:(code||'').slice(0,120),looksLikeXml:(code||'').trim().startsWith('<')});
    // #endregion
    ensureMermaid();
    const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2)}`;

    mermaid
      .render(id, sanitized)
      .then(({ svg: s }) => {
        // #region agent log
        _log('MermaidDiagram render success',{svgLen:s?.length});
        // #endregion
        setSvg(s);
      })
      .catch((err) => {
        // #region agent log
        _log('MermaidDiagram render failed',{error:err?.message||String(err)});
        // #endregion
        console.error("[MermaidDiagram] render failed:", err);
        setError(err?.message || String(err));
      });
  }, [sanitized, code]);

  if (!code?.trim()) return null;

  if (error) {
    return (
      <div className="w-full">
        <div
          style={{
            padding: "0.75rem 1rem",
            marginBottom: "0.75rem",
            background: "#fff3cd",
            border: "1px solid #ffc107",
            borderRadius: "0.375rem",
            color: "#856404",
            fontSize: "0.875rem",
          }}
        >
          Diagram rendering failed: {error}
        </div>
        <pre
          className="w-full overflow-auto p-4 rounded-md bg-muted text-sm font-mono"
          style={{ whiteSpace: "pre-wrap" }}
        >
          {code}
        </pre>
      </div>
    );
  }

  if (svg) {
    return (
      <div
        className="w-full overflow-auto [&_svg]:max-w-full"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    );
  }

  return (
    <div className="w-full min-h-[200px] flex items-center justify-center text-muted-foreground">
      Rendering diagram…
    </div>
  );
}
