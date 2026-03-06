import { create } from 'zustand';

interface EngagementState {
  processName: string;
  region: string;
  painPoints: string;
  painPointsList: string[];
  status: 'draft' | 'running' | 'ready';
  asIsFiles: { name: string; date: Date; id: string }[];
  regionalVariations: boolean;
  regionalNuances: string;
  kpis: { name: string; baseline: string; target: string; notes: string; id: string }[];
  strategicGuardrails: string;
  benchmarkFiles: { name: string; tag: string; id: string }[];
  painPointFiles: { name: string; date: Date; id: string }[];
  runProgress: number;
  
  setProcessName: (name: string) => void;
  setRegion: (region: string) => void;
  setPainPoints: (painPoints: string) => void;
  setPainPointsList: (painPoints: string[]) => void;
  setStatus: (status: 'draft' | 'running' | 'ready') => void;
  addAsIsFile: (file: { name: string; date: Date; id: string }) => void;
  removeAsIsFile: (id: string) => void;
  setRegionalVariations: (value: boolean) => void;
  setRegionalNuances: (nuances: string) => void;
  addKpi: () => void;
  updateKpi: (id: string, field: string, value: string) => void;
  removeKpi: (id: string) => void;
  setStrategicGuardrails: (guardrails: string) => void;
  addBenchmarkFile: (file: { name: string; tag: string; id: string }) => void;
  removeBenchmarkFile: (id: string) => void;
  addPainPointFile: (file: { name: string; date: Date; id: string }) => void;
  removePainPointFile: (id: string) => void;
  setRunProgress: (progress: number) => void;
}

export const useEngagementStore = create<EngagementState>((set) => ({
  processName: '',
  region: '',
  painPoints: '',
  painPointsList: [],
  status: 'draft',
  asIsFiles: [],
  regionalVariations: false,
  regionalNuances: '',
  kpis: [],
  strategicGuardrails: '',
  benchmarkFiles: [],
  painPointFiles: [],
  runProgress: 0,
  
  setProcessName: (name) => set({ processName: name }),
  setRegion: (region) => set({ region }),
  setPainPoints: (painPoints) => set({ painPoints }),
  setPainPointsList: (painPointsList) => set({ painPointsList }),
  setStatus: (status) => set({ status }),
  addAsIsFile: (file) => set((state) => ({ asIsFiles: [...state.asIsFiles, file] })),
  removeAsIsFile: (id) => set((state) => ({ asIsFiles: state.asIsFiles.filter(f => f.id !== id) })),
  setRegionalVariations: (value) => set({ regionalVariations: value }),
  setRegionalNuances: (nuances) => set({ regionalNuances: nuances }),
  addKpi: () => set((state) => ({
    kpis: [...state.kpis, { name: '', baseline: '', target: '', notes: '', id: Math.random().toString() }]
  })),
  updateKpi: (id, field, value) => set((state) => ({
    kpis: state.kpis.map(kpi => kpi.id === id ? { ...kpi, [field]: value } : kpi)
  })),
  removeKpi: (id) => set((state) => ({ kpis: state.kpis.filter(k => k.id !== id) })),
  setStrategicGuardrails: (guardrails) => set({ strategicGuardrails: guardrails }),
  addBenchmarkFile: (file) => set((state) => ({ benchmarkFiles: [...state.benchmarkFiles, file] })),
  removeBenchmarkFile: (id) => set((state) => ({ benchmarkFiles: state.benchmarkFiles.filter(f => f.id !== id) })),
  addPainPointFile: (file) => set((state) => ({ painPointFiles: [...state.painPointFiles, file] })),
  removePainPointFile: (id) => set((state) => ({ painPointFiles: state.painPointFiles.filter(f => f.id !== id) })),
  setRunProgress: (progress) => set({ runProgress: progress }),
}));