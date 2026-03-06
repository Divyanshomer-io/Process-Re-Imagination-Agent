import { useState } from "react";
import { Button } from "../ui/button";
import { toast } from "sonner";
import { Download, ZoomIn, ZoomOut, Maximize2, Copy } from "lucide-react";
import { mockBlueprintXML } from "../../data/mockResults";
import { useResultsStore } from "../../data/apiResults";

export function ProcessBlueprintTab() {
  const [zoom, setZoom] = useState(100);
  const [viewMode, setViewMode] = useState<'svg' | 'xml' | 'mermaid'>('svg');

  const blueprintSVG = useResultsStore((s) => s.blueprintSVG);
  const blueprintMermaid = useResultsStore((s) => s.blueprintMermaid);
  const blueprintXMLStore = useResultsStore((s) => s.blueprintXML);
  const xmlContent = blueprintXMLStore || String(mockBlueprintXML);

  const hasSVG = blueprintSVG.trim().length > 0;
  const hasMermaid = blueprintMermaid.trim().length > 0;
  const hasXML = xmlContent.trim().length > 0;
  const hasAnyContent = hasSVG || hasMermaid || hasXML;

  const handleDownload = () => {
    let content = '';
    let filename = 'process_blueprint';
    let mimeType = 'text/plain';

    if (viewMode === 'svg' && hasSVG) {
      content = blueprintSVG;
      filename += '.svg';
      mimeType = 'image/svg+xml';
    } else if (viewMode === 'mermaid' && hasMermaid) {
      content = blueprintMermaid;
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
    const content = viewMode === 'svg' ? blueprintSVG : viewMode === 'mermaid' ? blueprintMermaid : xmlContent;
    navigator.clipboard.writeText(content);
    toast.success("Copied to clipboard");
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
        </div>
      </div>

      <div className="flex-1 border border-border rounded-[var(--radius)] overflow-auto bg-card">
        <div className="flex items-center justify-center min-h-full p-8">
          <div style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center', transition: 'transform 0.2s' }}>
            {viewMode === 'svg' && hasSVG ? (
              <div dangerouslySetInnerHTML={{ __html: blueprintSVG }} />
            ) : viewMode === 'mermaid' && hasMermaid ? (
              <pre className="whitespace-pre-wrap font-mono text-sm bg-muted p-6 rounded-[var(--radius)] max-w-4xl">
                {blueprintMermaid}
              </pre>
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
