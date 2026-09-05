"""Institute Syllabus Ingestion & NLP Skill Extraction Service.

Extracts industry-aligned skills, NSQF levels, and domain categories directly
from course syllabus documents (PDF or plain text) using zero external dependencies.
"""
import re
import zlib
from collections import Counter
from typing import Any
from app.db import get_demo


def extract_raw_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract readable text streams from PDF bytes without requiring external binary packages."""
    if not pdf_bytes:
        return ""

    texts: list[str] = []
    # Match PDF stream blocks: stream\r?\n ... \r?\nendstream
    stream_pattern = re.compile(b"stream[\r\n]+(.*?)[\r\n]+endstream", re.DOTALL)

    for match in stream_pattern.finditer(pdf_bytes):
        raw_stream = match.group(1)
        decompressed: bytes = b""

        # Attempt FlateDecode decompression (standard in 99% of generated PDFs)
        try:
            decompressed = zlib.decompress(raw_stream)
        except Exception:
            # Might be raw uncompressed stream or unsupported filter
            decompressed = raw_stream

        # 1. Extract text from standard Tj operators: (Sample Text) Tj
        for tj in re.finditer(rb"\((.*?)\)\s*Tj", decompressed):
            try:
                # Replace standard escaped parentheses and octal/hex
                val = tj.group(1).replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
                texts.append(val.decode("latin-1", errors="ignore"))
            except Exception:
                pass

        # 2. Extract text from array TJ operators: [(Part1) -100 (Part2)] TJ
        for array_tj in re.finditer(rb"\[(.*?)\]\s*TJ", decompressed):
            inner = array_tj.group(1)
            for part in re.finditer(rb"\((.*?)\)", inner):
                try:
                    val = part.group(1).replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
                    texts.append(val.decode("latin-1", errors="ignore"))
                except Exception:
                    pass

    # If stream extraction yielded content, join with spaces
    extracted = " ".join(texts).strip()
    if extracted:
        return extracted

    # Fallback: simple printable ASCII/Latin-1 extraction from entire document
    fallback_chars = []
    for byte in pdf_bytes:
        if (32 <= byte <= 126) or byte in (10, 13, 9):
            fallback_chars.append(chr(byte))
        else:
            fallback_chars.append(" ")
    return " ".join("".join(fallback_chars).split())


def extract_skills_from_syllabus(
    content: str | bytes,
    course_name_hint: str | None = None,
    is_demo: bool | None = None,
) -> dict[str, Any]:
    """Analyze syllabus text or PDF document and map contents to the standard skill taxonomy."""
    # 1. Obtain clean string text
    text = ""
    if isinstance(content, bytes):
        if content.startswith(b"%PDF-"):
            text = extract_raw_text_from_pdf(content)
        else:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="ignore")
    else:
        text = str(content)

    clean_text = " " + text.replace("\n", " ").replace("\r", " ") + " "
    clean_text_lower = clean_text.lower()

    # 2. Match against platform standard taxonomy
    from app.core.data_mode import is_explicit_demo_mode
    if is_explicit_demo_mode(is_demo):
        all_skills = get_demo("skills") or []
    else:
        try:
            from app.repositories.supabase_repository import list_skills
            all_skills = list_skills(limit=10000) or []
        except Exception:
            all_skills = []
    matched_skills = []
    seen_ids = set()
    category_counts: Counter[str] = Counter()
    nsqf_levels: list[int] = []

    for sk in all_skills:
        s_id = sk.get("id")
        s_name = sk.get("name", "")
        if not s_id or not s_name:
            continue

        # Look for exact word boundary matches for skill name and synonyms
        candidates = [s_name] + sk.get("synonyms", [])
        matched = False

        for cand in candidates:
            # Escape regex symbols in skill name (e.g. C++, .NET, AI/ML)
            escaped = re.escape(cand.lower())
            pattern = r"(?<![a-zA-Z0-9])" + escaped + r"(?![a-zA-Z0-9])"
            if re.search(pattern, clean_text_lower):
                matched = True
                break

        if matched and s_id not in seen_ids:
            seen_ids.add(s_id)
            nsqf = sk.get("nsqf_level", 5)
            cat = sk.get("category", "Vocational & Emerging Tech")
            matched_skills.append({
                "skill_id": s_id,
                "name": s_name,
                "category": cat,
                "nsqf_level": nsqf,
            })
            category_counts[cat] += 1
            nsqf_levels.append(nsqf)

    # 3. Derive suggested course parameters
    if nsqf_levels:
        suggested_nsqf = round(sum(nsqf_levels) / len(nsqf_levels))
    else:
        suggested_nsqf = 5

    if category_counts:
        suggested_category = category_counts.most_common(1)[0][0]
    else:
        suggested_category = "Vocational & Emerging Tech"

    extracted_skill_names = [m["name"] for m in matched_skills]

    # Generate suggested course title if not provided
    if course_name_hint and len(course_name_hint.strip()) >= 3:
        suggested_title = course_name_hint.strip()
    elif extracted_skill_names:
        top_skills = extracted_skill_names[:2]
        suggested_title = f"Advanced Certificate in {' & '.join(top_skills)}"
    else:
        suggested_title = "Modern Vocational Certification Program"

    summary = (
        f"Extracted {len(extracted_skill_names)} curriculum skills aligned with NSQF Level {suggested_nsqf} "
        f"in the {suggested_category} domain."
        if extracted_skill_names
        else "No recognized standard skills detected in syllabus. You can manually enter skills below."
    )

    return {
        "status": "success",
        "extracted_skills": extracted_skill_names,
        "matched_skills": matched_skills,
        "suggested_nsqf_level": max(1, min(10, suggested_nsqf)),
        "suggested_category": suggested_category,
        "suggested_course_name": suggested_title,
        "skills_count": len(extracted_skill_names),
        "text_length": len(text.strip()),
        "summary": summary,
    }
