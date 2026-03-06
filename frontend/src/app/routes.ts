import { createBrowserRouter } from "react-router";
import { AppShell } from "./components/layout/AppShell";
import { StartScreen } from "./components/screens/StartScreen";
import { Phase1Step1 } from "./components/screens/Phase1Step1";
import { Phase1Step2 } from "./components/screens/Phase1Step2";
import { Phase1Step3 } from "./components/screens/Phase1Step3";
import { Phase2RunSetup } from "./components/screens/Phase2RunSetup";
import { RunProgress } from "./components/screens/RunProgress";
import { Phase3Results } from "./components/screens/Phase3Results";
import { UseCaseDetail } from "./components/screens/UseCaseDetail";
import { ApplicationLandscape } from "./components/screens/ApplicationLandscape";
import { StakeholdersOwnership } from "./components/screens/StakeholdersOwnership";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: AppShell,
    children: [
      { index: true, Component: StartScreen },
      { path: "phase1/step1", Component: Phase1Step1 },
      { path: "phase1/step2", Component: Phase1Step2 },
      { path: "phase1/step3", Component: Phase1Step3 },
      { path: "phase2/setup", Component: Phase2RunSetup },
      { path: "run/progress", Component: RunProgress },
      { path: "phase3/results", Component: Phase3Results },
      { path: "phase3/use-case/:id", Component: UseCaseDetail },
      { path: "reference/landscape", Component: ApplicationLandscape },
      { path: "reference/stakeholders", Component: StakeholdersOwnership },
    ],
  },
]);
