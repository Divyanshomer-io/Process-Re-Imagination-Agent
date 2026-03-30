import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { CognitiveFrictionTab } from "../tabs/CognitiveFrictionTab";
import { PathClassificationTab } from "../tabs/PathClassificationTab";
import { StrategyReportTab } from "../tabs/StrategyReportTab";
import { ProcessBlueprintTab } from "../tabs/ProcessBlueprintTab";
import { UseCaseCardsTab } from "../tabs/UseCaseCardsTab";

export function Phase3Results() {
  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border bg-card px-8 py-6">
        <h1>Phase 3 — Re‑Imagined Process Blueprint (The Outcome)</h1>
      </div>

      <Tabs defaultValue="friction" className="flex-1 flex flex-col">
        <TabsList className="border-b border-border px-8 py-0 h-auto bg-transparent rounded-none justify-start gap-6">
          <TabsTrigger value="friction" className="rounded-none border-b-2 border-transparent data-[state=active]:border-accent">
            Cognitive Friction Analysis
          </TabsTrigger>
          <TabsTrigger value="paths" className="rounded-none border-b-2 border-transparent data-[state=active]:border-accent">
            Path A/B/C Classification
          </TabsTrigger>
          <TabsTrigger value="strategy" className="rounded-none border-b-2 border-transparent data-[state=active]:border-accent">
            Strategy Report
          </TabsTrigger>
          <TabsTrigger value="blueprint" className="rounded-none border-b-2 border-transparent data-[state=active]:border-accent">
            Process Blueprint
          </TabsTrigger>
          <TabsTrigger value="usecases" className="rounded-none border-b-2 border-transparent data-[state=active]:border-accent">
            AI Agent Cards
          </TabsTrigger>
        </TabsList>

        <TabsContent value="friction" className="flex-1 overflow-auto m-0 p-8">
          <CognitiveFrictionTab />
        </TabsContent>
        <TabsContent value="paths" className="flex-1 overflow-auto m-0 p-8">
          <PathClassificationTab />
        </TabsContent>
        <TabsContent value="strategy" className="flex-1 overflow-auto m-0 p-8">
          <StrategyReportTab />
        </TabsContent>
        <TabsContent value="blueprint" className="flex-1 overflow-auto m-0 p-8">
          <ProcessBlueprintTab />
        </TabsContent>
        <TabsContent value="usecases" className="flex-1 overflow-auto m-0 p-8">
          <UseCaseCardsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}