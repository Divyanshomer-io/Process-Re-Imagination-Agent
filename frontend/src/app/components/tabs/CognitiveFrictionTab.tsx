import { useState } from "react";
import { Input } from "../ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../ui/sheet";
import { Badge } from "../ui/badge";
import { mockFrictionData, useResultsStore } from "../../data/mockResults";
import { Search, Database, Zap, Brain } from "lucide-react";

export function CognitiveFrictionTab() {
  const frictionData = useResultsStore((s) => s.frictionData);
  const [searchTerm, setSearchTerm] = useState("");
  const [regionFilter, setRegionFilter] = useState("all");
  const [evidenceFilter, setEvidenceFilter] = useState("all");
  const [selectedFriction, setSelectedFriction] = useState<typeof mockFrictionData[0] | null>(null);

  const sourceData = frictionData.length > 0 ? frictionData : mockFrictionData;

  const regions = Array.from(new Set(sourceData.map((d) => d.region))).sort();

  const filteredData = sourceData.filter(item => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = !term ||
      item.manualAction.toLowerCase().includes(term) ||
      item.id.toLowerCase().includes(term) ||
      (item.whyItMatters ?? "").toLowerCase().includes(term);
    const matchesRegion = regionFilter === "all" || item.region === regionFilter;
    const matchesEvidence = evidenceFilter === "all" ||
                            (evidenceFilter === "yes" && item.evidenceCount > 0) ||
                            (evidenceFilter === "no" && item.evidenceCount === 0);
    return matchesSearch && matchesRegion && matchesEvidence;
  });

  const pathBadgeVariant = (path: string) => {
    if (path === "A") return "pathA";
    if (path === "B") return "pathB";
    return "pathC";
  };

  const pathIcon = (path: string) => {
    if (path === "A") return <Database className="h-4 w-4" />;
    if (path === "B") return <Zap className="h-4 w-4" />;
    return <Brain className="h-4 w-4" />;
  };

  const pathDescription = (path: string) => {
    if (path === "A") return "Core Standardization";
    if (path === "B") return "Platform Automation";
    return "Agentic AI Deployment";
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search friction…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={regionFilter} onValueChange={setRegionFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Region/Context" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Regions</SelectItem>
            {regions.map((r) => (
              <SelectItem key={r} value={r}>{r}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={evidenceFilter} onValueChange={setEvidenceFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Evidence present" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="yes">Yes</SelectItem>
            <SelectItem value="no">No</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {filteredData.length > 0 ? (
        <div className="border border-border rounded-[var(--radius)] overflow-auto">
          <table className="w-full border-collapse" style={{ tableLayout: "fixed", minWidth: 1100 }}>
            <colgroup>
              <col style={{ width: "7%" }} />
              <col style={{ width: "18%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "10%" }} />
              <col style={{ width: "20%" }} />
              <col style={{ width: "20%" }} />
              <col style={{ width: "13%" }} />
            </colgroup>
            <thead className="bg-muted sticky top-0 z-10">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Friction ID</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Current Manual Action</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Where in Process</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Region Impacted</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Why It Matters</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence</th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Open Questions</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((item) => (
                <tr
                  key={item.id}
                  className="border-t border-border cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => setSelectedFriction(item)}
                  style={{
                    borderLeft: `4px solid var(--path-${item.pathClassification.toLowerCase()})`
                  }}
                >
                  <td className="px-4 py-3 align-top text-sm font-semibold whitespace-nowrap">{item.id}</td>
                  <td className="px-4 py-3 align-top text-sm leading-relaxed">{item.manualAction}</td>
                  <td className="px-4 py-3 align-top text-sm">{item.whereInProcess}</td>
                  <td className="px-4 py-3 align-top text-sm">{item.region}</td>
                  <td className="px-4 py-3 align-top text-sm leading-relaxed text-muted-foreground">{item.whyItMatters || "—"}</td>
                  <td className="px-4 py-3 align-top text-sm leading-relaxed text-muted-foreground">{item.evidenceText || "—"}</td>
                  <td className="px-4 py-3 align-top text-sm text-muted-foreground">{item.openQuestions || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          No cognitive friction items identified.
        </div>
      )}

      <Sheet open={!!selectedFriction} onOpenChange={() => setSelectedFriction(null)}>
        <SheetContent className="w-[640px] overflow-y-auto">
          {selectedFriction && (
            <>
              <SheetHeader>
                <SheetTitle>Friction Detail: {selectedFriction.id}</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div>
                  <h4 className="mb-2 text-sm font-semibold">Current Manual Action</h4>
                  <p className="text-sm text-muted-foreground">{selectedFriction.manualAction}</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="mb-1 text-sm font-semibold">Where in Process</h4>
                    <p className="text-sm text-muted-foreground">{selectedFriction.whereInProcess}</p>
                  </div>
                  <div>
                    <h4 className="mb-1 text-sm font-semibold">Region Impacted</h4>
                    <p className="text-sm text-muted-foreground">{selectedFriction.region}</p>
                  </div>
                </div>
                {selectedFriction.whyItMatters && (
                  <div>
                    <h4 className="mb-2 text-sm font-semibold">Why It Matters</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">{selectedFriction.whyItMatters}</p>
                  </div>
                )}
                {selectedFriction.evidenceText && (
                  <div>
                    <h4 className="mb-2 text-sm font-semibold">Evidence</h4>
                    <div className="p-3 border border-border rounded-[var(--radius)] bg-muted/30">
                      <p className="text-sm text-muted-foreground leading-relaxed">{selectedFriction.evidenceText}</p>
                    </div>
                  </div>
                )}
                {selectedFriction.openQuestions && (
                  <div>
                    <h4 className="mb-2 text-sm font-semibold">Open Questions</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">{selectedFriction.openQuestions}</p>
                  </div>
                )}
                {selectedFriction.relatedPainPoints.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-sm font-semibold">Related Pain Points</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                      {selectedFriction.relatedPainPoints.map((point, index) => (
                        <li key={index}>{point}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {selectedFriction.evidence.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-sm font-semibold">Source Files</h4>
                    <div className="space-y-2">
                      {selectedFriction.evidence.map((file, index) => (
                        <div key={index} className="p-2 border border-border rounded-[var(--radius)] text-sm">
                          {file}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div
                  className="p-4 rounded-[var(--radius)] border-2"
                  style={{
                    borderColor: `var(--path-${selectedFriction.pathClassification.toLowerCase()})`,
                    backgroundColor: `var(--path-${selectedFriction.pathClassification.toLowerCase()}-light)`
                  }}
                >
                  <h4 className="mb-3 text-sm font-semibold">Path Classification</h4>
                  <div className="flex items-center gap-3">
                    <div
                      className="p-2 rounded-lg"
                      style={{
                        backgroundColor: `var(--path-${selectedFriction.pathClassification.toLowerCase()})`,
                        color: `var(--path-${selectedFriction.pathClassification.toLowerCase()}-foreground)`
                      }}
                    >
                      {pathIcon(selectedFriction.pathClassification)}
                    </div>
                    <div>
                      <Badge variant={pathBadgeVariant(selectedFriction.pathClassification)} className="text-sm px-3 py-1 mb-1">
                        Path {selectedFriction.pathClassification}
                      </Badge>
                      <p className="text-[var(--text-caption)] text-muted-foreground">
                        {pathDescription(selectedFriction.pathClassification)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
