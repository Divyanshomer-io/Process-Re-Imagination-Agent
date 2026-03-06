import { Link, useLocation } from "react-router";
import { cn } from "../ui/utils";
import {
  Home,
  Database,
  Cpu,
  BarChart3,
  Map,
  Users,
  Layers,
  ChevronRight
} from "lucide-react";

const mainNavItems = [
  { path: "/", label: "Start", icon: Home },
  { path: "/phase1/step1", label: "Inputs", icon: Database },
  { path: "/phase2/setup", label: "Reasoning Run", icon: Cpu },
  { path: "/phase3/results", label: "Results", icon: BarChart3 },
];

const referenceNavItems = [
  { path: "/reference/landscape", label: "Application Landscape", icon: Layers },
  { path: "/reference/stakeholders", label: "Stakeholders & Ownership", icon: Users },
];

export function LeftNav() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <aside className="flex flex-col w-72 border-r border-sidebar-border bg-sidebar text-white h-full transition-all duration-300 ease-in-out shadow-xl z-50">
      {/* Header / Logo Area */}
      <div className="p-6 border-b border-sidebar-border/20">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-sidebar-primary/20">
            <Cpu size={24} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight tracking-tight text-white">
              CPRE
            </h1>
            <p className="text-xs text-white/60 font-medium tracking-wide">
              Cognitive Engine
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto py-6 px-3 space-y-8">
        {/* Main Section */}
        <div className="space-y-1">
          <p className="px-4 text-xs font-bold text-white/40 uppercase tracking-wider mb-2">
            Process
          </p>
          {mainNavItems.map((item) => {
            const active = isActive(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "group flex items-center gap-3 px-4 py-3 rounded-[var(--radius)] transition-all duration-200 ease-in-out relative overflow-hidden",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-md font-bold"
                    : "text-white/80 hover:bg-sidebar-accent/10 hover:text-white"
                )}
              >
                {active && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-white/20" />
                )}
                <Icon
                  size={20}
                  className={cn(
                    "transition-transform duration-200",
                    active ? "scale-110" : "group-hover:scale-110"
                  )}
                  strokeWidth={active ? 2.5 : 2}
                />
                <span className="flex-1">{item.label}</span>
                {active && <ChevronRight size={16} className="opacity-50" />}
              </Link>
            );
          })}
        </div>

        {/* Reference Section */}
        <div className="space-y-1">
          <p className="px-4 text-xs font-bold text-white/40 uppercase tracking-wider mb-2">
            Reference
          </p>
          {referenceNavItems.map((item) => {
            const active = isActive(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "group flex items-center gap-3 px-4 py-3 rounded-[var(--radius)] transition-all duration-200 ease-in-out relative overflow-hidden",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-md font-bold"
                    : "text-white/80 hover:bg-sidebar-accent/10 hover:text-white"
                )}
              >
                {active && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-white/20" />
                )}
                <Icon
                  size={20}
                  className={cn(
                    "transition-transform duration-200",
                    active ? "scale-110" : "group-hover:scale-110"
                  )}
                  strokeWidth={active ? 2.5 : 2}
                />
                <span className="flex-1">{item.label}</span>
                {active && <ChevronRight size={16} className="opacity-50" />}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Footer Area */}
      <div className="p-4 border-t border-sidebar-border/20 bg-white/5">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-sidebar-primary to-[var(--path-b)] flex items-center justify-center text-xs font-bold text-black border-2 border-white/10">
            MD
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold text-white">McCain Design</span>
            <span className="text-xs text-white/50">System v2.0</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
