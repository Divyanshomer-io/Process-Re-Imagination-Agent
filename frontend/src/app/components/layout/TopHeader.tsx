import { HelpCircle } from "lucide-react";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { useEngagementStore } from "../../store/engagementStore";

export function TopHeader() {
  const { processName, region, status } = useEngagementStore();

  const statusVariant = {
    draft: "default" as const,
    running: "secondary" as const,
    ready: "default" as const,
  };

  return (
    <header className="border-b border-border bg-card px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <h1 className="text-[var(--text-h2)] font-[var(--font-weight-bold)]">
          Cognitive Process Re‑imagination Engine
        </h1>
        {processName && (
          <div className="flex items-center gap-3">
            <span className="text-[var(--text-base)] text-muted-foreground">
              Engagement: {processName} {region && `— ${region}`}
            </span>
            <Badge variant={statusVariant[status]}>
              {status === "draft" && "Draft"}
              {status === "running" && "Running"}
              {status === "ready" && "Results Ready"}
            </Badge>
          </div>
        )}
      </div>
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="ghost" size="icon">
            <HelpCircle className="h-5 w-5" />
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Methodology & Terminology</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <h3 className="mb-2">Phase 1: The Fuel</h3>
              <p className="text-muted-foreground">
                Structured contextual inputs including As-Is process maps, pain points, regional nuances, KPIs, and benchmarks.
              </p>
            </div>
            <div>
              <h3 className="mb-2">Phase 2: The Architect</h3>
              <p className="text-muted-foreground">
                Agentic AI reasoning engine that analyzes patterns, identifies cognitive friction, and classifies into paths.
              </p>
            </div>
            <div>
              <h3 className="mb-2">Phase 3: The Outcome</h3>
              <p className="text-muted-foreground">
                Re-imagined process blueprint with cognitive friction analysis, strategy report, and technical implementation.
              </p>
            </div>
            <div>
              <h3 className="mb-2">Path Classifications</h3>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li><strong>Path A:</strong> Core Standardization</li>
                <li><strong>Path B:</strong> Platform Automation (deterministic workflows/RPA)</li>
                <li><strong>Path C:</strong> Agentic AI Deployment (perception/reasoning/adaptive action)</li>
              </ul>
            </div>
            <div>
              <h3 className="mb-2">Key Concepts</h3>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li><strong>Cognitive Friction:</strong> Humans acting as middleware or manual bottlenecks</li>
                <li><strong>Strategy Report:</strong> Markdown document with executive summary, agent personas, tech stack</li>
                <li><strong>Trust Gap Protocol:</strong> Shadow → Co-Pilot → Autopilot progression</li>
                <li><strong>Process Blueprint:</strong> Mermaid.js diagram wrapped in XML with layered architecture</li>
              </ul>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </header>
  );
}
