"""Employer Identity Verification Service — GSTIN and corporate domain validation.

Enables verified employer badges to establish authentic enterprise pedigree for
hiring demands and placement drives without requiring invasive third-party credentials.
"""
import re
from typing import Any

# Standard 15-character GSTIN regex
# Format: 2-digit state code + 10-char PAN + 1 entity code + 'Z' + 1 checksum char
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

# Indian State GST codes mapping
GST_STATE_CODES: dict[str, str] = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre Jurisdiction",
}

# Public webmail / non-corporate domains
PUBLIC_WEBMAIL_DOMAINS: set[str] = {
    "gmail.com",
    "yahoo.com",
    "yahoo.co.in",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "msn.com",
    "rediffmail.com",
    "icloud.com",
    "protonmail.com",
    "proton.me",
    "aol.com",
    "zoho.com",
    "mail.com",
    "gmx.com",
    "yandex.com",
}


def validate_gstin(gstin: str | None) -> dict[str, Any]:
    """Validate standard Indian GSTIN syntax and extract regional state metadata."""
    if not gstin:
        return {"valid": False, "reason": "No GSTIN provided"}

    clean_gstin = gstin.strip().upper()
    if len(clean_gstin) != 15:
        return {
            "valid": False,
            "reason": f"GSTIN must be exactly 15 characters (received {len(clean_gstin)})",
            "raw": clean_gstin,
        }

    if not GSTIN_REGEX.match(clean_gstin):
        return {
            "valid": False,
            "reason": "Invalid GSTIN pattern. Expected format: 2-digit state code + 10-char PAN + 1 entity char + 'Z' + 1 checksum char.",
            "raw": clean_gstin,
        }

    state_code = clean_gstin[:2]
    pan = clean_gstin[2:12]
    state_name = GST_STATE_CODES.get(state_code, "Unknown / Other Territory")

    return {
        "valid": True,
        "gstin": clean_gstin,
        "state_code": state_code,
        "state_name": state_name,
        "pan": pan,
        "is_maharashtra": (state_code == "27"),
    }


def is_corporate_domain(email: str | None) -> tuple[bool, str]:
    """Check if an email domain represents an organization/corporate domain rather than free webmail."""
    if not email or "@" not in email:
        return False, ""

    domain = email.strip().lower().split("@")[-1]
    if not domain or "." not in domain:
        return False, domain

    is_corp = domain not in PUBLIC_WEBMAIL_DOMAINS
    return is_corp, domain


def verify_employer_credentials(
    email: str | None,
    gstin: str | None = None,
    company_name: str | None = None,
) -> dict[str, Any]:
    """Evaluate employer authenticity tier based on corporate domain and GSTIN verification."""
    gstin_result = validate_gstin(gstin)
    has_valid_gstin = gstin_result["valid"]

    has_corp_domain, domain = is_corporate_domain(email)

    if has_valid_gstin and has_corp_domain:
        tier = "GSTIN_SYNTAX_VALIDATED"
        badge = "GSTIN & Corporate Domain Validated"
        verified = True
        desc = f"Corporate domain ({domain}) with syntax-validated GSTIN ({gstin_result.get('state_name')})."
    elif has_valid_gstin:
        tier = "GSTIN_SYNTAX_VALIDATED"
        badge = "GSTIN Syntax Validated"
        verified = True
        desc = f"Validated commercial registration syntax with GSTIN ({gstin_result.get('state_name')})."
    elif has_corp_domain:
        tier = "CORPORATE_DOMAIN_VERIFIED"
        badge = "Corporate Verified"
        verified = True
        desc = f"Verified corporate work domain ({domain})."
    else:
        tier = "STANDARD_UNVERIFIED"
        badge = "Standard Employer"
        verified = False
        desc = "Standard employer account using public webmail without registered GSTIN."

    return {
        "verified": verified,
        "verification_tier": tier,
        "badge": badge,
        "description": desc,
        "is_corporate_email": has_corp_domain,
        "email_domain": domain,
        "gstin_details": gstin_result,
        "company_name": company_name,
    }
