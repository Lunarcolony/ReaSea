"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, TOPICS } from "@/lib/api";

export default function TopicsPage() {
  const [selected, setSelected] = useState<string[]>([]);
  const [role, setRole] = useState("researcher");
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    api
      .getPreferences()
      .then((data) => {
        if (data.topic_slugs?.length) setSelected(data.topic_slugs);
        if (data.research_role) setRole(data.research_role);
      })
      .finally(() => setLoading(false));
  }, []);

  const toggle = (slug: string) => {
    setSelected((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    );
  };

  const save = async () => {
    if (selected.length < 1) return;
    await api.updatePreferences(selected, role);
    router.push("/");
  };

  if (loading) return <div className="loading">Loading topics...</div>;

  return (
    <div className="page onboarding-page">
      <div className="page-header">
        <h1>Your research interests</h1>
        <p className="page-subtitle">Pick topics to personalize your feed.</p>
      </div>
      <div className="topic-grid">
        {TOPICS.map((t) => (
          <button
            key={t.slug}
            type="button"
            className={`topic-btn ${selected.includes(t.slug) ? "selected" : ""}`}
            onClick={() => toggle(t.slug)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="role-select">
        <label>I am a:</label>
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="student">Student</option>
          <option value="researcher">Researcher</option>
          <option value="pi">Principal Investigator</option>
          <option value="industry">Industry Professional</option>
        </select>
      </div>
      <button className="btn primary" onClick={save} disabled={selected.length < 1}>
        Save & refresh feed
      </button>
    </div>
  );
}
