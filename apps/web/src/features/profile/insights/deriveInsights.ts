import type { Match, Profile } from "../../../api";

export type ProfileSnapshot = {
  summary?: string;
  targetRoles: string[];
  skills: string[];
};

export type StrengthInsight = {
  title: string;
  explanation: string;
  evidence: string;
};

export type GapInsight = {
  gap: string;
  severity: "addressable" | "blocking" | "unknown";
  occurrences: number;
  explanation: string;
};

export type MatchPattern = {
  label: string;
  value: string;
  detail: string;
};

export type RecommendationInsight = {
  title: string;
  explanation: string;
};

export function getProfileSnapshot(profile: Profile): ProfileSnapshot {
  const fields = profile.profile;
  return {
    summary: typeof fields.summary === "string" ? fields.summary : undefined,
    targetRoles: toStringList(fields.target_roles),
    skills: unique([
      ...toStringList(fields.skills),
      ...toStringList(fields.programming_languages),
      ...toStringList(fields.data_and_ai_tools),
    ]),
  };
}

export function deriveStrengths(matches: Match[]): StrengthInsight[] {
  const skillCounts = countValues(matches.flatMap((item) => item.match.matching_skills));
  const frequentSkills = [...skillCounts.entries()]
    .filter(([, count]) => count > 1)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3);
  return frequentSkills.map(([skill, count]) => ({
    title: `${skill} alignment`,
    explanation: `${skill} appears across several roles FoxPilot evaluated for you.`,
    evidence: `Matched in ${count} of ${matches.length} analyzed opportunities`,
  }));
}

export function deriveSkillGaps(matches: Match[]): GapInsight[] {
  const gaps = new Map<string, GapInsight>();
  for (const item of matches) {
    for (const gap of item.match.gap_analysis ?? []) {
      const existing = gaps.get(gap.gap);
      gaps.set(gap.gap, {
        gap: gap.gap,
        severity:
          existing?.severity === "blocking" || gap.severity === "blocking"
            ? "blocking"
            : existing?.severity === "addressable" || gap.severity === "addressable"
              ? "addressable"
              : "unknown",
        occurrences: (existing?.occurrences ?? 0) + 1,
        explanation: existing?.explanation ?? gap.explanation,
      });
    }
    for (const missingSkill of item.match.missing_skills) {
      if (!gaps.has(missingSkill))
        gaps.set(missingSkill, {
          gap: missingSkill,
          severity: "unknown",
          occurrences: 1,
          explanation: "Listed as missing for this opportunity; no severity was provided.",
        });
      else gaps.get(missingSkill)!.occurrences += 1;
    }
  }
  return [...gaps.values()].sort(
    (left, right) =>
      severityRank(left.severity) - severityRank(right.severity) ||
      right.occurrences - left.occurrences,
  );
}

export function deriveMatchPatterns(matches: Match[]): MatchPattern[] {
  if (matches.length === 0) return [];
  const average =
    matches.reduce((total, item) => total + item.match.match_score, 0) / matches.length;
  const highConfidence = matches.filter((item) => item.match.match_score >= 75).length;
  const recommendation = mostCommon(matches.map((item) => item.match.recommendation));
  const patterns: MatchPattern[] = [
    {
      label: "Average match score",
      value: `${Math.round(average)}%`,
      detail: `Across ${matches.length} analyzed opportunities`,
    },
    {
      label: "High-confidence matches",
      value: `${highConfidence}`,
      detail: "Roles scoring 75% or higher",
    },
  ];
  if (recommendation)
    patterns.push({
      label: "Most common recommendation",
      value: recommendation,
      detail: "Based on FoxPilot's current evaluations",
    });
  return patterns;
}

export function deriveRecommendations(
  matches: Match[],
  gaps: GapInsight[],
): RecommendationInsight[] {
  const recommendations: RecommendationInsight[] = [];
  for (const gap of gaps.filter((item) => item.severity === "addressable").slice(0, 2)) {
    recommendations.push({
      title: `Consider strengthening ${gap.gap}`,
      explanation: `${gap.gap} appears as an addressable gap in ${gap.occurrences} analyzed ${gap.occurrences === 1 ? "opportunity" : "opportunities"}.`,
    });
  }
  const frequentSkill = mostCommon(matches.flatMap((item) => item.match.matching_skills));
  if (frequentSkill)
    recommendations.push({
      title: `Lead with your ${frequentSkill} experience`,
      explanation: `${frequentSkill} is the most frequently matched skill across your current opportunities.`,
    });
  return recommendations.slice(0, 3);
}

function countValues(values: string[]) {
  const counts = new Map<string, number>();
  for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
  return counts;
}

function mostCommon(values: string[]) {
  return [...countValues(values).entries()].sort((left, right) => right[1] - left[1])[0]?.[0];
}

function severityRank(severity: GapInsight["severity"]) {
  return severity === "addressable" ? 0 : severity === "blocking" ? 1 : 2;
}

function toStringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function unique(values: string[]) {
  return [...new Set(values)];
}
