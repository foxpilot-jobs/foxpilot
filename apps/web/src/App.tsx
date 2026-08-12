import { useEffect, useState } from "react";
import { getJobs, getMatches, saveJob, type Job, type Match } from "./api";

export function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savedJobs, setSavedJobs] = useState<Set<string>>(new Set());

  useEffect(() => {
    Promise.all([getJobs(), getMatches()])
      .then(([loadedJobs, loadedMatches]) => {
        setJobs(loadedJobs);
        setMatches(loadedMatches);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load jobs");
      });
  }, []);

  const matchByJob = new Map(matches.map((item) => [item.job_id, item.match]));

  async function handleSave(jobId: string) {
    try {
      await saveJob(jobId);
      setSavedJobs((current) => new Set(current).add(jobId));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to save job");
    }
  }

  return (
    <main className="shell">
      <nav className="topbar">
        <div className="brand-mark">FP</div>
        <div>
          <p className="eyebrow">FOXPILOT</p>
          <p className="muted">A sharper shortlist for your next move</p>
        </div>
        <button className="ghost-button" type="button">
          Settings
        </button>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow accent">TODAY'S SIGNAL</p>
          <h1>Spend less time searching. Spend more time choosing.</h1>
          <p className="hero-copy">
            Your local agent found the opportunities most aligned with your profile. Review the
            evidence, then decide what deserves your attention.
          </p>
        </div>
        <div className="signal-card">
          <span className="signal-number">{jobs.length}</span>
          <span className="muted">target roles ready</span>
        </div>
      </section>

      {error && (
        <div className="error-card">
          {error}. Start the API with <code>uvicorn services.api.app:app --reload</code>.
        </div>
      )}

      <section className="section-heading">
        <div>
          <p className="eyebrow">SHORTLIST</p>
          <h2>Worth a closer look</h2>
        </div>
        <span className="count-pill">{matches.length} analyzed</span>
      </section>

      <section className="job-grid">
        {jobs.map((job) => {
          const match = matchByJob.get(job.job_id ?? "");
          return (
            <article className="job-card" key={job.job_id ?? `${job.company}-${job.title}`}>
              <div className="card-topline">
                <span className="source-label">{job.source ?? "JOB SOURCE"}</span>
                {match && <span className="score">{match.match_score}% fit</span>}
              </div>
              <h3>{job.title}</h3>
              <p className="company">{job.company}</p>
              <p className="location">{job.location || "Location not specified"}</p>
              {match && <p className="reason">{match.reasons[0] ?? match.experience_match}</p>}
              <div className="card-actions">
                {job.url && (
                  <a href={job.url} target="_blank" rel="noreferrer">
                    View role
                  </a>
                )}
                <button type="button" onClick={() => job.job_id && handleSave(job.job_id)}>
                  {job.job_id && savedJobs.has(job.job_id) ? "Saved" : "Save"}
                </button>
              </div>
            </article>
          );
        })}
      </section>
    </main>
  );
}
