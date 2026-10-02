// Artifacts are the chat's results, gathered from its messages: each answered result has an
// artifact {id, version, title} in its payload, and a follow-up that refines a result is the next
// version of the same artifact. Nothing is stored twice; the panel reads what the chat loaded.

import type { AssistantPayload } from "./api";

export interface ArtifactVersion {
  version: number;
  messageId: string;
  payload: AssistantPayload;
}

export interface Artifact {
  id: string;
  title: string; // of the newest version
  versions: ArtifactVersion[]; // oldest first
}

export function collectArtifacts(messages: { key: string; payload?: AssistantPayload | null }[]): Artifact[] {
  const byId = new Map<string, Artifact>();
  for (const m of messages) {
    const a = m.payload?.artifact;
    if (!a || !m.payload?.table) continue;
    const artifact = byId.get(a.id) ?? { id: a.id, title: a.title, versions: [] };
    artifact.title = a.title;
    artifact.versions.push({ version: a.version, messageId: m.key, payload: m.payload });
    byId.set(a.id, artifact);
  }
  return [...byId.values()];
}
