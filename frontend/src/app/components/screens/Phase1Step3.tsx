import { useState } from "react";
import { useNavigate } from "react-router";
import { Upload, X } from "lucide-react";
import { Button } from "../ui/button";
import { ProcessStepper } from "../shared/ProcessStepper";
import { useEngagementStore } from "../../store/engagementStore";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

const steps = [
  { number: 1, label: "As‑Is Process Maps" },
  { number: 2, label: "Pain Points & Performance Context" },
  { number: 3, label: "External Benchmarks" },
];

export function Phase1Step3() {
  const navigate = useNavigate();
  const { benchmarkFiles, addBenchmarkFile, removeBenchmarkFile } = useEngagementStore();
  const [showCompleteModal, setShowCompleteModal] = useState(false);

  const handleFileUpload = () => {
    const mockFile = {
      name: `Benchmark-${benchmarkFiles.length + 1}.pdf`,
      tag: "Benchmark",
      id: Math.random().toString(),
    };
    addBenchmarkFile(mockFile);
  };

  const handleUpdateTag = (id: string, tag: string) => {
    removeBenchmarkFile(id);
    addBenchmarkFile({ ...benchmarkFiles.find(f => f.id === id)!, tag });
  };

  const handleSaveDraft = () => {
    toast.success("Draft saved");
  };

  const handleFinish = () => {
    setShowCompleteModal(true);
  };

  const handleStartRun = () => {
    setShowCompleteModal(false);
    navigate('/phase2/setup');
  };

  const handleLater = () => {
    setShowCompleteModal(false);
    navigate('/phase2/setup');
  };

  const handleBack = () => {
    navigate('/phase1/step2');
  };

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div>
        <h1>Phase 1 — Structured Contextual Inputs (The Fuel)</h1>
        <div className="mt-6">
          <ProcessStepper steps={steps} currentStep={3} />
        </div>
      </div>

      <div className="space-y-6">
        <div>
          <h3 className="mb-4">External Benchmarks / Best Practices</h3>
          
          <div
            onClick={handleFileUpload}
            className="border-2 border-dashed border-border rounded-[var(--radius)] p-12 text-center cursor-pointer hover:border-accent transition-colors"
          >
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">
              Attach benchmarks / best practices / standard flows
            </p>
          </div>
        </div>

        {benchmarkFiles.length > 0 ? (
          <div className="border border-border rounded-[var(--radius)] overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left px-4 py-3">File Name</th>
                  <th className="text-left px-4 py-3">Tag</th>
                  <th className="text-left px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {benchmarkFiles.map((file) => (
                  <tr key={file.id} className="border-t border-border">
                    <td className="px-4 py-3">{file.name}</td>
                    <td className="px-4 py-3">
                      <Select
                        value={file.tag}
                        onValueChange={(value) => handleUpdateTag(file.id, value)}
                      >
                        <SelectTrigger className="w-40">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Benchmark">Benchmark</SelectItem>
                          <SelectItem value="Best Practice">Best Practice</SelectItem>
                          <SelectItem value="Reference">Reference</SelectItem>
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeBenchmarkFile(file.id)}
                      >
                        <X className="h-4 w-4 mr-2" />
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            No benchmarks attached.
          </div>
        )}
      </div>

      <div className="flex gap-4">
        <Button onClick={handleFinish}>Finish Phase 1</Button>
        <Button variant="secondary" onClick={handleBack}>
          Back
        </Button>
        <Button variant="secondary" onClick={handleSaveDraft}>
          Save Draft
        </Button>
      </div>

      <Dialog open={showCompleteModal} onOpenChange={setShowCompleteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Phase 1 complete</DialogTitle>
          </DialogHeader>
          <p>Start Phase 2 run now?</p>
          <DialogFooter>
            <Button variant="secondary" onClick={handleLater}>
              Later
            </Button>
            <Button onClick={handleStartRun}>Start Run</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
