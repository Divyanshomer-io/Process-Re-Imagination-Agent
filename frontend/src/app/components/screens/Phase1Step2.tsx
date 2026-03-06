import { useState } from "react";
import { useNavigate } from "react-router";
import { Upload, X, Eye } from "lucide-react";
import { Button } from "../ui/button";
import { ProcessStepper } from "../shared/ProcessStepper";
import { useEngagementStore } from "../../store/engagementStore";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";

const steps = [
  { number: 1, label: "As‑Is Process Maps" },
  { number: 2, label: "Pain Points & Performance Context" },
  { number: 3, label: "External Benchmarks" },
];

export function Phase1Step2() {
  const navigate = useNavigate();
  const {
    painPointFiles,
    addPainPointFile,
    removePainPointFile,
  } = useEngagementStore();

  const [previewFile, setPreviewFile] = useState<{ name: string } | null>(null);

  const handleFileUpload = () => {
    // Simulate file upload
    const mockFile = {
      name: `Pain-Points-Document-${painPointFiles.length + 1}.pdf`,
      date: new Date(),
      id: Math.random().toString(),
    };
    addPainPointFile(mockFile);
  };

  const handleSaveDraft = () => {
    toast.success("Draft saved");
  };

  const handleNext = () => {
    if (painPointFiles.length > 0) {
      navigate('/phase1/step3');
    }
  };

  const handleBack = () => {
    navigate('/phase1/step1');
  };

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div>
        <h1>Phase 1 — Structured Contextual Inputs (The Fuel)</h1>
        <div className="mt-6">
          <ProcessStepper steps={steps} currentStep={2} />
        </div>
      </div>

      <div className="space-y-6">
        <div>
          <h3 className="mb-4">Upload Pain Points & Performance Context</h3>
          <p className="text-muted-foreground mb-6">
            Upload documents containing pain points, regional nuances, KPI baselines, targets, and strategic constraints. The agent will extract all context from these documents.
          </p>
          
          <div
            onClick={handleFileUpload}
            className="border-2 border-dashed border-border rounded-[var(--radius)] p-12 text-center cursor-pointer hover:border-accent transition-colors"
          >
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              Click to upload Pain Points & Performance documents
            </p>
            <p className="text-[var(--text-caption)] text-muted-foreground mt-2">
              Include: pain points, regional variations, KPIs, strategic guardrails, and constraints
            </p>
          </div>
        </div>

        {painPointFiles.length > 0 ? (
          <div className="border border-border rounded-[var(--radius)] overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left px-4 py-3">File Name</th>
                  <th className="text-left px-4 py-3">Uploaded</th>
                  <th className="text-left px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {painPointFiles.map((file) => (
                  <tr key={file.id} className="border-t border-border">
                    <td className="px-4 py-3">{file.name}</td>
                    <td className="px-4 py-3">{file.date.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setPreviewFile(file)}
                        >
                          <Eye className="h-4 w-4 mr-2" />
                          View
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removePainPointFile(file.id)}
                        >
                          <X className="h-4 w-4 mr-2" />
                          Remove
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            No pain points documents uploaded yet.
          </div>
        )}

        <div className="bg-muted p-6 rounded-[var(--radius)] space-y-2">
          <h4>What should these documents include?</h4>
          <ul className="list-disc list-inside space-y-1 text-muted-foreground">
            <li>Current pain points and inefficiencies in the process</li>
            <li>Regional nuances and variations across different teams/sites</li>
            <li>Current KPI baselines and target performance metrics</li>
            <li>Strategic guardrails, risk appetite, and constraints</li>
            <li>Any performance context relevant to the transformation</li>
          </ul>
        </div>
      </div>

      <div className="flex gap-4">
        <Button onClick={handleNext} disabled={painPointFiles.length === 0}>
          Next
        </Button>
        <Button variant="secondary" onClick={handleBack}>
          Back
        </Button>
        <Button variant="secondary" onClick={handleSaveDraft}>
          Save Draft
        </Button>
      </div>

      <Dialog open={!!previewFile} onOpenChange={() => setPreviewFile(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Preview</DialogTitle>
          </DialogHeader>
          <div className="py-8 text-center">
            <p className="text-muted-foreground mb-4">{previewFile?.name}</p>
            <div className="border border-border rounded-[var(--radius)] p-12 bg-muted">
              <p className="text-muted-foreground">File preview placeholder</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}