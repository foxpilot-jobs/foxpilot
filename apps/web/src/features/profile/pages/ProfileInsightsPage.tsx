import { ArrowRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getMatches, getProfile, type Match, type Profile } from "../../../api";
import { Alert } from "../../../shared/ui/Alert";
import { Button } from "../../../shared/ui/Button";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { ErrorState } from "../../../shared/ui/ErrorState";
import { CareerSnapshot } from "../components/insights/CareerSnapshot";
import { InsightsHeader } from "../components/insights/InsightsHeader";
import { InsightsRecommendations } from "../components/insights/InsightsRecommendations";
import { InsightsSkeleton } from "../components/insights/InsightsSkeleton";
import { MatchEvidence } from "../components/insights/MatchEvidence";
import { MatchPatterns } from "../components/insights/MatchPatterns";
import { SkillGapsSection } from "../components/insights/SkillGapsSection";
import { StrengthsSection } from "../components/insights/StrengthsSection";
import {
  deriveMatchPatterns,
  deriveRecommendations,
  deriveSkillGaps,
  deriveStrengths,
  getProfileSnapshot,
} from "../insights/deriveInsights";
import { useAuth } from "../../auth/useAuth";

export function ProfileInsightsPage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [matchesError, setMatchesError] = useState(false);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    setLoadError(false);
    setMatchesError(false);
    void Promise.allSettled([getProfile(), getMatches()]).then(([profileResult, matchesResult]) => {
      if (profileResult.status === "fulfilled") setProfile(profileResult.value);
      else setLoadError(true);
      if (matchesResult.status === "fulfilled") setMatches(matchesResult.value);
      else setMatchesError(true);
      setLoading(false);
    });
  }, [retryToken, user?.user_id]);

  const insights = useMemo(() => {
    if (!profile) return null;
    return buildInsights(profile, matches);
  }, [matches, profile]);

  if (!user) return null;
  if (loading) return <InsightsSkeleton />;
  if (loadError)
    return (
      <main className="profile-insights-state">
        <ErrorState
          action={
            <Button type="button" onClick={() => setRetryToken((token) => token + 1)}>
              Try again
            </Button>
          }
          description="We couldn't load your profile insights. Please try again."
          title="Unable to load insights"
        />
      </main>
    );
  const hasProfileData = Boolean(profile && profile.resume_filename);
  if (!profile || !hasProfileData)
    return (
      <main className="profile-insights-page">
        <InsightsHeader />
        <EmptyState
          action={
            <Link className="ui-button ui-button-primary ui-button-md" to="/app/profile">
              Set up profile
            </Link>
          }
          description="Upload your resume to generate career insights."
          title="Build your profile first"
        />
      </main>
    );

  return (
    <main className="profile-insights-page">
      <InsightsHeader />
      {matchesError && (
        <div className="profile-insights-warning">
          <Alert variant="info">
            Your profile is available, but matching data could not be loaded. Profile-based insights
            are still shown.
          </Alert>
        </div>
      )}
      <ProfileInsightsContent
        insights={insights!}
        matches={matches}
        matchesAvailable={!matchesError}
      />
    </main>
  );
}

function ProfileInsightsContent({
  insights,
  matchesAvailable,
  matches,
}: {
  insights: ReturnType<typeof buildInsights>;
  matches: Match[];
  matchesAvailable: boolean;
}) {
  return (
    <>
      <CareerSnapshot snapshot={insights.snapshot} />
      <div className="profile-insights-columns">
        <div className="profile-insights-main">
          <StrengthsSection strengths={insights.strengths} />
          <SkillGapsSection gaps={insights.gaps} matchesAvailable={matchesAvailable} />
          <MatchEvidence matches={matches} />
        </div>
        <aside className="profile-insights-side">
          <MatchPatterns patterns={insights.patterns} />
          <InsightsRecommendations recommendations={insights.recommendations} />
        </aside>
      </div>
      <section className="profile-insights-cta">
        <div>
          <p className="ui-eyebrow">Next step</p>
          <h2>Ready to explore opportunities?</h2>
          <p>Use these insights to focus your attention on roles that fit your experience.</p>
        </div>
        <Link className="ui-button ui-button-primary ui-button-md" to="/app/matches">
          View your matches
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </section>
    </>
  );
}

function buildInsights(profile: Profile, matches: Match[]) {
  const gaps = deriveSkillGaps(matches);
  return {
    snapshot: getProfileSnapshot(profile),
    strengths: deriveStrengths(matches),
    gaps,
    patterns: deriveMatchPatterns(matches),
    recommendations: deriveRecommendations(matches, gaps),
  };
}
