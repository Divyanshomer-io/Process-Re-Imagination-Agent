import { useEffect } from "react";
import { useNavigate } from "react-router";
import { Button } from "../ui/button";
import { Progress } from "../ui/progress";
import { Alert, AlertDescription } from "../ui/alert";
import { useEngagementStore } from "../../store/engagementStore";
import { CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { useState } from "react";

interface StepStatus {
  label: string;
  status: 'pending' | 'running' | 'complete';
}

export function RunProgress() {
  const navigate = useNavigate();
  const [showCancelDialog, setShowCancelDialog] = useState(false);

  const {
    asIsFiles,
    triggerRun,
    _realRunTriggered,
    backendStatus,
    realPhase1Steps,
    realPhase2Steps,
    realPhase3Steps,
    realProgress,
    runComplete,
    runError,
  } = useEngagementStore();

  // Redirect to Phase 1 if no files have been uploaded (e.g. after hard refresh)
  useEffect(() => {
    if (asIsFiles.length === 0 && !_realRunTriggered && backendStatus === 'draft') {
      navigate('/phase1/step1');
      return;
    }
    if (!_realRunTriggered && asIsFiles.length > 0) {
      useEngagementStore.setState({ _realRunTriggered: true });
      triggerRun();
    }
  }, []);

  // Fallback step labels if backend hasn't responded yet
  const phase1Steps: StepStatus[] = realPhase1Steps.length > 0
    ? realPhase1Steps
    : [
        { label: "Read As\u2011Is maps", status: 'pending' },
        { label: "Read pain points & regional nuances", status: 'pending' },
        { label: "Read KPIs & guardrails", status: 'pending' },
        { label: "Read benchmarks", status: 'pending' },
        { label: "Identify cognitive friction", status: 'pending' },
      ];

  const phase2Steps: StepStatus[] = realPhase2Steps.length > 0
    ? realPhase2Steps
    : [
        { label: "Compare As\u2011Is vs benchmarks", status: 'pending' },
        { label: "Suitability assessment", status: 'pending' },
        { label: "Classify into Path A/B/C", status: 'pending' },
      ];

  const phase3Steps: StepStatus[] = realPhase3Steps.length > 0
    ? realPhase3Steps
    : [
        { label: "Produce Strategy Report (Markdown)", status: 'pending' },
        { label: "Generate Process Blueprint (XML/Mermaid)", status: 'pending' },
      ];

  const progress = realProgress;
  const isError = backendStatus === 'error';

  const handleCancel = () => {
    setShowCancelDialog(false);
    navigate('/phase2/setup');
  };

  const handleViewResults = () => {
    navigate('/phase3/results');
  };

  const PhaseSection = ({ title, steps }: { title: string; steps: StepStatus[] }) => (
    <div className="space-y-3">
      <h3>{title}</h3>
      {steps.map((step, index) => (
        <div key={index} className="flex items-center gap-3 pl-4">
          {step.status === 'complete' && <CheckCircle2 className="h-5 w-5 text-accent" />}
          {step.status === 'running' && <Loader2 className="h-5 w-5 animate-spin text-accent" />}
          {step.status === 'pending' && <div className="h-5 w-5 rounded-full border-2 border-muted" />}
          <span className={step.status === 'pending' ? 'text-muted-foreground' : ''}>{step.label}</span>
        </div>
      ))}
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      <div>
        <h1>{runComplete ? (isError ? 'Run failed' : 'Run complete') : 'Run in progress'}</h1>
        <Progress value={progress} className="mt-4" />
        <p className="text-muted-foreground mt-2">{Math.round(progress)}% complete</p>
      </div>

      {runComplete && !isError && (
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>
            All phases complete! Click below to view results.
          </AlertDescription>
        </Alert>
      )}

      {isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {runError || 'An error occurred during the agent run.'}
          </AlertDescription>
        </Alert>
      )}

      <div className="space-y-6">
        <PhaseSection title="Phase 1 — Ingest & Synthesize (Cognitive Friction)" steps={phase1Steps} />
        <PhaseSection title="Phase 2 — Pattern Match & Suitability (Path A/B/C)" steps={phase2Steps} />
        <PhaseSection title="Phase 3 — Generate Outcome" steps={phase3Steps} />
      </div>

      <div className="flex gap-4">
        {runComplete && !isError ? (
          <Button onClick={handleViewResults}>View Results</Button>
        ) : isError ? (
          <Button variant="secondary" onClick={() => navigate('/phase2/setup')}>
            Back to Setup
          </Button>
        ) : (
          <>
            <Button variant="destructive" onClick={() => setShowCancelDialog(true)}>
              Cancel Run
            </Button>
            <Button variant="secondary" disabled>
              View Partial Results
            </Button>
          </>
        )}
      </div>

      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel run?</DialogTitle>
          </DialogHeader>
          <p>Canceling stops the current run.</p>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setShowCancelDialog(false)}>
              Keep Running
            </Button>
            <Button variant="destructive" onClick={handleCancel}>
              Cancel Run
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
