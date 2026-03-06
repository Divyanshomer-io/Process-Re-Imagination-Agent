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

  const filteredData = (frictionData.length > 0 ? frictionData : mockFrictionData).filter(item => {
    const matchesSearch = item.manualAction.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          item.id.toLowerCase().includes(searchTerm.toLowerCase());
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
            <SelectItem value="North America">North America</SelectItem>
            <SelectItem value="Europe">Europe</SelectItem>
            <SelectItem value="All Regions">All Regions</SelectItem>
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
        <div className="border border-border rounded-[var(--radius)] overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">Friction ID</th>
                <th className="text-left px-4 py-3 font-semibold">Current Manual Action</th>
                <th className="text-left px-4 py-3 font-semibold">Where in Process</th>
                <th className="text-left px-4 py-3 font-semibold">Region Impacted</th>
                <th className="text-left px-4 py-3 font-semibold">Evidence</th>
                <th className="text-left px-4 py-3 font-semibold">Path</th>
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
                  <td className="px-4 py-3 font-semibold">{item.id}</td>
                  <td className="px-4 py-3">{item.manualAction}</td>
                  <td className="px-4 py-3">{item.whereInProcess}</td>
                  <td className="px-4 py-3">{item.region}</td>
                  <td className="px-4 py-3">{item.evidenceCount}</td>
                  <td className="px-4 py-3">
                    <Badge variant={pathBadgeVariant(item.pathClassification)} className="text-sm px-3 py-1">
                      Path {item.pathClassification}
                    </Badge>
                  </td>
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
        <SheetContent className="w-[600px]">
          {selectedFriction && (
            <>
              <SheetHeader>
                <SheetTitle>Friction Detail: {selectedFriction.id}</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div>
                  <h4 className="mb-2">Summary</h4>
                  <p className="text-muted-foreground">{selectedFriction.manualAction}</p>
                </div>
                <div>
                  <h4 className="mb-2">Related Pain Points</h4>
                  <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                    {selectedFriction.relatedPainPoints.map((point, index) => (
                      <li key={index}>{point}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="mb-2">Evidence</h4>
                  <div className="space-y-2">
                    {selectedFriction.evidence.map((file, index) => (
                      <div key={index} className="p-2 border border-border rounded-[var(--radius)]">
                        {file}
                      </div>
                    ))}
                  </div>
                </div>
                <div 
                  className="p-4 rounded-[var(--radius)] border-2"
                  style={{ 
                    borderColor: `var(--path-${selectedFriction.pathClassification.toLowerCase()})`,
                    backgroundColor: `var(--path-${selectedFriction.pathClassification.toLowerCase()}-light)`
                  }}
                >
                  <h4 className="mb-3">Path Classification</h4>
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