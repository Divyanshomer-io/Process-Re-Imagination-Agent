import { useNavigate } from "react-router";
import { Upload, X, Eye } from "lucide-react";
import { Button } from "../ui/button";
import { Checkbox } from "../ui/checkbox";
import { Label } from "../ui/label";
import { ProcessStepper } from "../shared/ProcessStepper";
import { useEngagementStore } from "../../store/engagementStore";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { useState } from "react";

const steps = [
  { number: 1, label: "As‑Is Process Maps" },
  { number: 2, label: "Pain Points & Performance Context" },
  { number: 3, label: "External Benchmarks" },
];

export function Phase1Step1() {
  const navigate = useNavigate();
  const { asIsFiles, regionalVariations, addAsIsFile, removeAsIsFile, setRegionalVariations } = useEngagementStore();
  const [previewFile, setPreviewFile] = useState<{ name: string } | null>(null);

  const handleFileUpload = () => {
    // Simulate file upload
    const mockFile = {
      name: `As-Is-Process-Map-${asIsFiles.length + 1}.pdf`,
      date: new Date(),
      id: Math.random().toString(),
    };
    addAsIsFile(mockFile);
  };

  const handleSaveDraft = () => {
    toast.success("Draft saved");
  };

  const handleNext = () => {
    if (asIsFiles.length > 0) {
      navigate('/phase1/step2');
    }
  };

  const handleBack = () => {
    navigate('/');
  };

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div>
        <h1>Phase 1 — Structured Contextual Inputs (The Fuel)</h1>
        <div className="mt-6">
          <ProcessStepper steps={steps} currentStep={1} />
        </div>
      </div>

      <div className="space-y-6">
        <div>
          <h3 className="mb-4">Upload As‑Is Process Maps</h3>
          
          <div
            onClick={handleFileUpload}
            className="border-2 border-dashed border-border rounded-[var(--radius)] p-12 text-center cursor-pointer hover:border-accent transition-colors"
          >
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              Click to upload As‑Is Process Map(s)
            </p>
          </div>
        </div>

        {asIsFiles.length > 0 ? (
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
                {asIsFiles.map((file) => (
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
                          onClick={() => removeAsIsFile(file.id)}
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
            No As‑Is maps uploaded yet.
          </div>
        )}

        <div className="flex items-center space-x-2">
          <Checkbox
            id="regionalVariations"
            checked={regionalVariations}
            onCheckedChange={(checked) => setRegionalVariations(checked as boolean)}
          />
          <Label htmlFor="regionalVariations" className="cursor-pointer">
            Includes regional variations
          </Label>
        </div>
        <p className="text-[var(--text-caption)] text-muted-foreground">
          Include regional variations so deviations can be evaluated for necessity vs inefficiency.
        </p>
      </div>

      <div className="flex gap-4">
        <Button onClick={handleNext} disabled={asIsFiles.length === 0}>
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
