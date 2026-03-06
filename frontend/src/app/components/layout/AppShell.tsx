import { Outlet, useLocation } from "react-router";
import { LeftNav } from "./LeftNav";
import { TopHeader } from "./TopHeader";

export function AppShell() {
  const location = useLocation();
  const isStartScreen = location.pathname === "/";

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {!isStartScreen && <LeftNav />}
      <div className="flex flex-1 flex-col overflow-hidden">
        {!isStartScreen && <TopHeader />}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}