import { useState, useMemo } from "react";
import { Button } from "../ui/button";
import { ScrollArea } from "../ui/scroll-area";
import { mockStrategyReport, useResultsStore } from "../../data/mockResults";
import { toast } from "sonner";
import { Copy } from "lucide-react";

function extractHeadings(markdown: string) {
  const headings: { id: string; label: string; level: number }[] = [];
  const lines = markdown.split('\n');
  for (const line of lines) {
    const match = line.match(/^(#{1,3})\s+(.+)$/);
    if (match) {
      const level = match[1].length;
      const label = match[2].replace(/\*\*/g, '').trim();
      const id = label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
      headings.push({ id, label, level });
    }
  }
  return headings;
}

export function StrategyReportTab() {
  const storeReport = useResultsStore((s) => s.strategyReport);
  const reportText = storeReport || String(mockStrategyReport);
  const headings = useMemo(() => extractHeadings(reportText), [reportText]);
  const [activeSection, setActiveSection] = useState(headings[0]?.id ?? "");

  const handleCopy = () => {
    navigator.clipboard.writeText(reportText);
    toast.success("Markdown copied to clipboard");
  };

  if (!reportText.trim()) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <p>Strategy report not yet generated. Please wait for the agent run to complete.</p>
      </div>
    );
  }

  return (
    <div className="flex gap-6 h-full">
      <div className="w-80 space-y-1 overflow-auto">
        <h3 className="mb-4">Table of Contents</h3>
        {headings.map((heading) => (
          <button
            key={heading.id}
            onClick={() => {
              setActiveSection(heading.id);
              const el = document.getElementById(`heading-${heading.id}`);
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }}
            className={`w-full text-left px-4 py-2 rounded-[var(--radius)] transition-colors ${
              activeSection === heading.id
                ? "bg-accent text-accent-foreground"
                : "hover:bg-muted"
            }`}
            style={{ paddingLeft: `${(heading.level - 1) * 16 + 16}px` }}
          >
            {heading.label}
          </button>
        ))}
      </div>

      <div className="flex-1 border border-border rounded-[var(--radius)] relative">
        <div className="absolute top-4 right-4 z-10">
          <Button variant="outline" size="sm" onClick={handleCopy}>
            <Copy className="h-4 w-4 mr-2" />
            Copy Markdown
          </Button>
        </div>
        <ScrollArea className="h-full p-8">
          <div className="prose prose-lg max-w-none">
            {reportText.split('\n').map((line, index) => {
              if (line.startsWith('# ')) {
                const text = line.replace('# ', '');
                const id = text.toLowerCase().replace(/\*\*/g, '').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
                return <h1 key={index} id={`heading-${id}`}>{text}</h1>;
              } else if (line.startsWith('## ')) {
                const text = line.replace('## ', '');
                const id = text.toLowerCase().replace(/\*\*/g, '').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
                return <h2 key={index} id={`heading-${id}`}>{text}</h2>;
              } else if (line.startsWith('### ')) {
                const text = line.replace('### ', '');
                const id = text.toLowerCase().replace(/\*\*/g, '').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
                return <h3 key={index} id={`heading-${id}`}>{text}</h3>;
              } else if (line.startsWith('**') && line.endsWith('**')) {
                return <p key={index}><strong>{line.replace(/\*\*/g, '')}</strong></p>;
              } else if (line.startsWith('- ')) {
                return <li key={index}>{line.replace('- ', '')}</li>;
              } else if (line.trim() === '') {
                return <br key={index} />;
              } else {
                return <p key={index}>{line}</p>;
              }
            })}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
