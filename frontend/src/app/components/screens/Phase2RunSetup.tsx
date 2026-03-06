import { useNavigate } from "react-router";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Alert, AlertDescription } from "../ui/alert";
import { useEngagementStore } from "../../store/engagementStore";
import { CheckCircle2, AlertCircle } from "lucide-react";

export function Phase2RunSetup() {
  const navigate = useNavigate();
  const { asIsFiles, kpis, benchmarkFiles, painPointsList } = useEngagementStore();

  const painPointsCount = painPointsList.length;
  const hasAllInputs = asIsFiles.length > 0;

  const handleStartRun = () => {
    navigate('/run/progress');
  };

  const handleBack = () => {
    navigate('/phase1/step1');
  };

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div>
        <h1>Phase 2 — Agentic AI Reasoning Engine (The Architect)</h1>
      </div>

      {!hasAllInputs && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Phase 1 inputs are incomplete. Complete missing sections before running.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Inputs Readiness Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            {asIsFiles.length > 0 ? (
              <CheckCircle2 className="h-5 w-5 text-accent" />
            ) : (
              <AlertCircle className="h-5 w-5 text-destructive" />
            )}
            <span>As‑Is maps: {asIsFiles.length}</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-accent" />
            <span>Pain points: {painPointsCount}</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-accent" />
            <span>KPI rows: {kpis.length}</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-accent" />
            <span>Benchmarks: {benchmarkFiles.length}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>What the engine will produce</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc list-inside space-y-2 text-muted-foreground">
            <li>Cognitive Friction Analysis table</li>
            <li>Path A/B/C classification with suitability reasons</li>
            <li>Strategy Report (Markdown)</li>
            <li>Process Blueprint (XML with Mermaid diagram)</li>
          </ul>
        </CardContent>
      </Card>

      <div className="flex gap-4">
        <Button onClick={handleStartRun} disabled={!hasAllInputs}>
          Start Run
        </Button>
        <Button variant="secondary" onClick={handleBack}>
          Back to Phase 1
        </Button>
      </div>
    </div>
  );
}