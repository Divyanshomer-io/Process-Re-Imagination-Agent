import React, { useState, useEffect, useMemo } from "react";
import { Button } from "../ui/button";
import { toast } from "sonner";
import { Download, ZoomIn, ZoomOut, Maximize2, Copy, FileCode } from "lucide-react";
import { mockBlueprintXML } from "../../data/mockResults";
import { useResultsStore } from "../../data/apiResults";
import { renderMermaidToSvg, getMermaidLiveUrl } from "../../api/client";

/** Check if string is valid SVG (not HTML error page). */
function isSvg(s: string): boolean {
  const t = s.trim();
  return t.startsWith("<svg") && t.includes("</svg>");
}

/**
 * Sanitize LLM-generated Mermaid. Aggressive normalization: flowchart LRsubgraph,
 * direction removal (fixes direction_tb parse error), node labels, --> end.
 */
function sanitizeMermaid(raw: string): string {
  if (!raw?.trim()) return raw;
  let code = raw.trim();

  // 1. CRITICAL: Fix "flowchart LRsubgraph" — parser expects newline
  code = code.replace(
    /(flowchart|graph)\s+(LR|TB|BT|RL)\s*subgraph/gi,
    "$1 $2\nsubgraph"
  );

  // 2. CRITICAL: Remove direction TB/BT/LR/RL — causes "got 'direction_tb'" parse error
  code = code.replace(/^\s*direction\s+(TB|BT|LR|RL)\s*$/gm, "");

  // 3. Newline after %% comments before subgraph (avoid tokenization issues)
  code = code.replace(/%%([^\n]*)\n\s*subgraph/gi, "%%$1\n\nsubgraph");

  // 4. Simplify subgraph id["Label"] — use id [Label] to avoid quoted-form issues
  code = code.replace(/subgraph\s+(\w+)\["([^"]+)"\]/gi, 'subgraph $1 [$2]');

  // 5. Node labels with ( or ) must be quoted — fixes "got 'PS'" error
  code = code.replace(/(\w+)\s*\[\s*\[\s*([^"][^\]]*)\s*\]\s*\]/g, (_, id, label) =>
    /[()]/.test(label) ? `${id}[["${label.replace(/"/g, '\\"')}"]]` : `${id}[[${label}]]`
  );
  code = code.replace(/(\w+)\s*\(\s*\[\s*([^"][^\]]*)\s*\]\s*\)/g, (_, id, label) =>
    /[()]/.test(label) ? `${id}(["${label.replace(/"/g, '\\"')}"])` : `${id}([${label}])`
  );
  code = code.replace(/(\w+)\s*\[\s*([^"\[\]][^\]]*)\s*\]/g, (_, id, label) =>
    /[()]/.test(label) ? `${id}["${label.replace(/"/g, '\\"')}"]` : `${id}[${label}]`
  );

  // 6. Illegal connections: strip arrows pointing to end
  code = code.replace(/-->\s*end\b.*/gi, "");
  code = code.replace(/==>\s*end\b.*/gi, "");
  code = code.replace(/-->\s*\[end\]/gi, "");

  // 7. Closing tag: "end subgraph Name" → "end"
  code = code.replace(/end\s+subgraph\s+[\w[\]"_-]+/gi, "end");

  // 8. Keyword isolation: "end" on its own line
  code = code
    .split("\n")
    .map((l) => (l.trim() === "end" ? "end" : l))
    .join("\n");

  // 9. Dangling arrows: remove trailing --> or ==>
  code = code.replace(/\s*(?:-->|==>)\s*$/gm, "");

  // 10. Normalize blank lines
  code = code.replace(/\n{3,}/g, "\n\n").trim();
  return code;
}

export function ProcessBlueprintTab() {
  const [zoom, setZoom] = useState(100);
  const [viewMode, setViewMode] = useState<'svg' | 'xml' | 'mermaid'>('mermaid');

  const blueprintSVG = useResultsStore((s) => s.blueprintSVG);
  const blueprintMermaid = useResultsStore((s) => s.blueprintMermaid);
  const blueprintXMLStore = useResultsStore((s) => s.blueprintXML);
  const xmlContent = blueprintXMLStore || String(mockBlueprintXML);

  const mermaidFromXml = (() => {
    if (blueprintMermaid?.trim()) return '';
    const m = xmlContent.match(/<mermaid[^>]*>([\s\S]*?)<\/mermaid>/i);
    if (m) {
      const inner = m[1].trim();
      const cdata = inner.match(/<!\[CDATA\[([\s\S]*?)\]\]>/);
      return (cdata ? cdata[1] : inner).trim();
    }
    const d = xmlContent.match(/<Diagram[^>]*>\s*<\!\[CDATA\[([\s\S]*?)\]\]>\s*<\/Diagram>/i);
    return d ? d[1].trim() : '';
  })();
  const effectiveMermaid = (blueprintMermaid?.trim() || mermaidFromXml) ?? '';
  const sanitizedCode = useMemo(
    () => sanitizeMermaid(effectiveMermaid),
    [blueprintMermaid, mermaidFromXml]
  );
  const wasSanitized = effectiveMermaid.length > 0 && sanitizedCode !== effectiveMermaid;
  const hasSVG = blueprintSVG.trim().length > 0;
  const hasMermaid = effectiveMermaid.length > 0;
  const hasXML = xmlContent.trim().length > 0;
  const hasAnyContent = hasSVG || hasMermaid || hasXML;

  // Tiered render: mmdc → Kroki → Mermaid Live iframe
  const [renderedSvg, setRenderedSvg] = useState<string>("");
  const [mermaidLiveUrl, setMermaidLiveUrl] = useState<string>("");
  const [renderLoading, setRenderLoading] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);
  useEffect(() => {
    if (!hasMermaid || !sanitizedCode) {
      setRenderedSvg("");
      setMermaidLiveUrl("");
      setRenderError(null);
      return;
    }
    let cancelled = false;
    setRenderLoading(true);
    setRenderError(null);
    setRenderedSvg("");
    setMermaidLiveUrl("");
    renderMermaidToSvg(sanitizedCode)
      .then((result) => {
        if (cancelled) return undefined;
        const validSvg = result.svg && isSvg(result.svg);
        if (validSvg) {
          setRenderedSvg(result.svg!);
          setRenderError(null);
          setMermaidLiveUrl("");
          return undefined;
        }
        setRenderedSvg("");
        setRenderError(result.error ?? "Render failed");
        return getMermaidLiveUrl(sanitizedCode);
      })
      .then((url) => {
        if (cancelled || typeof url !== "string") return;
        setMermaidLiveUrl(url);
        toast.error("Process blueprint rendering failed.");
      })
      .catch((err) => {
        if (!cancelled) {
          setRenderedSvg("");
          setRenderError(err?.message || "Render failed");
          setMermaidLiveUrl("");
          toast.error("Process blueprint rendering failed.");
        }
      })
      .finally(() => {
        if (!cancelled) setRenderLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sanitizedCode, hasMermaid]);

  useEffect(() => {
    if (hasSVG) setViewMode('svg');
    else if (hasMermaid) setViewMode('mermaid');
    else if (hasXML) setViewMode('xml');
  }, [hasSVG, hasMermaid, hasXML]);
  // #region agent log
  useEffect(() => {
    fetch('http://127.0.0.1:7619/ingest/0f8b9f3f-e807-4ec2-85bf-777064a112f6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'d79ac4'},body:JSON.stringify({sessionId:'d79ac4',location:'ProcessBlueprintTab.tsx',message:'Blueprint tab state',data:{hasSVG,hasMermaid,hasXML,viewMode,mermaidLen:effectiveMermaid?.length||0,fromApi:!!blueprintMermaid?.trim(),fromXml:!!mermaidFromXml},hypothesisId:'H1,H2',timestamp:Date.now()})}).catch(()=>{});
  },[hasSVG,hasMermaid,hasXML,viewMode,effectiveMermaid,blueprintMermaid,mermaidFromXml]);
  // #endregion

  const handleDownload = () => {
    let content = '';
    let filename = 'process_blueprint';
    let mimeType = 'text/plain';

    if (viewMode === 'svg' && hasSVG) {
      content = blueprintSVG;
      filename += '.svg';
      mimeType = 'image/svg+xml';
    } else if (viewMode === 'mermaid' && hasMermaid) {
      content = sanitizedCode;
      filename += '.mmd';
    } else {
      content = xmlContent;
      filename += '.xml';
      mimeType = 'application/xml';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Blueprint downloaded as ${filename}`);
  };

  const handleCopy = () => {
    const content = viewMode === 'svg' ? blueprintSVG : viewMode === 'mermaid' ? sanitizedCode : xmlContent;
    navigator.clipboard.writeText(content);
    toast.success("Copied to clipboard");
  };

  const handleExportHtml = () => {
    let svgContent = '';
    if (hasSVG) {
      svgContent = blueprintSVG;
    } else if (hasMermaid && renderedSvg && isSvg(renderedSvg)) {
      svgContent = renderedSvg;
    } else if (hasMermaid && mermaidLiveUrl) {
      svgContent = `<iframe src="${mermaidLiveUrl}" title="Process Blueprint" style="width:100%;min-height:480px;border:none"></iframe>`;
    }
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Process Blueprint</title>
  <style>
    body { margin: 1rem; background: #fff; }
    svg { max-width: 100%; }
  </style>
</head>
<body>
${svgContent ? `<div>${svgContent}</div>` : `<pre style="white-space:pre-wrap;font-family:monospace">${xmlContent.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>`}
</body>
</html>`;
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "process_blueprint.html";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Exported as HTML");
  };

  if (!hasAnyContent) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <p>Process blueprint not yet generated. Please wait for the agent run to complete.</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2>Re-imagined Process Blueprint</h2>
          <p className="text-muted-foreground mt-2" style={{ fontSize: 'var(--text-label)' }}>
            AI-generated process architecture showing layered workflow with agentic components
          </p>
        </div>
        <div className="flex gap-2">
          {hasSVG && (
            <Button variant={viewMode === 'svg' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('svg')}>
              SVG
            </Button>
          )}
          {hasMermaid && (
            <Button variant={viewMode === 'mermaid' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('mermaid')}>
              Mermaid
            </Button>
          )}
          {hasXML && (
            <Button variant={viewMode === 'xml' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('xml')}>
              XML
            </Button>
          )}
          <div className="w-px bg-border mx-1" />
          <Button variant="outline" size="icon" onClick={() => setZoom(Math.max(25, zoom - 10))}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => setZoom(Math.min(300, zoom + 10))}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => setZoom(100)}>
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={handleCopy}>
            <Copy className="h-4 w-4 mr-2" />
            Copy
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownload}>
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
          {(hasSVG || hasMermaid) && (
            <Button variant="outline" size="sm" onClick={handleExportHtml}>
              <FileCode className="h-4 w-4 mr-2" />
              Export as HTML
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 border border-border rounded-[var(--radius)] overflow-auto bg-card">
        <div className="flex items-center justify-center min-h-full p-8">
          <div style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center', transition: 'transform 0.2s' }}>
            {viewMode === 'svg' && hasSVG ? (
              <div dangerouslySetInnerHTML={{ __html: blueprintSVG }} />
            ) : viewMode === 'mermaid' && hasMermaid ? (
              <>
                {wasSanitized && (
                  <div
                    className="w-full mb-3 px-4 py-2 rounded-md text-sm"
                    style={{
                      background: "#e8f4fc",
                      border: "1px solid #0ea5e9",
                      color: "#0369a1",
                    }}
                  >
                    Syntax Recovery Mode: Some LLM syntax errors were automatically corrected.
                  </div>
                )}
                {renderLoading ? (
                  <div className="text-muted-foreground py-12">Rendering diagram…</div>
                ) : renderedSvg && isSvg(renderedSvg) ? (
                  <div dangerouslySetInnerHTML={{ __html: renderedSvg }} style={{ maxWidth: "none" }} />
                ) : mermaidLiveUrl ? (
                  <div className="w-full space-y-4">
                    <iframe
                      src={mermaidLiveUrl}
                      title="Process Blueprint (Mermaid Live)"
                      sandbox="allow-scripts"
                      style={{ width: "100%", minHeight: 480, border: "none" }}
                    />
                    <details className="mt-4">
                      <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                        Show Mermaid Code
                      </summary>
                      <pre className="mt-2 whitespace-pre-wrap font-mono text-xs bg-muted p-4 rounded-[var(--radius)] overflow-auto max-h-96">
                        {sanitizedCode}
                      </pre>
                    </details>
                  </div>
                ) : (
                  <div className="w-full space-y-3">
                    {renderError && (
                      <div
                        className="px-4 py-2 rounded-md text-sm"
                        style={{
                          background: "#fef2f2",
                          border: "1px solid #ef4444",
                          color: "#991b1b",
                        }}
                      >
                        Diagram rendering failed: {renderError}
                      </div>
                    )}
                    <p className="text-muted-foreground text-sm">
                      Mermaid code is shown below. You can copy it and paste into{" "}
                      <a href="https://mermaid.live" target="_blank" rel="noopener noreferrer" className="underline">
                        mermaid.live
                      </a>{" "}
                      to visualize.
                    </p>
                    <pre className="whitespace-pre-wrap font-mono text-xs bg-muted p-4 rounded-[var(--radius)] overflow-auto max-h-[600px]">
                      {sanitizedCode}
                    </pre>
                  </div>
                )}
              </>
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-sm bg-muted p-6 rounded-[var(--radius)] max-w-4xl">
                {xmlContent}
              </pre>
            )}
          </div>
        </div>
      </div>

      <div className="bg-muted p-6 rounded-[var(--radius)]">
        <h4>Blueprint Overview</h4>
        <p className="text-muted-foreground mt-2" style={{ fontSize: 'var(--text-label)' }}>
          This diagram shows the re-imagined process with distinct layers:
        </p>
        <ul className="list-disc list-inside space-y-1 mt-4 text-muted-foreground" style={{ fontSize: 'var(--text-label)' }}>
          <li><strong>Communication Layer:</strong> External interfaces and input channels</li>
          <li><strong>Agentic Layer:</strong> AI agents handling intelligent automation</li>
          <li><strong>Process Layer:</strong> Core workflow steps with decision points and integrations</li>
        </ul>
      </div>
    </div>
  );
}
