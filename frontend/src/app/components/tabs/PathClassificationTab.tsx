import { useState } from "react";
import { Input } from "../ui/input";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../ui/sheet";
import { mockPathData, useResultsStore } from "../../data/mockResults";
import { Search, Database, Zap, Brain } from "lucide-react";

export function PathClassificationTab() {
  const pathData = useResultsStore((s) => s.pathData);
  const [searchTerm, setSearchTerm] = useState("");
  const [pathFilter, setPathFilter] = useState("all");
  const [selectedItem, setSelectedItem] = useState<typeof mockPathData[0] | null>(null);

  const filteredData = (pathData.length > 0 ? pathData : mockPathData).filter(item => {
    const matchesSearch = item.item.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          item.suitabilityReason.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesPath = pathFilter === "all" || item.path === pathFilter;
    return matchesSearch && matchesPath;
  });

  const pathBadgeVariant = (path: string) => {
    if (path === "A") return "pathA";
    if (path === "B") return "pathB";
    return "pathC";
  };

  const pathLabel = (path: string) => {
    if (path === "A") return "Path A";
    if (path === "B") return "Path B";
    return "Path C";
  };
  
  const pathIcon = (path: string) => {
    if (path === "A") return <Database className="h-5 w-5" />;
    if (path === "B") return <Zap className="h-5 w-5" />;
    return <Brain className="h-5 w-5" />;
  };
  
  const pathDescription = (path: string) => {
    if (path === "A") return "Core Standardization";
    if (path === "B") return "Platform Automation (deterministic)";
    return "Agentic AI Deployment (perception/reasoning/adaptive)";
  };

  return (
    <div className="space-y-6">
      {/* Path Overview Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div 
          className="p-6 border-2 rounded-[var(--radius)] transition-all hover:shadow-md"
          style={{ 
            borderColor: 'var(--path-a)',
            backgroundColor: 'var(--path-a-light)'
          }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div 
              className="p-2 rounded-lg"
              style={{ backgroundColor: 'var(--path-a)', color: 'var(--path-a-foreground)' }}
            >
              <Database className="h-5 w-5" />
            </div>
            <Badge variant="pathA" className="text-sm px-3 py-1">Path A</Badge>
          </div>
          <p className="text-[var(--text-caption)] font-semibold" style={{ color: 'var(--path-a)' }}>
            Core Standardization
          </p>
          <p className="text-[var(--text-caption)] text-muted-foreground mt-2">
            Single source of truth and data consolidation
          </p>
        </div>
        
        <div 
          className="p-6 border-2 rounded-[var(--radius)] transition-all hover:shadow-md"
          style={{ 
            borderColor: 'var(--path-b)',
            backgroundColor: 'var(--path-b-light)'
          }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div 
              className="p-2 rounded-lg"
              style={{ backgroundColor: 'var(--path-b)', color: 'var(--path-b-foreground)' }}
            >
              <Zap className="h-5 w-5" />
            </div>
            <Badge variant="pathB" className="text-sm px-3 py-1">Path B</Badge>
          </div>
          <p className="text-[var(--text-caption)] font-semibold" style={{ color: 'var(--path-b)' }}>
            Platform Automation
          </p>
          <p className="text-[var(--text-caption)] text-muted-foreground mt-2">
            Deterministic workflows and rule-based systems
          </p>
        </div>
        
        <div 
          className="p-6 border-2 rounded-[var(--radius)] transition-all hover:shadow-md"
          style={{ 
            borderColor: 'var(--path-c)',
            backgroundColor: 'var(--path-c-light)'
          }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div 
              className="p-2 rounded-lg"
              style={{ backgroundColor: 'var(--path-c)', color: 'var(--path-c-foreground)' }}
            >
              <Brain className="h-5 w-5" />
            </div>
            <Badge variant="pathC" className="text-sm px-3 py-1">Path C</Badge>
          </div>
          <p className="text-[var(--text-caption)] font-semibold" style={{ color: 'var(--path-c)' }}>
            Agentic AI Deployment
          </p>
          <p className="text-[var(--text-caption)] text-muted-foreground mt-2">
            Perception, reasoning, and adaptive intelligence
          </p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search steps…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant={pathFilter === "all" ? "default" : "outline"}
            onClick={() => setPathFilter("all")}
          >
            All
          </Button>
          <Button
            variant={pathFilter === "A" ? "default" : "outline"}
            onClick={() => setPathFilter("A")}
            className={pathFilter === "A" ? "" : "hover:bg-[var(--path-a-light)]"}
          >
            <Database className="h-4 w-4 mr-2" />
            Path A
          </Button>
          <Button
            variant={pathFilter === "B" ? "default" : "outline"}
            onClick={() => setPathFilter("B")}
            className={pathFilter === "B" ? "" : "hover:bg-[var(--path-b-light)]"}
          >
            <Zap className="h-4 w-4 mr-2" />
            Path B
          </Button>
          <Button
            variant={pathFilter === "C" ? "default" : "outline"}
            onClick={() => setPathFilter("C")}
            className={pathFilter === "C" ? "" : "hover:bg-[var(--path-c-light)]"}
          >
            <Brain className="h-4 w-4 mr-2" />
            Path C
          </Button>
        </div>
      </div>

      {/* Classification Table */}
      {filteredData.length > 0 ? (
        <div className="border border-border rounded-[var(--radius)] overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">Item</th>
                <th className="text-left px-4 py-3 font-semibold">Recommended Path</th>
                <th className="text-left px-4 py-3 font-semibold">Suitability Reason</th>
                <th className="text-left px-4 py-3 font-semibold">Notes/Assumptions</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((item, index) => (
                <tr
                  key={index}
                  className="border-t border-border cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => setSelectedItem(item)}
                  style={{
                    borderLeft: `4px solid var(--path-${item.path.toLowerCase()})`
                  }}
                >
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <div 
                        className="p-1.5 rounded"
                        style={{ 
                          backgroundColor: `var(--path-${item.path.toLowerCase()}-light)`,
                          color: `var(--path-${item.path.toLowerCase()})`
                        }}
                      >
                        {pathIcon(item.path)}
                      </div>
                      <span className="font-semibold">{item.item}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <Badge variant={pathBadgeVariant(item.path)} className="text-sm px-3 py-1">
                      {pathLabel(item.path)}
                    </Badge>
                  </td>
                  <td className="px-4 py-4">{item.suitabilityReason}</td>
                  <td className="px-4 py-4 text-muted-foreground">{item.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          No items match the current filters.
        </div>
      )}

      {/* Detail Sheet */}
      <Sheet open={!!selectedItem} onOpenChange={() => setSelectedItem(null)}>
        <SheetContent className="w-[600px]">
          {selectedItem && (
            <>
              <SheetHeader>
                <SheetTitle>Classification Detail: {selectedItem.item}</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div 
                  className="p-4 rounded-[var(--radius)] border-2"
                  style={{ 
                    borderColor: `var(--path-${selectedItem.path.toLowerCase()})`,
                    backgroundColor: `var(--path-${selectedItem.path.toLowerCase()}-light)`
                  }}
                >
                  <h4 className="mb-3">Recommended Path</h4>
                  <div className="flex items-center gap-3">
                    <div 
                      className="p-2 rounded-lg"
                      style={{ 
                        backgroundColor: `var(--path-${selectedItem.path.toLowerCase()})`,
                        color: `var(--path-${selectedItem.path.toLowerCase()}-foreground)`
                      }}
                    >
                      {pathIcon(selectedItem.path)}
                    </div>
                    <div>
                      <Badge variant={pathBadgeVariant(selectedItem.path)} className="text-sm px-3 py-1 mb-1">
                        {pathLabel(selectedItem.path)}
                      </Badge>
                      <p className="text-[var(--text-caption)] text-muted-foreground">
                        {pathDescription(selectedItem.path)}
                      </p>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="mb-2">Why this path</h4>
                  <p className="text-muted-foreground">{selectedItem.suitabilityReason}</p>
                </div>
                <div>
                  <h4 className="mb-2">Notes & Assumptions</h4>
                  <p className="text-muted-foreground">{selectedItem.notes}</p>
                </div>
                <div className="space-y-2">
                  <Button variant="outline" className="w-full">
                    Open Strategy Report
                  </Button>
                  <Button variant="outline" className="w-full">
                    Open Blueprint Node
                  </Button>
                  <Button variant="outline" className="w-full">
                    View in Layered Blueprint
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}