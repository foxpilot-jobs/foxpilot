"""Technology & Digital Career Corpus Classifier.

Evaluates job listings to determine whether a job belongs to FoxPilot's
global technology and digital career corpus (engineering, data, AI, product,
design/UX, technical solutions, technical writing, business technology,
digital marketing / MarTech, product & technical support, and data annotation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

VALID_CATEGORIES = {
    "software_engineering",
    "data_analytics",
    "ai_ml",
    "devops_cloud",
    "infrastructure",
    "cybersecurity",
    "qa_testing",
    "product_management",
    "design_ux",
    "technical_solutions",
    "technical_writing",
    "business_technology",
    "marketing_tech",
    "other_digital",
}

STRONG_TECH_TITLE_PATTERNS: list[tuple[str, str]] = [
    # (regex_pattern, assigned_category)
    # Design / UX
    (r"\b(graphic designer|ux designer|ui designer|product designer|ux researcher|visual designer|interaction designer|web designer|motion designer|design engineer|design systems designer|diseñador|designer)\b", "design_ux"),
    # Product Management & Technical Project/Program Management
    (r"\b(technical product manager|product manager|product owner|technical program manager|technical project manager|engineering program manager|tpm|head of product|vp of product)\b", "product_management"),
    # Technical / Solutions / Implementation / Developer Relations / Technical Sales
    (r"\b(solutions architect|solutions engineer|sales engineer|technical sales|technical consultant|implementation consultant|implementation specialist|solutions consultant|technical account manager|developer relations|devrel|developer advocate|customer engineer)\b", "technical_solutions"),
    # Product & Technical Support
    (r"\b(technical support|support engineer|product support|tier \w+ support|saas support|customer support engineer|it support specialist|product support engineer|technical support engineer)\b", "technical_solutions"),
    # Technical Writing & Documentation
    (r"\b(technical writer|documentation engineer|developer documentation|developer documentation specialist|api documentation|tech writer|technical content)\b", "technical_writing"),
    # Business Technology & Systems Analysis
    (r"\b(it business analyst|business systems analyst|technology analyst|systems analyst|project systems specialist)\b", "business_technology"),
    # Data Annotation & AI Data Operations
    (r"\b(data (labeling|annotation|annotator|labeler|collection|specialists?)|ai data trainer|ai trainer|ai evaluator|ai tutor|data annotation specialist)\b", "data_analytics"),
    # Marketing Technology & Digital Growth
    (r"\b(marketing technology|martech|growth engineer|marketing automation|marketing automation specialist|marketing operations|digital marketing specialist)\b", "marketing_tech"),
    # Data & Analytics
    (r"\b(data engineer(ing)?|analytics engineer|data architect|database developer|database administrator|dba|bi analyst|bi developer|data analyst|data analytics)\b", "data_analytics"),
    (r"\b(data scientist|data science)\b", "ai_ml"),
    # AI / ML
    (r"\b(machine learning|ml engineer|ai engineer|ai researcher|mlops|nlp engineer|computer vision engineer|deep learning engineer)\b", "ai_ml"),
    # Software Engineering
    (r"\b(backend|frontend|full[\s\-]?stack|software engineer|software developer|web developer|mobile engineer|mobile developer|ios developer|android developer|platform engineer|embedded engineer|application developer|api developer|release engineer|build engineer|desarrollador|développeur|desenvolvedor)\b", "software_engineering"),
    (r"\b(engineering manager|vp of engineering|head of engineering|cto|chief technology officer)\b", "software_engineering"),
    # DevOps & Cloud
    (r"\b(devops|site reliability|sre|cloud engineer|cloud architect)\b", "devops_cloud"),
    # Cybersecurity & Compliance
    (r"\b(cybersecurity|security engineer|application security|secops|infosec|information security|cloud security|soc analyst|grc analyst|security analyst|compliance analyst)\b", "cybersecurity"),
    # Infrastructure
    (r"\b(infrastructure engineer|systems engineer|network engineer|sysadmin|systems administrator|network administrator|it administrator)\b", "infrastructure"),
    # QA & Testing
    (r"\b(qa|quality assurance|sdet|test automation|quality engineer|testing engineer)\b", "qa_testing"),
]

AMBIGUOUS_TITLE_PATTERNS: list[tuple[str, str]] = [
    (r"\b(business analyst|operations analyst|product analyst)\b", "business_technology"),
    (r"\b(consultant|advisor|specialist)\b", "technical_solutions"),
    (r"\b(project manager|program manager)\b", "product_management"),
    (r"\b(digital marketing|marketing manager|growth manager)\b", "marketing_tech"),
]

NON_TECH_TITLE_PATTERNS: list[str] = [
    r"\b(sandwich artist|subway|butcher|trimmer|cleaner|orderly|roupeiro|bell captain|housekeeper)\b",
    r"\b(pilot|flight attendant|delivery driver|truck driver|courier|mail carrier)\b",
    r"\b(retail|store associate|cashier|merchandiser|real estate)\b",
    r"\b(accountant|accounts payable|bookkeeper|auditor)\b",
    r"\b(recruiter|recruiting|talent acquisition|hr coordinator|human resources)\b",
    r"\b(nurse|physician|therapist|medical|pharmacist|dental|caregiver)\b",
    r"\b(quantity surveyor|estimator|construction|plumber|electrician|tradesperson)\b",
    r"\b(waiter|waitress|bartender|chef|cook|barista)\b",
    r"\b(freelance writer|copywriter|content reviewer)\b",
    r"\b(administrative assistant|executive assistant|office manager|receptionist)\b",
    r"\b(customer service representative|call center representative|front desk)\b",
]

# Exclusions when title contains generic "sales" or "marketing" WITHOUT technical/digital qualifiers
NON_TECH_SALES_ADVISOR_PATTERN = r"\b(sales advisor|sales representative|sales rep|sales associate|sales agent|inside sales contractor)\b"

STRONG_TECH_KEYWORDS: dict[str, str] = {
    "python": "software_engineering",
    "sql": "data_analytics",
    "postgresql": "data_analytics",
    "mysql": "data_analytics",
    "mongodb": "data_analytics",
    "redis": "data_analytics",
    "kafka": "data_analytics",
    "spark": "data_analytics",
    "snowflake": "data_analytics",
    "databricks": "data_analytics",
    "etl": "data_analytics",
    "data pipeline": "data_analytics",
    "data warehousing": "data_analytics",
    "data warehouse": "data_analytics",
    "aws": "devops_cloud",
    "azure": "devops_cloud",
    "gcp": "devops_cloud",
    "docker": "devops_cloud",
    "kubernetes": "devops_cloud",
    "terraform": "devops_cloud",
    "ci/cd": "devops_cloud",
    "jenkins": "devops_cloud",
    "github actions": "devops_cloud",
    "react": "software_engineering",
    "typescript": "software_engineering",
    "javascript": "software_engineering",
    "node.js": "software_engineering",
    "nodejs": "software_engineering",
    "django": "software_engineering",
    "fastapi": "software_engineering",
    "golang": "software_engineering",
    "rust": "software_engineering",
    "c++": "software_engineering",
    "c#": "software_engineering",
    ".net": "software_engineering",
    "java": "software_engineering",
    "rest api": "software_engineering",
    "graphql": "software_engineering",
    "microservices": "software_engineering",
    "machine learning": "ai_ml",
    "deep learning": "ai_ml",
    "tensorflow": "ai_ml",
    "pytorch": "ai_ml",
    "llm": "ai_ml",
    "llms": "ai_ml",
    "figma": "design_ux",
    "sketch": "design_ux",
    "adobe xd": "design_ux",
    "ux research": "design_ux",
    "wireframing": "design_ux",
    "prototyping": "design_ux",
    "penetration testing": "cybersecurity",
    "secops": "cybersecurity",
    "siem": "cybersecurity",
    "sdet": "qa_testing",
    "test automation": "qa_testing",
    "saas": "technical_solutions",
    "hubspot": "marketing_tech",
    "marketo": "marketing_tech",
    "google analytics": "marketing_tech",
    "tag manager": "marketing_tech",
}

SECONDARY_TECH_KEYWORDS: list[str] = [
    "code",
    "git",
    "github",
    "gitlab",
    "database",
    "api",
    "apis",
    "cloud",
    "agile",
    "scrum",
    "deployment",
    "linux",
    "bash",
    "scripting",
    "unit testing",
    "architecture",
    "backend",
    "frontend",
    "fullstack",
    "full-stack",
    "user experience",
    "user interface",
    "troubleshooting",
    "ticketing",
    "zendesk",
    "intercom",
    "jira",
    "data annotation",
    "data labeling",
    "ai training",
    "system requirements",
    "software integration",
    "compliance",
    "soc2",
    "gdpr",
]


@dataclass
class TechClassificationResult:
    is_tech_job: bool
    tech_category: str | None
    confidence: float
    score: float
    signals: list[str] = field(default_factory=list)


def _normalize_text(text_val: Any) -> str:
    if not text_val:
        return ""
    return re.sub(r"\s+", " ", str(text_val).lower()).strip()


def classify_tech_job(job: dict[str, Any]) -> TechClassificationResult:
    """Classify whether a job belongs to FoxPilot's global technology/digital corpus."""
    title_raw = str(job.get("title", ""))
    desc_raw = str(job.get("description", ""))
    dept_raw = str(job.get("department", "") or job.get("category", "") or "")

    title_norm = _normalize_text(title_raw)
    desc_norm = _normalize_text(desc_raw)
    dept_norm = _normalize_text(dept_raw)
    full_text_norm = f"{title_norm} {dept_norm} {desc_norm}"

    signals: list[str] = []
    score = 0.0
    category_votes: dict[str, float] = {cat: 0.0 for cat in VALID_CATEGORIES}

    # 1. Title Evaluation & Category Anchor
    title_strong_matched = False
    title_assigned_category: str | None = None

    for pattern, cat in STRONG_TECH_TITLE_PATTERNS:
        if re.search(pattern, title_norm):
            score += 45.0
            title_strong_matched = True
            title_assigned_category = cat
            signals.append(f"title: '{title_raw}' ({cat})")
            category_votes[cat] += 45.0
            break

    if not title_strong_matched:
        for pattern, cat in AMBIGUOUS_TITLE_PATTERNS:
            if re.search(pattern, title_norm):
                score += 20.0
                title_assigned_category = cat
                signals.append(f"ambiguous_title: '{title_raw}' ({cat})")
                category_votes[cat] += 20.0
                break

    # Non-tech title penalties
    is_explicit_non_tech = False
    for pattern in NON_TECH_TITLE_PATTERNS:
        if re.search(pattern, title_norm) and not title_strong_matched:
            score -= 40.0
            is_explicit_non_tech = True
            signals.append(f"non_tech_title_penalty: '{title_raw}'")
            break

    if (
        not is_explicit_non_tech
        and not title_strong_matched
        and re.search(NON_TECH_SALES_ADVISOR_PATTERN, title_norm)
        and not any(
            t in title_norm for t in ["engineer", "technical", "solutions", "architect", "support"]
        )
    ):
        score -= 40.0
        is_explicit_non_tech = True
        signals.append(f"non_tech_sales_penalty: '{title_raw}'")

    # 2. Source Category / Department Metadata
    tech_dept_keywords = ["engineering", "data", "software", "technology", "it", "infrastructure", "security", "machine learning", "ai", "design", "product", "support", "marketing"]
    if any(k in dept_norm for k in tech_dept_keywords):
        score += 15.0
        signals.append(f"category_metadata: '{dept_raw}'")
        if "design" in dept_norm:
            category_votes["design_ux"] += 15.0
        elif "product" in dept_norm:
            category_votes["product_management"] += 15.0
        elif "data" in dept_norm:
            category_votes["data_analytics"] += 15.0
        elif "security" in dept_norm:
            category_votes["cybersecurity"] += 15.0
        elif "support" in dept_norm:
            category_votes["technical_solutions"] += 15.0

    # 3. Description Keywords & Context Differentiation
    matched_strong_keywords: list[str] = []
    for kw, cat in STRONG_TECH_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", full_text_norm):
            matched_strong_keywords.append(kw)
            if not title_assigned_category or title_assigned_category in ("software_engineering", "data_analytics", "ai_ml", "devops_cloud", "marketing_tech"):
                category_votes[cat] += 5.0

    if matched_strong_keywords:
        kw_score = min(len(matched_strong_keywords) * 5.0, 30.0)
        score += kw_score
        signals.append(f"keywords_strong ({len(matched_strong_keywords)}): {', '.join(matched_strong_keywords[:5])}")

    matched_secondary_keywords: list[str] = []
    for sk in SECONDARY_TECH_KEYWORDS:
        if re.search(r"\b" + re.escape(sk) + r"\b", full_text_norm):
            matched_secondary_keywords.append(sk)

    if matched_secondary_keywords:
        sec_score = min(len(matched_secondary_keywords) * 2.5, 15.0)
        score += sec_score
        signals.append(f"keywords_secondary ({len(matched_secondary_keywords)}): {', '.join(matched_secondary_keywords[:4])}")

    # Context Penalty for Ambiguous Non-Tech Marketing/Finance Roles
    if not title_strong_matched and ("marketing" in title_norm or "business analyst" in title_norm):
        non_tech_context = ["budget", "payroll", "sales leads", "cold call", "brochure", "event planning", "flyer"]
        if any(c in desc_norm for c in non_tech_context) and not matched_strong_keywords:
            score -= 20.0
            signals.append("non_tech_description_context_penalty")

    # 4. Determine Final Tech Category
    final_category: str | None = None
    if title_assigned_category:
        final_category = title_assigned_category
    elif max(category_votes.values()) > 0:
        final_category = max(category_votes, key=lambda k: category_votes[k])

    # 5. Threshold & Confidence Calibration (High Recall: score >= 20.0)
    is_tech_job = score >= 20.0

    if score >= 40.0:
        confidence = min(0.85 + (score - 40.0) * 0.003, 0.98)
    elif 20.0 <= score < 40.0:
        confidence = round(0.70 + (score - 20.0) * 0.007, 2)
    elif 10.0 <= score < 20.0:
        confidence = round(0.45 + (score - 10.0) * 0.02, 2)
    else:
        confidence = min(0.85 + max(0.0, 10.0 - score) * 0.005, 0.99)

    return TechClassificationResult(
        is_tech_job=is_tech_job,
        tech_category=final_category if is_tech_job else None,
        confidence=round(confidence, 2),
        score=round(score, 1),
        signals=signals,
    )
