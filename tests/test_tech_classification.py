from __future__ import annotations

import pytest

from career_agent.tech_classification import (
    classify_tech_job,
)


def create_job(title: str, description: str = "", company: str = "Test Co", department: str = "") -> dict:
    return {
        "title": title,
        "description": description,
        "company": company,
        "department": department,
    }


@pytest.mark.parametrize(
    ("title", "description", "expected_category"),
    [
        # Engineering & Infrastructure
        ("Senior Software Engineer", "Developing scalable backend microservices.", "software_engineering"),
        ("Backend Engineer", "Building APIs in Python and FastAPI.", "software_engineering"),
        ("Frontend Developer", "Building React and TypeScript interfaces.", "software_engineering"),
        ("Full Stack Engineer", "Full stack Node.js and React development.", "software_engineering"),
        ("Mobile Developer", "Developing iOS and Android mobile apps.", "software_engineering"),
        ("Platform Engineer", "Building internal developer platform tooling.", "software_engineering"),
        ("Infrastructure Engineer", "Managing cloud servers, Linux, and network cluster.", "infrastructure"),
        ("Release Engineer", "Automating software release deployments and CI/CD.", "software_engineering"),
        ("Build Engineer", "Configuring build systems, Docker images, and pipelines.", "software_engineering"),
        ("Network Engineer", "Configuring firewalls, routers, and network infrastructure.", "infrastructure"),
        # Data & Analytics
        ("Data Engineer", "Building ETL pipelines with Python, SQL, PostgreSQL and Spark.", "data_analytics"),
        ("Data Analyst", "Analyzing business metrics using SQL queries and dashboards.", "data_analytics"),
        ("Analytics Engineer", "Modeling data in Snowflake using dbt and SQL.", "data_analytics"),
        ("BI Analyst", "Building PowerBI and Tableau data dashboards.", "data_analytics"),
        ("Data Annotation Specialist", "Annotating and labeling datasets for AI training models.", "data_analytics"),
        ("AI Data Trainer", "Evaluating model outputs and training AI data pipelines.", "data_analytics"),
        # AI / ML
        ("Machine Learning Engineer", "Training PyTorch deep learning models for LLM applications.", "ai_ml"),
        ("AI Engineer", "Building AI agents with Python and OpenAI APIs.", "ai_ml"),
        ("MLOps Engineer", "Deploying machine learning models into production with Docker.", "ai_ml"),
        ("Data Scientist", "Predictive modeling and statistics in Python.", "ai_ml"),
        # Cloud / DevOps
        ("DevOps Engineer", "Managing AWS infrastructure with Terraform and Kubernetes.", "devops_cloud"),
        ("Cloud Engineer", "Architecting Azure cloud services and Docker containers.", "devops_cloud"),
        ("Site Reliability Engineer", "SRE role monitoring system performance, CI/CD, and GCP.", "devops_cloud"),
        # Security & Compliance
        ("Security Analyst", "Monitoring SOC alerts, vulnerability scans, and SIEM logs.", "cybersecurity"),
        ("GRC Analyst", "Managing SOC2 compliance, ISO 27001, and cybersecurity policies.", "cybersecurity"),
        ("Cybersecurity Analyst", "Threat hunting, incident response, and network security.", "cybersecurity"),
        ("Security Engineer", "SecOps, application security, and penetration testing.", "cybersecurity"),
        ("SOC Analyst", "Analyzing security logs and incident response.", "cybersecurity"),
        # Product & TPM
        ("Product Manager", "Defining product roadmap and user stories.", "product_management"),
        ("Technical Product Manager", "Translating API requirements to engineering team.", "product_management"),
        ("Technical Program Manager", "Managing technical cross-functional engineering deliverables.", "product_management"),
        ("Technical Project Manager", "Managing software development sprints and technical projects.", "product_management"),
        # Design / UX
        ("Graphic Designer", "Designing brand assets, banners, and visual graphics.", "design_ux"),
        ("Graphic Designer", "Boilerplate description: Python, React, Node.js developer agency.", "design_ux"),
        ("UX Designer", "Conducting wireframes and user interface prototypes in Figma.", "design_ux"),
        ("UI Designer", "Creating UI design components and design systems.", "design_ux"),
        ("Product Designer", "End to end user experience and product UI design.", "design_ux"),
        ("Visual Designer", "Visual layout, typography, and UI assets.", "design_ux"),
        ("Design Engineer", "Design systems and frontend CSS component implementation.", "design_ux"),
        # Technical Solutions / Support / DevRel
        ("Solutions Engineer", "Technical customer demos, REST API integration, and proof of concept.", "technical_solutions"),
        ("Sales Engineer", "Technical sales demos, architecture validation, and API integration.", "technical_solutions"),
        ("Solutions Consultant", "Consulting on REST API integrations and software architecture.", "technical_solutions"),
        ("Implementation Consultant for SaaS", "Onboarding enterprise clients to SaaS software platform.", "technical_solutions"),
        ("Technical Account Manager", "Technical support for enterprise SaaS accounts.", "technical_solutions"),
        ("Product Support Engineer", "Resolving customer technical software tickets in Zendesk and Jira.", "technical_solutions"),
        ("Technical Support Engineer", "Troubleshooting cloud SaaS applications, APIs, and logs.", "technical_solutions"),
        ("Developer Advocate", "Building open source samples and developer community content.", "technical_solutions"),
        ("Developer Relations", "Engaging developer communities and SDK documentation.", "technical_solutions"),
        # Business Technology
        ("IT Business Analyst", "Gathering software requirements, SQL database queries.", "business_technology"),
        ("Systems Analyst", "Analyzing IT systems architecture and database requirements.", "business_technology"),
        # Technical Writing
        ("Technical Writer", "Writing API documentation and developer guides.", "technical_writing"),
        # Marketing Tech
        ("Growth Engineer", "Building growth experiments, web tracking, and A/B testing in JS.", "marketing_tech"),
        ("Marketing Automation Specialist", "Managing HubSpot automation, Google Analytics, and SQL data.", "marketing_tech"),
    ],
)
def test_expanded_tech_and_digital_jobs_high_recall(title: str, description: str, expected_category: str) -> None:
    job = create_job(title=title, description=description)
    res = classify_tech_job(job)
    assert res.is_tech_job is True, f"Failed high recall for: '{title}'"
    assert res.confidence >= 0.70
    assert res.tech_category == expected_category, f"Wrong category for '{title}': got '{res.tech_category}', expected '{expected_category}'"


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("Accountant", "Tax filing, ledger entries, and accounts reconciliation."),
        ("Cashier", "Operating cash register at grocery store."),
        ("Retail Associate", "Greeting customers and stocking retail shelves."),
        ("Delivery Driver", "Driving delivery truck to deliver packages."),
        ("Sandwich Artist", "Making sandwiches and operating POS cash register at Subway."),
        ("Cleaner", "Cleaning office restrooms and vacuuming floors."),
        ("Butcher", "Cutting meat in butcher shop."),
        ("Mail Carrier", "Delivering mail along residential postal route."),
        ("Generic Sales Representative", "Cold calling leads and closing retail sales deals."),
        ("Generic Customer Service Representative", "Answering phone calls and managing customer returns."),
        ("Administrative Assistant", "Booking executive travel, calendar scheduling, and filing paperwork."),
    ],
)
def test_explicit_non_tech_exclusions(title: str, description: str) -> None:
    job = create_job(title=title, description=description)
    res = classify_tech_job(job)
    assert res.is_tech_job is False, f"False positive for non-tech job: '{title}'"
    assert res.confidence >= 0.70
    assert res.tech_category is None


def test_ambiguous_roles_rescued_by_technical_evidence() -> None:
    # GRC Analyst with cybersecurity context
    grc_cyber = create_job(
        title="GRC Analyst",
        description="Managing SOC2 compliance, vulnerability assessments, penetration testing, and cloud security policies.",
    )
    res = classify_tech_job(grc_cyber)
    assert res.is_tech_job is True
    assert res.tech_category == "cybersecurity"

    # Business Analyst with SQL and data warehouse
    ba_tech = create_job(
        title="Business Analyst",
        description="Writing complex SQL queries, analyzing PostgreSQL data warehouse, building dashboards.",
    )
    res_ba = classify_tech_job(ba_tech)
    assert res_ba.is_tech_job is True
    assert res_ba.tech_category in ("business_technology", "data_analytics")

    # Systems Analyst with API and system requirements
    sys_analyst = create_job(
        title="Systems Analyst",
        description="Analyzing system requirements, database schema design, and REST API integrations.",
    )
    res_sys = classify_tech_job(sys_analyst)
    assert res_sys.is_tech_job is True
    assert res_sys.tech_category == "business_technology"

    # Implementation Consultant for SaaS
    impl_saas = create_job(
        title="Implementation Consultant",
        description="Onboarding enterprise clients to SaaS platform, configuring database settings and APIs.",
    )
    res_impl = classify_tech_job(impl_saas)
    assert res_impl.is_tech_job is True
    assert res_impl.tech_category == "technical_solutions"


def test_boilerplate_protection_prevents_false_positives() -> None:
    # Retail Cashier at a tech agency with developer footer boilerplate
    cashier_boilerplate = create_job(
        title="Cashier",
        description="Greeting customers and scanning items at checkout. About Us: We build AI applications using Python, React, PostgreSQL, and AWS.",
    )
    res = classify_tech_job(cashier_boilerplate)
    assert res.is_tech_job is False
