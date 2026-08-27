import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Match } from "../../../../api";
import { MatchGapAnalysis } from "./MatchGapAnalysis";

const match: Match["match"] = {
  match_score: 42,
  recommendation: "CONSIDER",
  reasons: [],
  matching_skills: [],
  missing_skills: ["SQL"],
  experience_match: "",
  concerns: [],
  gap_analysis: [{ gap: "", severity: "blocking", explanation: "" }],
};

describe("MatchGapAnalysis", () => {
  it("keeps gap cards informative when the API omits gap copy", () => {
    render(<MatchGapAnalysis match={match} />);

    expect(screen.getAllByText("SQL")).not.toHaveLength(0);
    expect(
      screen.getByText("Review this requirement against your experience before applying."),
    ).toBeInTheDocument();
    expect(screen.getByText("blocking")).toBeInTheDocument();
  });
});
