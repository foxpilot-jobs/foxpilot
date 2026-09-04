import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  getApplications,
  getMatches,
  getProfile,
  updateApplication,
  type Application,
  type Match,
  type Profile,
} from "../../../api";
import { Button } from "../../../shared/ui/Button";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { ErrorState } from "../../../shared/ui/ErrorState";
import { MatchCard } from "../components/matches/MatchCard";
import { MatchFilters } from "../components/matches/MatchFilters";
import { MatchListSkeleton } from "../components/matches/MatchListSkeleton";
import { MatchesHeader } from "../components/matches/MatchesHeader";
import { MatchSummary } from "../components/matches/MatchSummary";
import { useAuth } from "../../auth/useAuth";

export function MatchesPage() {
  const { user } = useAuth();
  const [matches, setMatches] = useState<Match[]>([]);
  const [applications, setApplications] = useState<Record<string, Application>>({});
  const [profile, setProfile] = useState<Profile | null>(null);
  const [query, setQuery] = useState("");
  const [recommendation, setRecommendation] = useState("all");
  const [sort, setSort] = useState("score");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingJob, setUpdatingJob] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    const handleWorkspaceChange = () => setReloadToken((t) => t + 1);
    window.addEventListener("workspace-changed", handleWorkspaceChange);
    return () => window.removeEventListener("workspace-changed", handleWorkspaceChange);
  }, []);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    setError(null);
    void Promise.allSettled([
      getMatches({ limit: 200 }),
      getApplications({ limit: 200 }),
      getProfile(),
    ]).then(([matchesResult, applicationsResult, profileResult]) => {
      const failures: string[] = [];
      if (matchesResult.status === "fulfilled") setMatches(matchesResult.value.items);
      else failures.push("matches");
      if (applicationsResult.status === "fulfilled") {
        setApplications(
          Object.fromEntries(
            applicationsResult.value.items.map((application) => [application.job_id, application]),
          ),
        );
      } else failures.push("applications");
      if (profileResult.status === "fulfilled") setProfile(profileResult.value);
      else failures.push("profile");
      if (failures.length > 0) setError("Couldn't load all of your matching data.");
      setLoading(false);
    });
  }, [reloadToken, user?.user_id]);

  const visibleMatches = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return matches
      .filter(({ job, match }) => {
        const matchesRecommendation =
          recommendation === "all" || match.recommendation === recommendation;
        const searchable = `${job.title} ${job.company} ${job.location ?? ""}`.toLowerCase();
        return matchesRecommendation && (!normalizedQuery || searchable.includes(normalizedQuery));
      })
      .sort((left, right) => {
        if (sort === "newest")
          return (
            (Date.parse(right.job.last_seen_at ?? "") || 0) -
            (Date.parse(left.job.last_seen_at ?? "") || 0)
          );
        if (sort === "company") return left.job.company.localeCompare(right.job.company);
        if (sort === "title") return left.job.title.localeCompare(right.job.title);
        return right.match.match_score - left.match.match_score;
      });
  }, [matches, query, recommendation, sort]);

  if (!user) return null;

  async function handleStatus(jobId: string, status: Application["status"]) {
    setUpdatingJob(jobId);
    setError(null);
    try {
      const application = await updateApplication(jobId, status);
      setApplications((current) => ({ ...current, [jobId]: application }));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to update application");
    } finally {
      setUpdatingJob(null);
    }
  }

  const strongCount = matches.filter((item) => item.match.match_score >= 75).length;
  const applyCount = matches.filter((item) => item.match.recommendation === "APPLY").length;
  const hasActiveFilters = Boolean(query.trim()) || recommendation !== "all";

  return (
    <main className="matches-page">
      <MatchesHeader onQueryChange={setQuery} query={query} />
      {error && (
        <div className="matches-error">
          <ErrorState
            action={
              <Button
                type="button"
                variant="outline"
                onClick={() => setReloadToken((token) => token + 1)}
              >
                Try again
              </Button>
            }
            description={error}
            title="Couldn't load your matches"
          />
        </div>
      )}
      {loading ? (
        <MatchListSkeleton />
      ) : matches.length === 0 ? (
        <NoMatches profile={profile} />
      ) : (
        <>
          <MatchSummary recommended={applyCount} strong={strongCount} total={matches.length} />
          <MatchFilters
            onRecommendationChange={setRecommendation}
            onSortChange={setSort}
            recommendation={recommendation}
            sort={sort}
          />
          {visibleMatches.length === 0 ? (
            <FilteredEmptyState
              hasSearch={Boolean(query.trim())}
              onClear={() => {
                setQuery("");
                setRecommendation("all");
              }}
              recommendation={recommendation}
            />
          ) : (
            <section className="matches-list" aria-label="Personalized job matches">
              {visibleMatches.map((item) => (
                <MatchCard
                  application={applications[item.job_id]}
                  item={item}
                  key={item.job_id}
                  updating={updatingJob === item.job_id}
                  onStatusChange={(status) => void handleStatus(item.job_id, status)}
                />
              ))}
            </section>
          )}
          {!hasActiveFilters && (
            <p className="matches-list-note">
              Ranked by match score. FoxPilot uses the evidence available in your profile and each
              role.
            </p>
          )}
        </>
      )}
    </main>
  );
}

function NoMatches({ profile }: { profile: Profile | null }) {
  const hasProfileData = Boolean(profile && profile.resume_filename);
  return (
    <EmptyState
      action={
        <Link className="ui-button ui-button-primary ui-button-md" to="/app/profile">
          {hasProfileData ? "Run matching" : "Complete profile"}
        </Link>
      }
      description={
        hasProfileData
          ? "Run a scan and matching job from your profile to generate personalized opportunities."
          : "Upload your resume to give FoxPilot the context it needs to find roles that fit."
      }
      title="No matches yet"
    />
  );
}

function FilteredEmptyState({
  hasSearch,
  onClear,
  recommendation,
}: {
  hasSearch: boolean;
  onClear: () => void;
  recommendation: string;
}) {
  const title = hasSearch ? "No matches found" : `No ${recommendation.toLowerCase()} matches`;
  return (
    <EmptyState
      description={
        hasSearch
          ? "Try a broader search or clear the current filters."
          : "Choose another recommendation filter to see more of your matches."
      }
      title={title}
      action={
        <Button type="button" variant="outline" onClick={onClear}>
          Clear filters
        </Button>
      }
    />
  );
}
