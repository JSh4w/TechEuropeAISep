"use client";

import dynamic from "next/dynamic";
import { use, useEffect, useState } from "react";
import type { AreaFeedback, Polygon, SessionState } from "@/lib/types";

const SessionMap = dynamic(() => import("@/components/SessionMap"), { ssr: false });

const POLL_MS = 1000;

export default function SessionPage({ params }: PageProps<"/session/[id]">) {
  const { id } = use(params);
  const [state, setState] = useState<SessionState | null>(null);
  const [draft, setDraft] = useState<Polygon | null>(null); // local polygon while the user drags
  const [feedback, setFeedback] = useState<AreaFeedback | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Poll the workflow's `state` query until the session is done.
  useEffect(() => {
    let stop = false;
    async function poll() {
      const res = await fetch(`/api/session/${id}`);
      const body = await res.json();
      if (stop) return;
      if (!res.ok) setError(body.error);
      else setState(body as SessionState);
      if (res.ok && body.stage === "done") return;
      setTimeout(poll, POLL_MS);
    }
    poll();
    return () => {
      stop = true;
    };
  }, [id]);

  // Take the server's area whenever it changes (new suggestion or an accepted edit).
  useEffect(() => {
    if (state?.current_area) setDraft(state.current_area);
    if (state?.feedback) setFeedback(state.feedback);
  }, [state?.stage, state?.edits]); // eslint-disable-line react-hooks/exhaustive-deps

  async function post<T>(path: string, body?: unknown): Promise<T | null> {
    setBusy(true);
    setError(null);
    const res = await fetch(`/api/session/${id}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const json = await res.json();
    setBusy(false);
    if (!res.ok) {
      setError(json.error);
      return null;
    }
    return json as T;
  }

  async function submitArea(area: Polygon) {
    setDraft(area);
    const fb = await post<AreaFeedback>("/area", area);
    if (fb) setFeedback(fb);
  }

  if (!state) return <main className="loading">{error ?? "Connecting to session…"}</main>;

  const editable = state.stage === "awaiting_human";
  const center: [number, number] = [state.input?.lat ?? 51.6075, state.input?.lng ?? -1.241];

  return (
    <main className="session">
      <SessionMap
        center={center}
        titleBoundary={state.title_boundary}
        suggested={state.suggested_area}
        area={draft}
        ok={feedback?.ok ?? true}
        editable={editable && !busy}
        onChange={submitArea}
        onDraft={setDraft}
      />

      <aside className="panel">
        <header>
          <h1>Bessible</h1>
          <code className="muted">{id}</code>
        </header>

        <section>
          <span className={`stage stage-${state.stage}`}>{state.stage.replace("_", " ")}</span>
          <p>{state.step}</p>
        </section>

        {state.suggestion_rationale && (
          <section>
            <h2>AI suggestion</h2>
            <p>{state.suggestion_rationale}</p>
          </section>
        )}

        {feedback && (
          <section>
            <h2>Area check {busy && <span className="muted">· validating…</span>}</h2>
            <p>
              {feedback.area_m2.toLocaleString()} m² · fits ~{feedback.capacity_mw} MW
            </p>
            {feedback.issues.length ? (
              <ul className="issues">
                {feedback.issues.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            ) : (
              <p className="ok">✓ Looks good</p>
            )}
          </section>
        )}

        {editable && (
          <section className="actions">
            <p className="muted">Drag the white handles to adjust the area. {state.edits} edit(s) so far.</p>
            <button disabled={busy || !feedback?.ok} onClick={() => post("/confirm")}>
              Confirm area
            </button>
            {state.suggested_area && (
              <button className="secondary" disabled={busy} onClick={() => submitArea(state.suggested_area!)}>
                Reset to AI suggestion
              </button>
            )}
          </section>
        )}

        {(state.feasibility || state.suitability) && (
          <section>
            <h2>Assessment</h2>
            {state.feasibility && (
              <p>
                <b>Feasibility {Math.round(state.feasibility.score * 100)}%</b> — {state.feasibility.summary}
              </p>
            )}
            {state.suitability && (
              <p>
                <b>Suitability {Math.round(state.suitability.score * 100)}%</b> — {state.suitability.summary}
              </p>
            )}
          </section>
        )}

        {state.verdict && <section className="verdict">{state.verdict}</section>}

        {state.artifacts.length > 0 && (
          <section>
            <h2>Evidence</h2>
            <ul className="artifacts">
              {state.artifacts.map((a, i) => (
                <li key={i}>
                  <span className="muted">[{a.step}]</span> {a.claim} ({Math.round(a.confidence * 100)}%){" "}
                  <a href={a.source} target="_blank" rel="noreferrer">
                    source
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}

        {error && <p className="error">{error}</p>}
      </aside>
    </main>
  );
}
