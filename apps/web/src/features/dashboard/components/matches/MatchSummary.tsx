export function MatchSummary({
  total,
  strong,
  recommended,
}: {
  total: number;
  strong: number;
  recommended: number;
}) {
  return (
    <div className="matches-summary" aria-label="Match summary">
      <div>
        <strong>{total}</strong>
        <span>Total matches</span>
      </div>
      <div>
        <strong>{strong}</strong>
        <span>Strong matches</span>
      </div>
      <div>
        <strong>{recommended}</strong>
        <span>Recommended to apply</span>
      </div>
    </div>
  );
}
