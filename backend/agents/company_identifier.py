"""Company Identifier Agent — resolves visitor IP or input to a company."""

import json
import os
from backend.models.schemas import CompanyIdentification
from backend.services.ip_lookup_service import lookup_ip
from backend.services.llm_service import llm_json_query

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_ip_map() -> dict:
    path = os.path.join(DATA_DIR, "ip_company_map.json")
    with open(path, "r") as f:
        return json.load(f)


async def identify_company_from_ip(ip_address: str) -> CompanyIdentification:
    """Resolve an IP address to a company using mapping + IP lookup."""
    ip_map = _load_ip_map()

    # 1. Check simulated mapping first
    if ip_address in ip_map:
        entry = ip_map[ip_address]
        return CompanyIdentification(
            company_name=entry["company"],
            domain=entry["domain"],
            confidence=0.95,
            method="ip_lookup",
        )

    # 2. Try real IP lookup
    ip_data = await lookup_ip(ip_address)
    if ip_data.get("success") and ip_data.get("org"):
        # Ask LLM to clean up the org name
        result = await llm_json_query(
            f"""Given this IP lookup result, identify the company:
            Organization: {ip_data['org']}
            ISP: {ip_data['isp']}
            Location: {ip_data['city']}, {ip_data['region']}, {ip_data['country']}

            Return JSON: {{"company_name": "...", "domain": "...", "confidence": 0.0-1.0}}""",
            "You are a B2B company identification expert."
        )
        return CompanyIdentification(
            company_name=result.get("company_name", ip_data["org"]),
            domain=result.get("domain", ""),
            confidence=result.get("confidence", 0.5),
            method="ip_lookup",
        )

    return CompanyIdentification(
        company_name="Unknown",
        domain="",
        confidence=0.0,
        method="ip_lookup",
    )


async def identify_company_from_name(
    company_name: str, domain: str = ""
) -> CompanyIdentification:
    """Direct company input — resolve domain if missing."""
    if domain:
        return CompanyIdentification(
            company_name=company_name,
            domain=domain,
            confidence=1.0,
            method="direct_input",
        )

    # Use LLM to guess the domain
    result = await llm_json_query(
        f"""What is the website domain for the company "{company_name}"?
        Return JSON: {{"domain": "example.com", "confidence": 0.0-1.0}}""",
        "You are a B2B data expert. Return only the primary domain, no www prefix."
    )
    return CompanyIdentification(
        company_name=company_name,
        domain=result.get("domain", ""),
        confidence=result.get("confidence", 0.6),
        method="llm_inference",
    )
