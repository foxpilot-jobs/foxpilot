type MetricsSummaryProps = {
  matches: number;
  saved: number;
  applied: number;
};

export function MetricsSummary({ applied, matches, saved }: MetricsSummaryProps) {
  return (
    <section className="metrics" aria-label="Application summary">
      <div>
        <span className="metric-value">{matches}</span>
        <span className="metric-label">analyzed matches</span>
      </div>
      <div>
        <span className="metric-value">{saved}</span>
        <span className="metric-label">saved to revisit</span>
      </div>
      <div>
        <span className="metric-value">{applied}</span>
        <span className="metric-label">applications sent</span>
      </div>
    </section>
  );
}
