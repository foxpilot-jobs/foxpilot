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


# Country pattern mappings to canonical names and ISO 2-letter codes / flags
COUNTRY_PATTERNS = [
    (r"\b(india|in|ind)\b", "India", "🇮🇳"),
    (r"\b(united states|usa|u\.s\.a?|u\.s\.)\b", "United States", "🇺🇸"),
    (r"\b(germany|berlin|munich|münchen|wiesbaden|frankfurt|hamburg|deutschland|de)\b", "Germany", "🇩🇪"),
    (r"\b(united kingdom|uk|england|london|great britain|gb)\b", "United Kingdom", "🇬🇧"),
    (r"\b(canada|ca)\b", "Canada", "🇨🇦"),
    (r"\b(australia|au)\b", "Australia", "🇦🇺"),
    (r"\b(mexico|mx)\b", "Mexico", "🇲🇽"),
    (r"\b(france|paris|fr)\b", "France", "🇫🇷"),
    (r"\b(netherlands|amsterdam|nl)\b", "Netherlands", "🇳🇱"),
    (r"\b(spain|madrid|es)\b", "Spain", "🇪🇸"),
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
    if re.search(r"\b(remote|wfh|work from home|telecommute|anywhere|distributed)\b", combined_short):
        if re.search(r"\b(hybrid)\b", combined_short):
            work_mode = "hybrid"
        else:
            work_mode = "remote"
    elif re.search(r"\b(hybrid)\b", combined_short):
        work_mode = "hybrid"
    elif re.search(r"\b(on-site|onsite|in-office|office-based)\b", combined_short):
        work_mode = "onsite"
    elif re.search(r"\b(remote|wfh|work from home|telecommute)\b", full_text[:1000]):
        if re.search(r"\b(hybrid)\b", full_text[:1000]):
            work_mode = "hybrid"
        else:
            work_mode = "remote"
    elif re.search(r"\b(hybrid)\b", full_text[:1000]):
        work_mode = "hybrid"
    elif re.search(r"\b(on-site|onsite|in-office)\b", full_text[:1000]):
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
            r"\b(worldwide|anywhere in the world|global remote|globally|work from anywhere|remote - global|remote - worldwide)\b",
            full_text,
        )
    )

    if is_worldwide:
        remote_scope = "worldwide"
        if work_mode == "unknown":
            work_mode = "remote"

    # Extract Country Restrictions
    for pattern, country_name, flag in COUNTRY_PATTERNS:
        if country_name == "United States":
            c_match = re.search(r"\b(united states|usa|u\.s\.a?|u\.s\.|us only|us remote|us based|us citizens?|us timezones?|reside in the us|remote - us|remote \(us\))\b", full_text)
        elif country_name == "India":
            c_match = re.search(r"\b(india|ind|remote - in|remote \(in\))\b", full_text)
        elif country_name == "Germany":
            c_match = re.search(r"\b(germany|berlin|munich|münchen|wiesbaden|frankfurt|hamburg|deutschland|remote - de|remote \(de\))\b", full_text)
        else:
            c_match = re.search(pattern, full_text)

        if c_match:
            remote_countries.add(country_name)
            country_flags[country_name] = flag

    # Extract Region Restrictions
    for pattern, region_name, flag in REGION_PATTERNS:
        if re.search(pattern, full_text):
            remote_regions.add(region_name)
            region_flags[region_name] = flag

    # Refine Remote Scope if not worldwide
    if work_mode == "remote" and not is_worldwide:
        if remote_countries:
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
        if "India" in remote_countries or re.search(r"\b(bangalore|bengaluru|mumbai|delhi|noida|gurgaon|hyderabad|pune|chennai)\b", full_text):
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
