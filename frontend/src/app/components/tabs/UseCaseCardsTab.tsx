import { useState } from "react";
import { useNavigate } from "react-router";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { mockUseCases, useResultsStore } from "../../data/mockResults";
import { Search } from "lucide-react";

export function UseCaseCardsTab() {
  const navigate = useNavigate();
  const useCasesData = useResultsStore((s) => s.useCases);
  const [searchTerm, setSearchTerm] = useState("");

  const allUseCases = useCasesData.length > 0 ? useCasesData : mockUseCases;
  const filteredUseCases = allUseCases.filter(useCase => 
    useCase.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (useCase.title ?? "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    useCase.context.toLowerCase().includes(searchTerm.toLowerCase()) ||
    useCase.agentRole.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search AI agent cards…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {filteredUseCases.length > 0 ? (
        <div className="grid grid-cols-3 gap-6">
          {filteredUseCases.map((useCase) => (
            <Card key={useCase.id} className="flex flex-col">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>{useCase.id}</span>
                  {useCase.path && (
                    <span
                      className="text-xs font-medium px-2 py-0.5 rounded"
                      style={{
                        background: useCase.path === "C" ? "#dbeafe" : useCase.path === "B" ? "#fef3c7" : "#d1fae5",
                        color: useCase.path === "C" ? "#1e40af" : useCase.path === "B" ? "#92400e" : "#065f46",
                      }}
                    >
                      Path {useCase.path}
                    </span>
                  )}
                </CardTitle>
                {useCase.title && (
                  <p className="text-sm text-muted-foreground mt-1">{useCase.title}</p>
                )}
              </CardHeader>
              <CardContent className="flex-1 space-y-4">
                {useCase.sapTarget && (
                  <div>
                    <h4 className="mb-1">SAP Target</h4>
                    <p className="text-[var(--text-caption)] text-muted-foreground">{useCase.sapTarget}</p>
                  </div>
                )}
                <div>
                  <h4 className="mb-1">Context</h4>
                  <p className="text-[var(--text-caption)] text-muted-foreground">{useCase.context}</p>
                </div>
                <div>
                  <h4 className="mb-1">Agent Role</h4>
                  <p className="text-[var(--text-caption)] font-semibold">{useCase.agentRole}</p>
                </div>
                <div>
                  <h4 className="mb-1">Mechanism</h4>
                  <p className="text-[var(--text-caption)] text-muted-foreground">{useCase.mechanism}</p>
                </div>
                <div>
                  <h4 className="mb-1">Tech</h4>
                  <p className="text-[var(--text-caption)] text-muted-foreground">{useCase.tech}</p>
                </div>
                <div>
                  <h4 className="mb-1">Value</h4>
                  <p className="text-[var(--text-caption)] text-muted-foreground">{useCase.value}</p>
                </div>
                <Button
                  className="w-full"
                  onClick={() => navigate(`/phase3/use-case/${useCase.id}`)}
                >
                  Open
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          No AI agent cards generated.
        </div>
      )}
    </div>
  );
}
