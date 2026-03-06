import { useNavigate, useParams } from "react-router";
import { Button } from "../ui/button";
import { mockUseCases } from "../../data/mockResults";

export function UseCaseDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const useCase = mockUseCases.find(uc => uc.id === id);

  if (!useCase) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <h1>Use Case not found</h1>
        <Button onClick={() => navigate('/phase3/results')} className="mt-4">
          Back to Results
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      <div>
        <h1>Use Case {useCase.id}</h1>
        <p className="text-[var(--text-h4)] text-muted-foreground mt-2">
          Agent Role: {useCase.agentRole}
        </p>
      </div>

      <div className="space-y-6">
        <div className="border border-border rounded-[var(--radius)] p-6">
          <h3 className="mb-4">Context</h3>
          <p className="text-muted-foreground">{useCase.context}</p>
        </div>

        <div className="border border-border rounded-[var(--radius)] p-6">
          <h3 className="mb-4">Agent Role</h3>
          <p className="text-muted-foreground">{useCase.agentRole}</p>
        </div>

        <div className="border border-border rounded-[var(--radius)] p-6">
          <h3 className="mb-4">Mechanism</h3>
          <p className="text-muted-foreground">{useCase.mechanism}</p>
        </div>

        <div className="border border-border rounded-[var(--radius)] p-6">
          <h3 className="mb-4">Tech</h3>
          <p className="text-muted-foreground">{useCase.tech}</p>
        </div>

        <div className="border border-border rounded-[var(--radius)] p-6">
          <h3 className="mb-4">Value</h3>
          <p className="text-muted-foreground">{useCase.value}</p>
        </div>
      </div>

      <div className="flex gap-4">
        <Button variant="secondary" onClick={() => navigate('/phase3/results')}>
          Back to Use Case Cards
        </Button>
        <Button variant="outline" onClick={() => navigate('/phase3/results')}>
          View in Layered Blueprint
        </Button>
        <Button variant="outline" onClick={() => navigate('/phase3/results')}>
          View Path Classification
        </Button>
      </div>
    </div>
  );
}
