/**
 * Drop-in replacement for engagementStore.ts.
 *
 * Key behaviors:
 *  - File upload opens a real native file picker and stores the File blob.
 *  - triggerRun() creates a backend engagement, uploads files, starts the
 *    agent, and polls for real progress.
 *  - Real-time phase steps / progress are exposed so RunProgress can read them.
 */

import { create } from 'zustand';
import {
  createEngagement,
  uploadFile,
  deleteFile as apiDeleteFile,
  startRun,
  pollRunStatus,
  approve as apiApprove,
  updateEngagement,
} from '../api/client';
import { loadResults, clearResults } from '../data/apiResults';

const ACCEPTED_FILE_TYPES = [
  '.txt', '.csv', '.md',
  '.pdf',
  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff',
  '.pptx',
].join(',');

// ---------------------------------------------------------------------------
// Native file picker helper
// ---------------------------------------------------------------------------

function pickFile(accept: string): Promise<File | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.style.display = 'none';
    document.body.appendChild(input);

    let resolved = false;
    const done = (file: File | null) => {
      if (resolved) return;
      resolved = true;
      if (document.body.contains(input)) document.body.removeChild(input);
      resolve(file);
    };

    input.addEventListener('change', () => done(input.files?.[0] ?? null));
    input.addEventListener('cancel', () => done(null));

    window.addEventListener('focus', function onFocus() {
      window.removeEventListener('focus', onFocus);
      setTimeout(() => done(null), 500);
    });

    input.click();
  });
}

// ---------------------------------------------------------------------------
// Step status type
// ---------------------------------------------------------------------------

interface StepStatus {
  label: string;
  status: 'pending' | 'running' | 'complete';
}

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

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

  // Integration fields
  engagementId: string | null;
  threadId: string | null;
  backendStatus: string;
  confidenceScore: number | null;
  qualityGateResult: string | null;
  _realRunTriggered: boolean;
  _fileBlobs: Record<string, File>;

  // Real-time progress from backend
  realPhase1Steps: StepStatus[];
  realPhase2Steps: StepStatus[];
  realPhase3Steps: StepStatus[];
  realCurrentPhase: number;
  realProgress: number;
  runComplete: boolean;
  runError: string | null;

  // Actions
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

  ensureEngagement: () => Promise<string>;
  triggerRun: () => Promise<void>;
  approveRun: (approver: string, notes?: string) => Promise<void>;
}

let _pollingInterval: ReturnType<typeof setInterval> | null = null;

function _stopPolling() {
  if (_pollingInterval) {
    clearInterval(_pollingInterval);
    _pollingInterval = null;
  }
}

export const useEngagementStore = create<EngagementState>((set, get) => ({
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

  engagementId: null,
  threadId: null,
  backendStatus: 'draft',
  confidenceScore: null,
  qualityGateResult: null,
  _realRunTriggered: false,
  _fileBlobs: {},

  realPhase1Steps: [],
  realPhase2Steps: [],
  realPhase3Steps: [],
  realCurrentPhase: 0,
  realProgress: 0,
  runComplete: false,
  runError: null,

  // -----------------------------------------------------------------------
  // Basic setters
  // -----------------------------------------------------------------------

  setProcessName: (name) => set({ processName: name }),
  setRegion: (region) => set({ region }),
  setPainPoints: (painPoints) => set({ painPoints }),
  setPainPointsList: (painPointsList) => set({ painPointsList }),

  setStatus: (status) => {
    set({ status });
    if (status === 'ready' && !get()._realRunTriggered) {
      set({ _realRunTriggered: true });
      get().triggerRun();
    }
  },

  // -----------------------------------------------------------------------
  // FILE UPLOAD — open real file picker
  // -----------------------------------------------------------------------

  addAsIsFile: (_mockFile) => {
    pickFile(ACCEPTED_FILE_TYPES).then(async (realFile) => {
      if (!realFile) return;
      const fileId = Math.random().toString(36).slice(2);
      const entry = { name: realFile.name, date: new Date(), id: fileId };
      set((s) => ({
        asIsFiles: [...s.asIsFiles, entry],
        _fileBlobs: { ...s._fileBlobs, [fileId]: realFile },
      }));
      const eid = get().engagementId;
      if (eid) {
        try {
          await uploadFile(eid, realFile, 'as_is');
        } catch { /* uploaded at run time */ }
      }
    });
  },

  removeAsIsFile: (id) => {
    const state = get();
    if (state.engagementId) apiDeleteFile(state.engagementId, id).catch(() => {});
    set((s) => {
      const blobs = { ...s._fileBlobs };
      delete blobs[id];
      return { asIsFiles: s.asIsFiles.filter((f) => f.id !== id), _fileBlobs: blobs };
    });
  },

  addPainPointFile: (_mockFile) => {
    pickFile(ACCEPTED_FILE_TYPES).then(async (realFile) => {
      if (!realFile) return;
      const fileId = Math.random().toString(36).slice(2);
      const entry = { name: realFile.name, date: new Date(), id: fileId };
      set((s) => ({
        painPointFiles: [...s.painPointFiles, entry],
        _fileBlobs: { ...s._fileBlobs, [fileId]: realFile },
      }));
      const eid = get().engagementId;
      if (eid) {
        try {
          await uploadFile(eid, realFile, 'pain_point');
        } catch { /* uploaded at run time */ }
      }
    });
  },

  removePainPointFile: (id) => {
    const state = get();
    if (state.engagementId) apiDeleteFile(state.engagementId, id).catch(() => {});
    set((s) => {
      const blobs = { ...s._fileBlobs };
      delete blobs[id];
      return { painPointFiles: s.painPointFiles.filter((f) => f.id !== id), _fileBlobs: blobs };
    });
  },

  addBenchmarkFile: (_mockFile) => {
    pickFile(ACCEPTED_FILE_TYPES).then(async (realFile) => {
      if (!realFile) return;
      const tag = (_mockFile as any).tag || 'Benchmark';
      const fileId = Math.random().toString(36).slice(2);
      const entry = { name: realFile.name, tag, id: fileId };
      set((s) => ({
        benchmarkFiles: [...s.benchmarkFiles, entry],
        _fileBlobs: { ...s._fileBlobs, [fileId]: realFile },
      }));
      const eid = get().engagementId;
      if (eid) {
        try {
          await uploadFile(eid, realFile, 'benchmark', tag);
        } catch { /* uploaded at run time */ }
      }
    });
  },

  removeBenchmarkFile: (id) => {
    const state = get();
    if (state.engagementId) apiDeleteFile(state.engagementId, id).catch(() => {});
    set((s) => {
      const blobs = { ...s._fileBlobs };
      delete blobs[id];
      return { benchmarkFiles: s.benchmarkFiles.filter((f) => f.id !== id), _fileBlobs: blobs };
    });
  },

  setRegionalVariations: (value) => set({ regionalVariations: value }),
  setRegionalNuances: (nuances) => set({ regionalNuances: nuances }),

  addKpi: () =>
    set((state) => ({
      kpis: [
        ...state.kpis,
        { name: '', baseline: '', target: '', notes: '', id: Math.random().toString() },
      ],
    })),

  updateKpi: (id, field, value) =>
    set((state) => ({
      kpis: state.kpis.map((kpi) => (kpi.id === id ? { ...kpi, [field]: value } : kpi)),
    })),

  removeKpi: (id) => set((state) => ({ kpis: state.kpis.filter((k) => k.id !== id) })),
  setStrategicGuardrails: (guardrails) => set({ strategicGuardrails: guardrails }),
  setRunProgress: (progress) => set({ runProgress: progress }),

  // -----------------------------------------------------------------------
  // Integration actions
  // -----------------------------------------------------------------------

  ensureEngagement: async () => {
    const state = get();
    if (state.engagementId) return state.engagementId;

    const name = state.processName || 'Untitled Process';
    const region = state.region || 'Global';
    const engagement = await createEngagement(name, region);
    set({ engagementId: engagement.id, threadId: engagement.thread_id });

    const patchData: Record<string, unknown> = {};
    if (state.painPoints) patchData.pain_points = state.painPoints;
    if (state.painPointsList.length > 0) patchData.pain_points_list = state.painPointsList;
    if (state.regionalVariations) patchData.regional_variations = state.regionalVariations;
    if (state.regionalNuances) patchData.regional_nuances = state.regionalNuances;
    if (state.strategicGuardrails) patchData.strategic_guardrails = state.strategicGuardrails;

    if (Object.keys(patchData).length > 0) {
      await updateEngagement(engagement.id, patchData).catch(() => {});
    }

    for (const f of state.asIsFiles) {
      const blob = state._fileBlobs[f.id];
      if (blob) {
        try { await uploadFile(engagement.id, blob, 'as_is'); } catch { /* best-effort */ }
      }
    }
    for (const f of state.painPointFiles) {
      const blob = state._fileBlobs[f.id];
      if (blob) {
        try { await uploadFile(engagement.id, blob, 'pain_point'); } catch { /* best-effort */ }
      }
    }
    for (const f of state.benchmarkFiles) {
      const blob = state._fileBlobs[f.id];
      if (blob) {
        try { await uploadFile(engagement.id, blob, 'benchmark', f.tag); } catch { /* best-effort */ }
      }
    }

    return engagement.id;
  },

  triggerRun: async () => {
    try {
      const state = get();
      const hasFiles = state.asIsFiles.length > 0 || state.painPointFiles.length > 0 || state.benchmarkFiles.length > 0;
      if (!hasFiles) {
        set({ backendStatus: 'error', runComplete: true, runError: 'No files uploaded. Please upload at least one As-Is process file in Phase 1.' });
        return;
      }
      const engagementId = await get().ensureEngagement();
      set({ backendStatus: 'running', runComplete: false, runError: null });
      clearResults();

      const initialStatus = await startRun(engagementId);

      set({
        realPhase1Steps: initialStatus.phase1_steps ?? [],
        realPhase2Steps: initialStatus.phase2_steps ?? [],
        realPhase3Steps: initialStatus.phase3_steps ?? [],
        realCurrentPhase: initialStatus.current_phase ?? 1,
        realProgress: initialStatus.progress ?? 0,
      });

      _stopPolling();
      let _pollFailures = 0;
      _pollingInterval = setInterval(async () => {
        try {
          const rs = await pollRunStatus(engagementId);
          _pollFailures = 0;
          set({
            backendStatus: rs.status,
            confidenceScore: rs.confidence_score,
            qualityGateResult: rs.quality_gate_result,
            realPhase1Steps: rs.phase1_steps ?? get().realPhase1Steps,
            realPhase2Steps: rs.phase2_steps ?? get().realPhase2Steps,
            realPhase3Steps: rs.phase3_steps ?? get().realPhase3Steps,
            realCurrentPhase: rs.current_phase ?? get().realCurrentPhase,
            realProgress: rs.progress ?? get().realProgress,
          });

          if (rs.status === 'ready') {
            _stopPolling();
            set({ runComplete: true, backendStatus: rs.status, realProgress: 100 });
            await loadResults(engagementId);
          } else if (rs.status === 'error') {
            _stopPolling();
            set({ runComplete: true, backendStatus: 'error', runError: rs.error || 'Agent run failed' });
          }
        } catch (pollErr: any) {
          _pollFailures++;
          if (_pollFailures >= 15) {
            _stopPolling();
            set({ backendStatus: 'error', runComplete: true, runError: 'Lost connection to backend — the server may have restarted. Please try again.' });
          }
        }
      }, 2000);
    } catch (err: any) {
      set({ backendStatus: 'error', runComplete: true, runError: err?.message || 'Failed to start run' });
    }
  },

  approveRun: async (approver, notes = '') => {
    const state = get();
    if (!state.engagementId) return;
    set({ backendStatus: 'running', runComplete: false });
    await apiApprove(state.engagementId, approver, notes);

    _stopPolling();
    _pollingInterval = setInterval(async () => {
      try {
        const rs = await pollRunStatus(state.engagementId!);
        set({
          backendStatus: rs.status,
          realPhase1Steps: rs.phase1_steps ?? get().realPhase1Steps,
          realPhase2Steps: rs.phase2_steps ?? get().realPhase2Steps,
          realPhase3Steps: rs.phase3_steps ?? get().realPhase3Steps,
          realProgress: rs.progress ?? get().realProgress,
        });

        if (rs.status === 'ready') {
          _stopPolling();
          set({ runComplete: true, realProgress: 100 });
          await loadResults(state.engagementId!);
        } else if (rs.status === 'error') {
          _stopPolling();
          set({ runComplete: true, runError: rs.error || 'Resume failed' });
        }
      } catch {
        // Retry
      }
    }, 2000);
  },
}));
