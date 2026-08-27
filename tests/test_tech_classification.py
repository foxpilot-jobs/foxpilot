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
        # Engineering
        ("Senior Software Engineer", "Developing scalable backend microservices.", "software_engineering"),
        ("Backend Engineer", "Building APIs in Python and FastAPI.", "software_engineering"),
        ("Frontend Developer", "Building React and TypeScript interfaces.", "software_engineering"),
        ("Full Stack Engineer", "Full stack Node.js and React development.", "software_engineering"),
        ("Mobile Developer", "Developing iOS and Android mobile apps.", "software_engineering"),
        ("Platform Engineer", "Building internal developer platform tooling.", "software_engineering"),
        # Data & Annotation
        ("Data Engineer", "Building ETL pipelines with Python, SQL, PostgreSQL and Spark.", "data_analytics"),
        ("Data Analyst", "Analyzing business metrics using SQL queries and dashboards.", "data_analytics"),
        ("Analytics Engineer", "Modeling data in Snowflake using dbt and SQL.", "data_analytics"),
        ("BI Analyst", "Building PowerBI and Tableau data dashboards.", "data_analytics"),
        ("Data Annotation Specialist", "Annotating and labeling datasets for AI training models.", "data_analytics"),
        ("Data Labeling Specialists", "Reviewing and tagging image datasets for computer vision models.", "data_analytics"),
        # AI
        ("Machine Learning Engineer", "Training PyTorch deep learning models for LLM applications.", "ai_ml"),
        ("AI Engineer", "Building AI agents with Python and OpenAI APIs.", "ai_ml"),
        ("MLOps Engineer", "Deploying machine learning models into production with Docker.", "ai_ml"),
        ("Data Scientist", "Predictive modeling and statistics in Python.", "ai_ml"),
        # Cloud / Infrastructure
        ("DevOps Engineer", "Managing AWS infrastructure with Terraform and Kubernetes.", "devops_cloud"),
        ("Cloud Engineer", "Architecting Azure cloud services and Docker containers.", "devops_cloud"),
        ("Site Reliability Engineer", "SRE role monitoring system performance, CI/CD, and GCP.", "devops_cloud"),
        ("Infrastructure Engineer", "Managing servers, network systems, and Linux cluster.", "infrastructure"),
        # Security
        ("Cybersecurity Analyst", "Monitoring SOC alerts, threat hunting, and SIEM logs.", "cybersecurity"),
        ("Security Engineer", "SecOps, application security, and penetration testing.", "cybersecurity"),
        ("SOC Analyst", "Analyzing security logs and incident response.", "cybersecurity"),
        ("Cloud Security Engineer", "Hardening AWS and Azure IAM policies and SecOps.", "cybersecurity"),
        # Product
        ("Product Manager", "Defining product roadmap and user stories.", "product_management"),
        ("Technical Product Manager", "Translating API requirements to engineering team.", "product_management"),
        ("Product Owner", "Managing agile backlog and sprint planning.", "product_management"),
        # Design
        ("Graphic Designer", "Designing brand assets, banners, and visual graphics.", "design_ux"),
        ("Graphic Designer", "Boilerplate description: Python, React, Node.js developer agency.", "design_ux"),
        ("UX Designer", "Conducting wireframes and user interface prototypes in Figma.", "design_ux"),
        ("UI Designer", "Creating UI design components and design systems.", "design_ux"),
        ("Product Designer", "End to end user experience and product UI design.", "design_ux"),
        ("Visual Designer", "Visual layout, typography, and UI assets.", "design_ux"),
        ("UX Researcher", "User testing interviews and usability research.", "design_ux"),
        ("Design Engineer", "Design systems and frontend CSS component implementation.", "design_ux"),
        # Technical / Product Support & Solutions
        ("Technical Support Engineer", "Troubleshooting cloud SaaS applications, APIs, and logs.", "technical_solutions"),
        ("Product Support Engineer", "Resolving customer technical software tickets in Zendesk and Jira.", "technical_solutions"),
        ("Product Support Jedi", "Supporting SaaS web application users, database troubleshooting.", "technical_solutions"),
        ("Implementation Consultant", "Integrating REST APIs, configuring PostgreSQL databases.", "technical_solutions"),
        ("Implementation Consultant — SaaS", "Onboarding enterprise clients to SaaS software platform.", "technical_solutions"),
        ("Solutions Architect", "Designing cloud enterprise architecture for microservices.", "technical_solutions"),
        ("Solutions Engineer", "Technical customer demos, REST API integration, and proof of concept.", "technical_solutions"),
        ("Sales Engineer", "Technical sales demos, architecture validation, and API integration.", "technical_solutions"),
        # Business Technology
        ("Business Systems Analyst", "Gathering software requirements, SQL database queries.", "business_technology"),
        ("Project Systems Specialist", "Managing SQL database system configurations.", "business_technology"),
        # Technical Writing
        ("Technical Writer", "Writing API documentation and developer guides.", "technical_writing"),
        ("Developer Documentation Specialist", "Writing software architecture guides.", "technical_writing"),
        # Marketing Technology
        ("Marketing Technology Manager", "Managing HubSpot automation, Google Analytics, and SQL data.", "marketing_tech"),
    ],
)
def test_broad_tech_and_digital_jobs(title: str, description: str, expected_category: str) -> None:
    job = create_job(title=title, description=description)
    res = classify_tech_job(job)
    assert res.is_tech_job is True
    assert res.confidence >= 0.70
    assert res.tech_category == expected_category


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("Sandwich Artist", "Making sandwiches and operating POS cash register at Subway."),
        ("Retail Store Associate", "Greeting customers and stocking shelves at Rowan."),
        ("Trimmer", "Trimming products in warehouse facility."),
        ("Pilot", "Flying commercial aircraft for SpaceX."),
        ("AP Accountant", "Managing accounts payable, invoices, and ledger at Bosta."),
        ("Delivery Driver", "Driving delivery truck to deliver packages."),
        ("Post Office Manager", "Managing postal office operations and staff."),
        ("Beauty Merchandiser", "Merchandising cosmetics at Shoppers Drug Mart."),
        ("Cashier", "Operating cash register at grocery store."),
        ("Recruiter", "Sourcing candidates and conducting phone screens."),
        ("Sales Representative", "Cold calling leads and closing sales deals."),
        ("Customer Service Representative", "Answering phone calls and managing customer returns."),
        ("Generic Marketing Manager", "Planning event flyers, brochure distribution, and local advertising."),
        ("Administrative Assistant", "Booking executive travel, calendar scheduling, and filing paperwork."),
        ("Accountant", "Tax filing and ledger entries."),
    ],
)
def test_explicit_non_tech_jobs(title: str, description: str) -> None:
    job = create_job(title=title, description=description)
    res = classify_tech_job(job)
    assert res.is_tech_job is False
    assert res.confidence >= 0.70
    assert res.tech_category is None
