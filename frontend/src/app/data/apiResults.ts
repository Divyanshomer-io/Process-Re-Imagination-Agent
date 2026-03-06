/**
 * Drop-in replacement for mockResults.ts.
 *
 * When the Vite plugin is active, every component that imports from
 * "../../data/mockResults" will resolve here instead.
 *
 * Uses a Proxy pattern so that every read of the exported arrays/strings
 * returns the LATEST data from the internal Zustand micro-store.
 */

import { create } from 'zustand';
import type { FrictionItem, PathItem, UseCase } from '../api/client';
import {
  fetchFriction,
  fetchPaths,
  fetchStrategy,
  fetchBlueprint,
  fetchUseCases,
} from '../api/client';

// ---------------------------------------------------------------------------
// Internal reactive store — holds the live API data
// ---------------------------------------------------------------------------

interface ResultsState {
  frictionData: FrictionItem[];
  pathData: PathItem[];
  strategyReport: string;
  blueprintXML: string;
  blueprintMermaid: string;
  blueprintSVG: string;
  useCases: UseCase[];
  loaded: boolean;
  loading: boolean;
  engagementId: string | null;
}

export const useResultsStore = create<ResultsState>(() => ({
  frictionData: [],
  pathData: [],
  strategyReport: '',
  blueprintXML: '',
  blueprintMermaid: '',
  blueprintSVG: '',
  useCases: [],
  loaded: false,
  loading: false,
  engagementId: null,
}));

/**
 * Fetch all results from the backend and populate the store.
 * Called by apiEngagementStore when a run reaches completion.
 */
export async function loadResults(engagementId: string): Promise<void> {
  const current = useResultsStore.getState();
  if (current.loading || (current.loaded && current.engagementId === engagementId)) return;

  useResultsStore.setState({ loading: true });

  try {
    const [friction, paths, strategy, blueprint, useCases] = await Promise.allSettled([
      fetchFriction(engagementId),
      fetchPaths(engagementId),
      fetchStrategy(engagementId),
      fetchBlueprint(engagementId),
      fetchUseCases(engagementId),
    ]);

    useResultsStore.setState({
      frictionData: friction.status === 'fulfilled' ? friction.value : [],
      pathData: paths.status === 'fulfilled' ? paths.value : [],
      strategyReport: strategy.status === 'fulfilled' ? strategy.value.markdown : '',
      blueprintXML: blueprint.status === 'fulfilled' ? blueprint.value.xml : '',
      blueprintMermaid: blueprint.status === 'fulfilled' ? blueprint.value.mermaid : '',
      blueprintSVG: blueprint.status === 'fulfilled' ? blueprint.value.svg : '',
      useCases: useCases.status === 'fulfilled' ? useCases.value : [],
      loaded: true,
      loading: false,
      engagementId,
    });
  } catch {
    useResultsStore.setState({ loading: false });
  }
}

export function clearResults(): void {
  useResultsStore.setState({
    frictionData: [],
    pathData: [],
    strategyReport: '',
    blueprintXML: '',
    blueprintMermaid: '',
    blueprintSVG: '',
    useCases: [],
    loaded: false,
    loading: false,
    engagementId: null,
  });
}

// ---------------------------------------------------------------------------
// Proxy-backed exports — always return the freshest data from the store
// ---------------------------------------------------------------------------

function liveArray<T>(selector: () => T[]): T[] {
  return new Proxy([] as unknown as T[], {
    get(_target, prop, _receiver) {
      const current = selector();
      if (prop === Symbol.iterator) return current[Symbol.iterator].bind(current);
      const value = (current as any)[prop];
      if (typeof value === 'function') return value.bind(current);
      return value;
    },
    has(_target, prop) {
      return prop in selector();
    },
    ownKeys() {
      return Reflect.ownKeys(selector());
    },
    getOwnPropertyDescriptor(_target, prop) {
      return Object.getOwnPropertyDescriptor(selector(), prop);
    },
  }) as T[];
}

function liveString(selector: () => string): string {
  return new Proxy(new String(''), {
    get(_target, prop) {
      const current = selector();
      if (prop === Symbol.toPrimitive || prop === 'valueOf') return () => current;
      if (prop === 'toString') return () => current;
      if (prop === 'length') return current.length;
      const wrapped = Object(current);
      const value = wrapped[prop as any];
      if (typeof value === 'function') return value.bind(current);
      return value;
    },
    has(_target, prop) {
      return prop in Object(selector());
    },
  }) as unknown as string;
}

// Named exports that mirror mockResults.ts — components import these directly.
export const mockFrictionData = liveArray(() => useResultsStore.getState().frictionData);
export const mockPathData = liveArray(() => useResultsStore.getState().pathData);
export const mockUseCases = liveArray(() => useResultsStore.getState().useCases);

export const mockStrategyReport = liveString(() => useResultsStore.getState().strategyReport);
export const mockBlueprintXML = liveString(() => useResultsStore.getState().blueprintXML);
