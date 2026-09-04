"""Work Arrangement & Remote Location Eligibility Parser.

Parses job location, work type, and description text into structured work mode,
remote scope, target countries/regions, candidate eligibility (e.g., India eligibility),
and user-facing display labels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkArrangement:
    work_mode: str  # "remote", "hybrid", "onsite", "unknown"
    remote_scope: str  # "worldwide", "country_specific", "region_specific", "unknown"
    remote_countries: list[str] = field(default_factory=list)
    remote_regions: list[str] = field(default_factory=list)
    is_india_eligible: bool | None = None  # True: eligible, False: ineligible, None: unknown
    display_label: str = "❓ Work mode unknown"

    def as_dict(self) -> dict[str, Any]:
        return {
            "work_mode": self.work_mode,
            "remote_scope": self.remote_scope,
            "remote_countries": self.remote_countries,
            "remote_regions": self.remote_regions,
            "is_india_eligible": self.is_india_eligible,
            "display_label": self.display_label,
        }


# Country pattern mappings to canonical names and ISO codes / flags
COUNTRY_PATTERNS = [
    (r"\b(india|ind)\b", "India", "🇮🇳"),
    (r"\b(united states|usa|u\.s\.a?|u\.s\.)\b", "United States", "🇺🇸"),
    (r"\b(germany|deutschland)\b", "Germany", "🇩🇪"),
    (r"\b(united kingdom|uk|england|great britain|gb)\b", "United Kingdom", "🇬🇧"),
    (r"\b(canada|can)\b", "Canada", "🇨🇦"),
    (r"\b(australia|au)\b", "Australia", "🇦🇺"),
    (r"\b(mexico|mx)\b", "Mexico", "🇲🇽"),
    (r"\b(france|fr)\b", "France", "🇫🇷"),
    (r"\b(netherlands|nl)\b", "Netherlands", "🇳🇱"),
    (r"\b(spain|es)\b", "Spain", "🇪🇸"),
    (r"\b(brazil|brasil)\b", "Brazil", "🇧🇷"),
]

REGION_PATTERNS = [
    (r"\b(asia|apac|southeast asia|se asia)\b", "Asia", "🌏"),
    (r"\b(europe|emea|eu|european union)\b", "Europe", "🇪🇺"),
    (r"\b(latam|latin america)\b", "LATAM", "🌎"),
    (r"\b(north america)\b", "North America", "🌎"),
]


def _normalize_text(val: Any) -> str:
    if not val:
        return ""
    return re.sub(r"\s+", " ", str(val).lower()).strip()


def parse_work_arrangement(job: dict[str, Any]) -> WorkArrangement:
    """Parse work mode and location eligibility from job title, location, work_type, and description."""
    existing = job.get("work_arrangement")
    if isinstance(existing, dict) and "work_mode" in existing and "display_label" in existing:
        return WorkArrangement(
            work_mode=existing.get("work_mode", "unknown"),
            remote_scope=existing.get("remote_scope", "unknown"),
            remote_countries=existing.get("remote_countries") or [],
            remote_regions=existing.get("remote_regions") or [],
            is_india_eligible=existing.get("is_india_eligible"),
            display_label=existing.get("display_label", "❓ Work mode unknown"),
        )
    title_raw = str(job.get("title", ""))
    loc_raw = str(job.get("location", ""))
    work_type_raw = str(job.get("work_type", ""))
    desc_raw = str(job.get("description", ""))

    title_norm = _normalize_text(title_raw)
    loc_norm = _normalize_text(loc_raw)
    work_type_norm = _normalize_text(work_type_raw)
    desc_norm = _normalize_text(desc_raw)

    combined_short = f"{title_norm} | {loc_norm} | {work_type_norm}"
    full_text = f"{combined_short} \n {desc_norm}"

    # 1. Determine Work Mode (remote, hybrid, onsite, unknown)
    work_mode = "unknown"
    source_norm = _normalize_text(job.get("source", ""))

    remote_pattern = r"\b(remote|wfh|work from home|telecommute|anywhere|distributed|virtual|remote-first|remote first|fully remote|work from anywhere|remote option|remote work|remotely|work remotely|100% remote)\b"
    hybrid_pattern = r"\b(hybrid|flexible work|partially remote|part-remote|hybrid work|in-office and remote|office / remote|office/remote|flexible working)\b"
    onsite_pattern = r"\b(on-site|onsite|in-office|in office|office based|office-based|on site|on-site role|in-person|in person|office location)\b"

    if re.search(remote_pattern, combined_short):
        if re.search(hybrid_pattern, combined_short):
            work_mode = "hybrid"
        else:
            work_mode = "remote"
    elif re.search(hybrid_pattern, combined_short):
        work_mode = "hybrid"
    elif re.search(onsite_pattern, combined_short):
        work_mode = "onsite"
    elif re.search(remote_pattern, full_text[:1500]):
        if re.search(hybrid_pattern, full_text[:1500]):
            work_mode = "hybrid"
        else:
            work_mode = "remote"
    elif re.search(hybrid_pattern, full_text[:1500]):
        work_mode = "hybrid"
    elif re.search(onsite_pattern, full_text[:1500]):
        work_mode = "onsite"
    elif source_norm in ("jobicy", "remoteok", "remotive", "weworkremotely"):
        work_mode = "remote"
    elif loc_norm and loc_norm not in ("none", "null", "unknown", "remote", "anywhere", "n/a", "") and re.search(r"[a-z]{2,}", loc_norm):
        work_mode = "onsite"

    # 2. Extract Remote Scope & Country/Region Constraints
    remote_scope = "unknown"
    remote_countries: set[str] = set()
    remote_regions: set[str] = set()
    country_flags: dict[str, str] = {}
    region_flags: dict[str, str] = {}

    # Check worldwide indicators
    is_worldwide = bool(
        re.search(
            r"\b(worldwide|anywhere|anywhere in the world|global remote|globally|work from anywhere|globally distributed|distributed globally|remote - global|remote - worldwide|remote - anywhere)\b",
            full_text,
        )
    )

    if is_worldwide:
        remote_scope = "worldwide"
        if work_mode == "unknown":
            work_mode = "remote"

    # Distinguish company HQ location metadata from explicit restriction text
    restriction_text = f"{title_norm} \n {desc_norm}"
    if re.search(r"\b(remote|wfh|telecommute|hybrid|onsite|on-site)\s*-\s*", loc_norm):
        restriction_text = f"{loc_norm} \n {restriction_text}"

    # Strip employer HQ metadata before extracting applicant country restrictions
    clean_restriction_text = restriction_text
    hq_patterns = [
        r"\bheadquartered\s+(?:in|out\s+of|from)\s+[^.\n;]+",
        r"\bheadquarters\s+(?:is|are)?\s*(?:located)?\s*(?:in|out\s+of)?\s+[^.\n;]+",
        r"\b(?:company|our)\s+hq\s+(?:is|are)?\s*(?:located)?\s*(?:in|out\s+of)?\s+[^.\n;]+",
        r"\bhq\s+(?:is|are)\s+(?:located\s+)?in\s+[^.\n;]+",
        r"\b(?:company|our)\s+headquarters\s+[^.\n;]+",
        r"\b(?:company|main|corporate)\s+office\s+(?:is\s+)?(?:located\s+)?in\s+[^.\n;]+",
        r"\bour\s+(?:main\s+)?office\s+(?:is\s+)?(?:located\s+)?in\s+[^.\n;]+",
        r"\bbased\s+out\s+of\s+(?:our\s+)?(?:office\s+in\s+|hq\s+in\s+)?[^.\n;]+",
        r"\bcompany\s+(?:is\s+)?based\s+in\s+[^.\n;]+",
        r"\bhq\s+in\s+[^.\n;]+",
    ]
    for hq_pat in hq_patterns:
        clean_restriction_text = re.sub(hq_pat, " ", clean_restriction_text, flags=re.IGNORECASE)

    # Extract Country Restrictions
    for pattern, country_name, flag in COUNTRY_PATTERNS:
        if country_name == "United States":
            c_match = re.search(r"\b(united states|usa|u\.s\.a?|u\.s\.|us only|us remote|us based|us citizens?|us timezones?|reside in the us|remote - us|remote \(us\))\b", clean_restriction_text)
        elif country_name == "India":
            c_match = re.search(r"\b(india|ind|remote - in|remote \(in\))\b", clean_restriction_text)
        elif country_name == "Germany":
            c_match = re.search(r"\b(germany|deutschland|remote - de|remote \(de\))\b", clean_restriction_text)
        else:
            c_match = re.search(pattern, clean_restriction_text)

        if c_match:
            remote_countries.add(country_name)
            country_flags[country_name] = flag

    # Generic extraction for explicit applicant restrictions (e.g. "Remote - Country A only", "Must reside in Country A", "Applicants must be located in Country A", "Available only in Country A")
    m1 = re.findall(r"\b(?:remote\s*-\s*)([a-z0-9]+(?:\s+[a-z0-9]+){0,2})\s+only\b", clean_restriction_text)
    m2 = re.findall(r"\b(?:must|applicants must) (?:be|reside|be located|be based) in (?:the\s+)?([a-z0-9]+(?:\s+[a-z0-9]+){0,2})", clean_restriction_text)
    m3 = re.findall(r"\b(?:available|available only|open to candidates) in (?:the\s+)?([a-z0-9]+(?:\s+[a-z0-9]+){0,2})", clean_restriction_text)
    m4 = re.findall(r"\b(?:remote\s*-\s*)([a-z0-9]+(?:\s+[a-z0-9]+){0,2})", clean_restriction_text)
    generic_country_matches = m1 + m2 + m3 + m4

    excluded_words = {"anywhere", "worldwide", "global", "all", "country", "region", "location", "area", "zone"}

    for g_match in generic_country_matches:
        cleaned_g = g_match.strip()
        cleaned_g = re.sub(r"\s+only$", "", cleaned_g, flags=re.IGNORECASE).strip()
        if cleaned_g and len(cleaned_g) > 1 and cleaned_g.lower() not in excluded_words:
            found_canonical = None
            for pattern, country_name, flag in COUNTRY_PATTERNS:
                if re.search(pattern, cleaned_g):
                    found_canonical = country_name
                    country_flags[country_name] = flag
                    break
            if not found_canonical:
                tokens_g = set(re.findall(r"\b[a-z0-9]+\b", cleaned_g.lower()))
                if tokens_g & {"us", "usa", "u.s.", "united states"}:
                    found_canonical = "United States"
                elif tokens_g & {"in", "ind", "india"}:
                    found_canonical = "India"
                elif tokens_g & {"can", "ca", "canada"}:
                    found_canonical = "Canada"
                elif tokens_g & {"uk", "gb", "united kingdom"}:
                    found_canonical = "United Kingdom"
                elif tokens_g & {"de", "germany"}:
                    found_canonical = "Germany"
            c_name = found_canonical or cleaned_g.title()
            if not any(c_name.lower() in existing.lower() or existing.lower() in c_name.lower() for existing in remote_countries):
                remote_countries.add(c_name)

    # Extract Region Restrictions
    for pattern, region_name, flag in REGION_PATTERNS:
        if re.search(pattern, full_text):
            remote_regions.add(region_name)
            region_flags[region_name] = flag

    # Refine Remote Scope if not worldwide
    if is_worldwide:
        remote_scope = "worldwide"
        remote_countries.clear()
    else:
        has_explicit_country_restriction = bool(
            re.search(
                r"\b(only|based|reside|citizens|timezones|remote\s*-\s*[a-z0-9\s]+|remote\s*\([a-z0-9\s]+\)|must be in|located in|available in|open to candidates in|applicants must be)\b",
                full_text,
            )
        )
        if work_mode == "remote":
            if remote_countries and has_explicit_country_restriction:
                remote_scope = "country_specific"
            elif remote_regions:
                remote_scope = "region_specific"

    # 3. Determine Candidate Eligibility for India (High-Recall Policy)
    is_india_eligible: bool | None = None

    if work_mode == "remote":
        if is_worldwide or "India" in remote_countries or any(r in remote_regions for r in ["Asia", "APAC"]):
            is_india_eligible = True
        elif len(remote_countries) == 1 or (
            len(remote_countries) == 2 and "United States" in remote_countries and "Canada" in remote_countries
        ):
            # Strict single-country restriction (e.g. US Only, Germany Only, UK Only) or North America restriction
            is_india_eligible = False
        elif len(remote_countries) > 2:
            # Multi-country global/regional remote posting -> Ambiguous, treat as None (Kept at Stage 1 for High Recall!)
            is_india_eligible = None
        elif remote_regions:
            # Region restriction like Europe/EMEA
            is_india_eligible = False
        else:
            is_india_eligible = True
    elif work_mode in ("hybrid", "onsite"):
        if "India" in remote_countries:
            is_india_eligible = True
        elif remote_countries or loc_norm:
            # On-site / Hybrid in specific non-India location (e.g. Hybrid Berlin, On-site Munich)
            is_india_eligible = False
        else:
            is_india_eligible = None
    else:
        is_india_eligible = None

    # 4. Generate Display Label
    display_label = "❓ Work mode unknown"
    sorted_countries = sorted(remote_countries)
    sorted_regions = sorted(remote_regions)

    if work_mode == "remote":
        if is_worldwide:
            display_label = "🌎 Remote · Worldwide"
        elif "India" in remote_countries:
            display_label = "🏠 Remote · India eligible"
        elif any(r in sorted_regions for r in ["Asia", "APAC"]):
            display_label = "🌏 Remote · Asia"
        elif len(sorted_countries) == 1:
            c_name = sorted_countries[0]
            flag = country_flags.get(c_name, "📍")
            if c_name == "United States":
                display_label = "🇺🇸 Remote · US only"
            elif c_name == "Germany":
                display_label = "🇩🇪 Remote · Germany only"
            else:
                display_label = f"{flag} Remote · {c_name}"
        elif sorted_countries:
            c_name = sorted_countries[0]
            flag = country_flags.get(c_name, "🌐")
            display_label = f"{flag} Remote · {', '.join(sorted_countries[:2])}"
        elif sorted_regions:
            r_name = sorted_regions[0]
            flag = region_flags.get(r_name, "🌐")
            display_label = f"{flag} Remote · {r_name}"
        else:
            display_label = "🏠 Remote"

    elif work_mode == "hybrid":
        if "India" in remote_countries:
            display_label = "🔀 Hybrid · India"
        elif sorted_countries:
            c_name = sorted_countries[0]
            display_label = f"🔀 Hybrid · {c_name}"
        elif loc_raw:
            loc_short = loc_raw.split(",")[0].strip()
            display_label = f"🔀 Hybrid · {loc_short}"
        else:
            display_label = "🔀 Hybrid"

    elif work_mode == "onsite":
        if sorted_countries:
            c_name = sorted_countries[0]
            display_label = f"🏢 On-site · {c_name}"
        elif loc_raw:
            loc_short = loc_raw.split(",")[0].strip()
            display_label = f"🏢 On-site · {loc_short}"
        else:
            display_label = "🏢 On-site"

    elif loc_raw:
        display_label = f"📍 {loc_raw}"

    return WorkArrangement(
        work_mode=work_mode,
        remote_scope=remote_scope,
        remote_countries=sorted_countries,
        remote_regions=sorted_regions,
        is_india_eligible=is_india_eligible,
        display_label=display_label,
    )


def _matches_preferred_location(
    job_location_text: str,
    preferred_locations: list[str],
) -> bool:
    """Return True if any preferred location matches the job location text generically."""
    if not preferred_locations:
        return True
    if not job_location_text or not job_location_text.strip():
        return False

    norm_text = _normalize_text(job_location_text)
    text_words = set(re.findall(r"\w+", norm_text))

    for pref in preferred_locations:
        norm_pref = _normalize_text(pref)
        if not norm_pref:
            continue
        # Direct substring match (e.g. "mumbai" in "mumbai, maharashtra, india")
        if norm_pref in norm_text:
            return True
        # Token set match (e.g. "new york" tokens in "new york city, ny")
        pref_words = set(re.findall(r"\w+", norm_pref))
        if pref_words and pref_words.issubset(text_words):
            return True

    return False


def _matches_remote_applicant_constraint(
    preferred_locations: list[str],
    wa: WorkArrangement,
) -> bool:
    """Return True if preferred_locations match remote applicant geographic constraints (or if job is unrestricted)."""
    if not preferred_locations or wa.remote_scope in ("worldwide", "unknown") or not wa.remote_countries:
        return True

    for pref in preferred_locations:
        norm_pref = _normalize_text(pref)
        if not norm_pref:
            continue
        # Direct match on country name in pref
        for c in wa.remote_countries:
            c_norm = _normalize_text(c)
            if c_norm in norm_pref or norm_pref in c_norm:
                return True
        # Match using COUNTRY_PATTERNS
        for pattern, country_name, _ in COUNTRY_PATTERNS:
            if re.search(pattern, norm_pref) and country_name in wa.remote_countries:
                return True
        # Match region if present
        for r in wa.remote_regions:
            r_norm = _normalize_text(r)
            if r_norm in norm_pref or norm_pref in r_norm:
                return True

    return False


def is_job_location_eligible(
    job: dict[str, Any],
    work_arrangement: str = "any",
    preferred_locations: list[str] | None = None,
) -> bool:
    """Return True if job is compatible with work arrangement and preferred location preferences.

    Semantics:
    - Work arrangement preference ("remote", "onsite", "hybrid", "any"):
        - "remote": only remote jobs allowed.
        - "onsite": only onsite jobs allowed.
        - "hybrid": only hybrid jobs allowed.
        - "any": remote, hybrid, and onsite jobs allowed.
    - Preferred locations:
        - Apply as physical office location constraints for On-site and Hybrid jobs.
        - Remote jobs are NOT restricted by company HQ/office location metadata, but respect explicit applicant country/region constraints.
        - If preferred_locations is empty ([]), no location restriction applies to any mode.
    """
    user_mode = (work_arrangement or "any").strip().lower()
    norm_preferred = [p.strip().lower() for p in (preferred_locations or []) if p and p.strip()]

    wa = parse_work_arrangement(job)
    job_mode = wa.work_mode.lower()

    # 1. Work Arrangement Filter
    if user_mode != "any":
        if user_mode == "remote" and job_mode in ("onsite", "hybrid"):
            return False
        if user_mode == "onsite" and job_mode in ("remote", "hybrid"):
            return False
        if user_mode == "hybrid" and job_mode in ("remote", "onsite"):
            return False

    # 2. Preferred Locations Filter
    if norm_preferred:
        if job_mode in ("onsite", "hybrid", "unknown"):
            job_loc_raw = str(job.get("location") or "")
            title_raw = str(job.get("title") or "")
            desc_raw = str(job.get("description") or "")
            search_text = f"{job_loc_raw} {title_raw} {desc_raw}"

            if not _matches_preferred_location(search_text, norm_preferred):
                return False
        elif job_mode == "remote":
            if not _matches_remote_applicant_constraint(norm_preferred, wa):
                return False

    return True
