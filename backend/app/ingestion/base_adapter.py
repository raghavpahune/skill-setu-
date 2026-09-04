"""Base Source Adapter and Provenance Engine for SkillSetu Ingestion Pipeline.

Provides:
1. Explicit Source Classification Constants (LIVE_API, VERIFIED_SNAPSHOT, SANDBOX_SIMULATION, DEMO_SYNTHETIC).
2. Standardized Provenance Metadata Contract (source, source_type, is_snapshot, content_hash, etc.).
3. Deterministic SHA-256 Content Hashing for reliable deduplication across ingestion runs.
4. Objective Freshness Classification based on true publication or snapshot capture dates.
5. Maharashtra 36 Canonical District Normalization (mapping raw locations/aliases).
6. Keyword-to-Skill Taxonomy Extraction with short-acronym false-positive protections and unmapped skill capture.
7. BaseSourceAdapter abstract interface for external data providers.
"""
from __future__ import annotations

import abc
import datetime
import hashlib
import logging
import re
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("skillsetu.ingestion.base_adapter")

# ---------------------------------------------------------------------------
# Data Source Classifications
# ---------------------------------------------------------------------------
SOURCE_TYPE_LIVE_API = "LIVE_API"
SOURCE_TYPE_VERIFIED_SNAPSHOT = "VERIFIED_SNAPSHOT"
SOURCE_TYPE_SANDBOX_SIMULATION = "SANDBOX_SIMULATION"
SOURCE_TYPE_DEMO_SYNTHETIC = "DEMO_SYNTHETIC"

VALID_SOURCE_TYPES = {
    SOURCE_TYPE_LIVE_API,
    SOURCE_TYPE_VERIFIED_SNAPSHOT,
    SOURCE_TYPE_SANDBOX_SIMULATION,
    SOURCE_TYPE_DEMO_SYNTHETIC,
}

# ---------------------------------------------------------------------------
# Maharashtra 36 Canonical Districts & Alias Normalization Map
# ---------------------------------------------------------------------------
MAHARASHTRA_CANONICAL_DISTRICTS: set[str] = {
    "Ahmednagar", "Akola", "Amravati", "Chhatrapati Sambhajinagar", "Beed",
    "Bhandara", "Buldhana", "Chandrapur", "Dhule", "Gadchiroli", "Gondia",
    "Hingoli", "Jalgaon", "Jalna", "Kolhapur", "Latur", "Mumbai City",
    "Mumbai Suburban", "Nagpur", "Nanded", "Nandurbar", "Nashik",
    "Dharashiv", "Palghar", "Parbhani", "Pune", "Raigad", "Ratnagiri",
    "Sangli", "Satara", "Sindhudurg", "Solapur", "Thane", "Wardha",
    "Washim", "Yavatmal",
}

DISTRICT_ALIASES: dict[str, str] = {
    "pune": "Pune",
    "poona": "Pune",
    "pcmc": "Pune",
    "hinjawadi": "Pune",
    "hadapsar": "Pune",
    "chakan": "Pune",
    "bhosari": "Pune",
    "talwade": "Pune",
    "mumbai": "Mumbai City",
    "bombay": "Mumbai City",
    "mumbai city": "Mumbai City",
    "mumbai suburban": "Mumbai Suburban",
    "navi mumbai": "Thane",
    "thane": "Thane",
    "kalyan": "Thane",
    "dombivli": "Thane",
    "airoli": "Thane",
    "aurangabad": "Chhatrapati Sambhajinagar",
    "chhatrapati sambhajinagar": "Chhatrapati Sambhajinagar",
    "sambhajinagar": "Chhatrapati Sambhajinagar",
    "nagpur": "Nagpur",
    "nashik": "Nashik",
    "nasik": "Nashik",
    "kolhapur": "Kolhapur",
    "solapur": "Solapur",
    "sholapur": "Solapur",
    "amravati": "Amravati",
    "nanded": "Nanded",
    "sangli": "Sangli",
    "jalgaon": "Jalgaon",
    "akola": "Akola",
    "latur": "Latur",
    "dhule": "Dhule",
    "ahmednagar": "Ahmednagar",
    "ahilyanagar": "Ahmednagar",
    "chandrapur": "Chandrapur",
    "parbhani": "Parbhani",
    "jalna": "Jalna",
    "beed": "Beed",
    "bid": "Beed",
    "osmanabad": "Dharashiv",
    "dharashiv": "Dharashiv",
    "palghar": "Palghar",
    "raigad": "Raigad",
    "alibag": "Raigad",
    "panvel": "Raigad",
    "satara": "Satara",
    "ratnagiri": "Ratnagiri",
    "sindhudurg": "Sindhudurg",
    "yavatmal": "Yavatmal",
    "wardha": "Wardha",
    "gondia": "Gondia",
    "bhandara": "Bhandara",
    "buldhana": "Buldhana",
    "buldana": "Buldhana",
    "washim": "Washim",
    "hingoli": "Hingoli",
    "nandurbar": "Nandurbar",
    "gadchiroli": "Gadchiroli",
}


def normalize_maharashtra_district(raw_text: str | None, default: str = "Maharashtra") -> str:
    """Resolve free-text location string to a canonical Maharashtra district."""
    if not raw_text or not raw_text.strip():
        return default

    cleaned = raw_text.strip().lower()

    # Exact alias match
    if cleaned in DISTRICT_ALIASES:
        return DISTRICT_ALIASES[cleaned]

    # Substring search — longest alias first so "navi mumbai" beats "mumbai"
    for alias, canonical in sorted(DISTRICT_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, cleaned):
            return canonical

    return default


# ---------------------------------------------------------------------------
# Content Hashing & Freshness Utilities
# ---------------------------------------------------------------------------

def compute_content_hash(*parts: Any) -> str:
    """Compute a deterministic SHA-256 hash from normalized string fields.

    Used for deduplicating external postings even when IDs differ across providers.
    """
    normalized_parts = [str(p or "").strip().lower() for p in parts]
    payload = "|".join(normalized_parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_freshness(
    published_at: str | None = None,
    snapshot_captured_at: str | None = None,
    last_seen_at: str | None = None,
) -> str:
    """Classify record freshness based on genuine publication or snapshot capture age.

    Rules:
    - Never default an unknown date to 'now' (which would falsely label stale/snapshot data as NEW).
    - If provider publication timestamp exists, use it.
    - For snapshots, use the actual snapshot capture timestamp.
    - If neither publication nor capture timestamp is provided, return 'UNKNOWN'.

    Age thresholds:
    - NEW: <= 7 days
    - RECENT: 8 to 30 days
    - OLDER: 31 to 90 days
    - STALE: 91 to 180 days
    - EXPIRED: > 180 days
    - UNKNOWN: missing or unparseable timestamp
    """
    ts_str = published_at or snapshot_captured_at
    if not ts_str:
        return "UNKNOWN"

    try:
        clean_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        delta_days = (now - dt).days

        if delta_days < 0:
            # Future date or minor clock skew
            return "NEW"
        elif delta_days <= 7:
            return "NEW"
        elif delta_days <= 30:
            return "RECENT"
        elif delta_days <= 90:
            return "OLDER"
        elif delta_days <= 180:
            return "STALE"
        else:
            return "EXPIRED"
    except Exception:
        return "UNKNOWN"


# ---------------------------------------------------------------------------
# Provenance Metadata Schema
# ---------------------------------------------------------------------------

class ProvenanceMetadata(BaseModel):
    """Standardized, unforgeable provenance stamp attached to all ingested records."""
    source: str = Field(..., description="Provider identifier (e.g., ADZUNA_API, OGD_DATAGOV_IN)")
    source_type: str = Field(
        ...,
        description="Explicit classification: LIVE_API, VERIFIED_SNAPSHOT, SANDBOX_SIMULATION, DEMO_SYNTHETIC",
    )
    source_label: str = Field(..., description="Human-readable provenance label")
    source_record_id: str = Field(..., description="Upstream external record identifier")
    resource_id: str | None = Field(default=None, description="Dataset/catalog resource ID if applicable")
    source_url: str = Field(..., description="Verifiable link to original posting or dataset")
    content_hash: str = Field(..., description="Deterministic SHA-256 signature for deduplication")
    fetched_at: str = Field(..., description="Timestamp when record was fetched or historical snapshot captured")
    published_at: str | None = Field(default=None, description="Original publication timestamp from provider")
    snapshot_captured_at: str | None = Field(default=None, description="Historical capture timestamp if source is a snapshot")
    last_seen_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    verified_at: str | None = Field(default=None, description="Timestamp when verification rules passed")
    verification_status: str = Field(
        default="UNVERIFIED",
        description="VERIFIED, PENDING, UNVERIFIED, REJECTED, EXPIRED, SIMULATED",
    )
    verification_method: str = Field(
        default="STRUCTURAL_API_VALIDATION",
        description="STRUCTURAL_API_VALIDATION, GOVERNMENT_PORTAL_API_FEED, GSTIN_SYNTAX_VALIDATED, SANDBOX_SIMULATION",
    )
    confidence: int = Field(default=0, ge=0, le=100)
    freshness_status: str = Field(default="UNKNOWN")
    is_demo: bool = False
    is_snapshot: bool = False


# ---------------------------------------------------------------------------
# Skill Keyword Matching & Unmapped Skill Extraction
# ---------------------------------------------------------------------------

# Common stop words to exclude when discovering unmapped technical keywords
COMMON_NON_SKILL_WORDS: set[str] = {
    "the", "and", "for", "with", "this", "that", "from", "will", "are", "have",
    "has", "had", "job", "role", "work", "team", "year", "years", "degree",
    "experience", "skills", "candidate", "responsibilities", "requirements",
    "preferred", "salary", "pune", "mumbai", "india", "maharashtra", "apply",
    "company", "industry", "required", "knowledge", "ability", "strong", "good",
    "hands", "must", "should", "including", "across", "other", "such", "well",
    "also", "high", "level", "related", "relevant", "seeking", "looking",
}

# Technical keywords / frameworks that frequently appear as unmapped skills
KNOWN_TECH_TOKENS: set[str] = {
    "kubernetes", "docker", "pytorch", "tensorflow", "fastapi", "nextjs", "react",
    "vue", "angular", "rust", "golang", "redis", "kafka", "graphql", "terraform",
    "ansible", "airflow", "snowflake", "databricks", "solidity", "langchain",
    "opencv", "scada", "plc", "autocad", "catia", "solidworks", "ansys", "matlab",
    "simulink", "embedded", "firmware", "iot", "ros", "bms", "canbus",
}


def extract_skills_and_unmapped(
    text: str,
    master_skills: list[dict[str, Any]],
    max_skills: int = 8,
    max_unmapped: int = 8,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Match words against canonical master skill records AND capture unmapped technical skills.

    Safety:
    - Single/two-letter tokens like 'C', 'R', 'Go' are checked with strict language context
      to avoid matching standard English words ("go to our site", "c suite").
    - Non-taxonomy technical terms are gathered into unmapped_skills for future expansion.
    """
    if not text:
        return [], []

    matched = []
    matched_ids = set()
    matched_skill_names_lower = set()

    for skill in master_skills:
        if len(matched) >= max_skills:
            break

        name = skill.get("name", "").strip()
        sid = skill.get("id")
        if not name or sid in matched_ids:
            continue

        name_lower = name.lower()

        # Short acronym context guard
        is_short = len(name) <= 2
        is_matched = False

        if is_short:
            # Require technical context words or specific casing
            if name_lower == "c":
                pattern = r"\b(c\s*\+\+|c/c\+\+|embedded\s+c|c\s+programming|ansi\s+c)\b"
                if re.search(pattern, text, re.IGNORECASE):
                    is_matched = True
            elif name_lower == "r":
                pattern = r"\b(r\s+programming|r\s+language|r\s+studio|r/python)\b"
                if re.search(pattern, text, re.IGNORECASE):
                    is_matched = True
            elif name_lower == "go":
                pattern = r"\b(golang|go\s+programming|go\s+developer|go\s+backend)\b"
                if re.search(pattern, text, re.IGNORECASE):
                    is_matched = True
            else:
                pattern = r"\b" + re.escape(name) + r"\b"
                if re.search(pattern, text):
                    is_matched = True
        else:
            pattern = r"\b" + re.escape(name_lower) + r"\b"
            if re.search(pattern, text, re.IGNORECASE):
                is_matched = True

        if not is_matched:
            # Check synonyms
            for syn in skill.get("synonyms", []):
                if not syn:
                    continue
                syn_lower = syn.lower()
                syn_pat = r"\b" + re.escape(syn_lower) + r"\b"
                if re.search(syn_pat, text, re.IGNORECASE):
                    is_matched = True
                    matched_skill_names_lower.add(syn_lower)  # prevent synonym appearing in unmapped
                    break

        if is_matched:
            matched.append(skill)
            matched_ids.add(sid)
            matched_skill_names_lower.add(name_lower)

    # Extract unmapped technical skills
    unmapped: list[str] = []
    unmapped_seen = set()

    # Match tokens: alphanumeric with optional dots, hyphens, pluses
    raw_tokens = re.findall(r"\b[A-Za-z0-9+#\.\-]{2,20}\b", text)
    for tok in raw_tokens:
        if len(unmapped) >= max_unmapped:
            break
        cleaned_tok = tok.strip(".-").lower()
        if len(cleaned_tok) < 2 or cleaned_tok in COMMON_NON_SKILL_WORDS:
            continue
        if cleaned_tok in matched_skill_names_lower or cleaned_tok in unmapped_seen:
            continue

        # Check if it matches known technical tokens or technical pattern
        if cleaned_tok in KNOWN_TECH_TOKENS or (tok[0].isupper() and bool(re.search(r"[A-Z0-9]", tok[1:]))):
            display_tok = tok.strip(".-")
            unmapped.append(display_tok)
            unmapped_seen.add(cleaned_tok)

    return matched, unmapped


def extract_skills_from_text(
    text: str,
    master_skills: list[dict[str, Any]],
    max_skills: int = 8,
) -> list[dict[str, Any]]:
    """Helper preserving backwards-compatible signature returning list of matched skills."""
    matched, _ = extract_skills_and_unmapped(text, master_skills, max_skills=max_skills)
    return matched


# ---------------------------------------------------------------------------
# BaseSourceAdapter Abstract Interface
# ---------------------------------------------------------------------------

class BaseSourceAdapter(abc.ABC):
    """Abstract Base Class for all SkillSetu data source adapters."""

    def __init__(self, source_name: str, timeout_seconds: float = 30.0, max_retries: int = 3):
        self.source_name = source_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @abc.abstractmethod
    def fetch_raw(self, limit: int = 50, offset: int = 0, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch raw records from the external provider with retry logic."""
        raise NotImplementedError

    @abc.abstractmethod
    def validate_and_transform(self, raw_records: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        """Validate raw records against Pydantic models, apply normalization and attach provenance."""
        raise NotImplementedError

    @abc.abstractmethod
    def verify_record(self, record: dict[str, Any]) -> tuple[bool, str, int]:
        """Verify record authenticity. Returns (is_verified, verification_method, confidence_score)."""
        raise NotImplementedError
