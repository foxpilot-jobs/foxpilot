# Product Brief

## Problem

Job seekers spend substantial time searching across fragmented sources, rereading repetitive listings, and deciding whether their experience is relevant. Existing automation often creates noise, depends on paid APIs, exposes personal data, or attempts unsafe auto-application behavior.

## User

The initial user is a technical professional actively searching for a role. The product must later support any job seeker who can provide a resume and define preferences, without encoding one person's role taxonomy, location, or career history into the application.

## Promise

FoxPilot turns a broad job search into a prioritized, explainable shortlist while keeping the user and their data in control.

## MVP

- Local resume import and structured profile.
- Configurable target roles and constraints.
- Reliable job ingestion from a small number of compliant sources.
- Deterministic deduplication and relevance filtering.
- Local LLM matching with transparent evidence.
- SQLite-backed saved jobs and application status.
- Useful CLI summaries and exports.

## Non-goals

- Automated applications.
- Recruiter outreach automation.
- A hosted account system in the first release.
- Guaranteed job-board coverage.
- Objective or legally meaningful hiring predictions.

## Success Measures

- Time from setup to first useful shortlist.
- Qualified opportunities reviewed per hour.
- Percentage of recommendations the user considers relevant.
- Duplicate and irrelevant listings avoided.
- Saved-to-applied conversion.
- Interview conversion tracked by the user.
- Local workflow completion without a paid API.
