"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export default function Home() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function start(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    const res = await fetch("/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_url: form.get("property_url"),
        lat: Number(form.get("lat")),
        lng: Number(form.get("lng")),
        battery_mw: Number(form.get("battery_mw")),
      }),
    });
    const body = await res.json();
    if (!res.ok) {
      setError(body.error);
      setBusy(false);
      return;
    }
    router.push(`/session/${body.id}`);
  }

  return (
    <main className="home">
      <h1>Bessible</h1>
      <p className="muted">Could a battery go here, and should it?</p>
      <form onSubmit={start} className="start-form">
        <label>
          Property link
          <input name="property_url" defaultValue="https://example.com/property/123" required />
        </label>
        <div className="row">
          <label>
            Lat
            <input name="lat" type="number" step="any" defaultValue={51.6075} />
          </label>
          <label>
            Lng
            <input name="lng" type="number" step="any" defaultValue={-1.241} />
          </label>
          <label>
            Battery (MW)
            <input name="battery_mw" type="number" step="0.5" min="0.5" defaultValue={5} />
          </label>
        </div>
        <button disabled={busy}>{busy ? "Starting…" : "Assess site"}</button>
        {error && <p className="error">{error}</p>}
      </form>
    </main>
  );
}
