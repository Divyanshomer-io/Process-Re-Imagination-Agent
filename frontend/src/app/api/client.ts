const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Types matching the backend Pydantic schemas
// ---------------------------------------------------------------------------

export interface EngagementMeta {
  id: string;
  thread_id: string;
  process_name: string;
  region: string;
  status: 'draft' | 'running' | 'ready' | 'error' | 'pending_approval';
  created_at: string;
}

export interface StepStatus {
  label: string;
  status: 'pending' | 'running' | 'complete';
}

export interface RunStatus {
  status: 'draft' | 'running' | 'ready' | 'error' | 'pending_approval';
  progress: number;
  current_phase: number;
  phase1_steps: StepStatus[];
  phase2_steps: StepStatus[];
  phase3_steps: StepStatus[];
  error: string | null;
  confidence_score: number | null;
  quality_gate_result: string | null;
}

export interface FrictionItem {
  id: string;
  manualAction: string;
  whereInProcess: string;
  region: string;
  evidenceCount: number;
  relatedPainPoints: string[];
  evidence: string[];
  pathClassification: 'A' | 'B' | 'C';
}

export interface PathItem {
  item: string;
  path: 'A' | 'B' | 'C';
  suitabilityReason: string;
  notes: string;
}

export interface UseCase {
  id: string;
  context: string;
  agentRole: string;
  mechanism: string;
  tech: string;
  value: string;
}

export interface BlueprintData {
  xml: string;
  mermaid: string;
  svg: string;
}

export interface UploadedFile {
  id: string;
  name: string;
  date: string;
}

// ---------------------------------------------------------------------------
// Engagement CRUD
// ---------------------------------------------------------------------------

export function createEngagement(processName: string, region: string) {
  return request<EngagementMeta>('/engagements', {
    method: 'POST',
    body: JSON.stringify({ process_name: processName, context_region: region }),
  });
}

export function getEngagement(id: string) {
  return request<EngagementMeta>(`/engagements/${id}`);
}

export function updateEngagement(id: string, data: Record<string, unknown>) {
  return request<EngagementMeta>(`/engagements/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// File operations
// ---------------------------------------------------------------------------

export async function uploadFile(
  engagementId: string,
  file: File,
  category: string,
  tag = '',
): Promise<UploadedFile> {
  const form = new FormData();
  form.append('file', file);
  form.append('category', category);
  form.append('tag', tag);

  const res = await fetch(`${BASE}/engagements/${engagementId}/files`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export function deleteFile(engagementId: string, fileId: string) {
  return request<{ status: string; id: string }>(
    `/engagements/${engagementId}/files/${fileId}`,
    { method: 'DELETE' },
  );
}

// ---------------------------------------------------------------------------
// Run management
// ---------------------------------------------------------------------------

export function startRun(engagementId: string) {
  return request<RunStatus>(`/engagements/${engagementId}/run`, { method: 'POST' });
}

export function pollRunStatus(engagementId: string) {
  return request<RunStatus>(`/engagements/${engagementId}/run/status`);
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

export function fetchFriction(engagementId: string) {
  return request<FrictionItem[]>(`/engagements/${engagementId}/results/friction`);
}

export function fetchPaths(engagementId: string) {
  return request<PathItem[]>(`/engagements/${engagementId}/results/paths`);
}

export function fetchStrategy(engagementId: string) {
  return request<{ markdown: string }>(`/engagements/${engagementId}/results/strategy`);
}

export function fetchBlueprint(engagementId: string) {
  return request<BlueprintData>(`/engagements/${engagementId}/results/blueprint`);
}

export function fetchUseCases(engagementId: string) {
  return request<UseCase[]>(`/engagements/${engagementId}/results/use-cases`);
}

// ---------------------------------------------------------------------------
// Approval
// ---------------------------------------------------------------------------

export function approve(engagementId: string, approver: string, notes = '') {
  return request<{ status: string; message: string }>(
    `/engagements/${engagementId}/approve`,
    {
      method: 'POST',
      body: JSON.stringify({ approver, notes }),
    },
  );
}
