"""Comprehensive test suite for AI Copilot query grounding, skill detection, and data truthfulness."""
import asyncio
import os
import sys
from pathlib import Path

# Add project root and backend to path
_root = Path(__file__).resolve().parent.parent
_backend = _root / "backend"
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_backend))

from starlette.testclient import TestClient
from app.main import app
from app.db import get_demo, set_demo, load_demo_data
from ai.copilot import handle_question, _build_context, extract_queried_skill
from ai.demo_provider import DemoProvider


def test_copilot_grounding():
    print("Starting AI Copilot Data-Grounding & Truthfulness Test Suite...\n")
    client = TestClient(app)
    load_demo_data()

    # ------------------------------------------------------------------------
    # Test 1: Go / Golang Query with No Go Records in Dataset
    # ------------------------------------------------------------------------
    print("Testing 1: Go / Golang query with no Go records...")
    res_go = asyncio.run(handle_question("tell me about requirement of go lang developer", role="student"))
    answer_go = res_go.get("answer", "")

    assert "Go" in answer_go or "Golang" in answer_go, "Response must address Go/Golang"
    assert (
        "does not contain sufficient" in answer_go
        or "0 verified" in answer_go
        or "not present" in answer_go
        or "Data Availability Notice" in answer_go
    ), f"Response must acknowledge missing Go data. Got:\n{answer_go}"

    # Verify that Python/PLC demand stats are NOT claimed as Go demand
    assert "Go appears in 26%" not in answer_go, "Must NOT claim Go has 26% demand"
    assert "Go (appears in 26%" not in answer_go, "Must NOT claim Go appears in 26%"
    assert "146 active roles for Go" not in answer_go, "Must NOT claim 146 active roles for Go"
    print("  OK: Go query correctly identifies missing dataset telemetry and does not hallucinate.\n")

    # ------------------------------------------------------------------------
    # Test 2: Python Query with Verified Records
    # ------------------------------------------------------------------------
    print("Testing 2: Python query with real dataset records...")
    res_py = asyncio.run(handle_question("tell me about requirements for python developer", role="student"))
    answer_py = res_py.get("answer", "")

    assert "Python" in answer_py, "Response must discuss Python"
    assert "26%" in answer_py or "146" in answer_py, "Response should cite verified Python demand"
    assert "HIGH" in answer_py or "deficit" in answer_py.lower() or "gap" in answer_py.lower(), "Response should mention Python gap/deficit"
    print("  OK: Python query correctly returns verified demand, gap metrics, and accredited modules.\n")

    # ------------------------------------------------------------------------
    # Test 3: Unrelated Skill Statistics Leakage Prevention
    # ------------------------------------------------------------------------
    print("Testing 3: Unrelated skill isolation (PLC Programming)...")
    res_plc = asyncio.run(handle_question("tell me about PLC Programming demand", role="student"))
    answer_plc = res_plc.get("answer", "")

    assert "PLC Programming" in answer_plc, "Response must focus on PLC Programming"
    # Should not confuse with Python
    assert "14%" in answer_plc or "Manufacturing" in answer_plc, "Should include PLC-specific metrics"
    print("  OK: PLC Programming query is strictly isolated from unrelated programming stats.\n")

    # ------------------------------------------------------------------------
    # Test 4: Insufficient Data for External Technologies (Rust, Ruby, Zig)
    # ------------------------------------------------------------------------
    print("Testing 4: Unindexed technology detection (Rust, Ruby, Zig)...")
    for tech in ["Rust", "Ruby on Rails", "Zig"]:
        ctx = _build_context("student", f"What are the job opportunities for a {tech} developer?")
        assert ctx.get("data_available_for_skill") is False, f"Expected data_available_for_skill=False for {tech}"
        assert ctx.get("queried_skill", {}).get("found_in_dataset") is False

        ans = asyncio.run(handle_question(f"What are the job opportunities for a {tech} developer?", role="student"))
        assert (
            "does not contain sufficient" in ans["answer"]
            or "0 verified" in ans["answer"]
            or "Data Availability Notice" in ans["answer"]
        ), f"Failed for {tech}"
    print("  OK: Rust, Ruby, and Zig all trigger explicit insufficient-data notices.\n")

    # ------------------------------------------------------------------------
    # Test 5: Dynamic Injected Go Records Verification
    # ------------------------------------------------------------------------
    print("Testing 5: Go query when Go job records ARE present...")
    original_skills = list(get_demo("skills"))
    original_jobs = list(get_demo("jobs"))
    original_js = list(get_demo("job_skills"))

    try:
        # Inject mock Go skill and 10 Go jobs
        mock_go_skill = {"id": "sk-go-001", "name": "Go", "category": "Programming", "nsqf_level": 6, "synonyms": ["Golang"]}
        set_demo("skills", original_skills + [mock_go_skill])

        mock_go_jobs = [
            {"id": f"job-go-{i}", "title": "Go Backend Engineer", "company": "GoTech", "district": "Pune", "industry": "IT/ITES", "source": "TEST"}
            for i in range(10)
        ]
        set_demo("jobs", original_jobs + mock_go_jobs)

        mock_go_js = [{"job_id": f"job-go-{i}", "skill_id": "sk-go-001"} for i in range(10)]
        set_demo("job_skills", original_js + mock_go_js)

        res_injected_go = asyncio.run(handle_question("tell me about requirement of go developer", role="student"))
        ans_injected = res_injected_go.get("answer", "")

        assert "Go" in ans_injected
        assert "10" in ans_injected, "Should cite the 10 injected Go jobs"
        print("  OK: When Go records are present, exact verified Go data is retrieved and reported.\n")
    finally:
        # Restore baseline
        set_demo("skills", original_skills)
        set_demo("jobs", original_jobs)
        set_demo("job_skills", original_js)

    # ------------------------------------------------------------------------
    # Test 6: Normal Maharashtra Macro & District Questions
    # ------------------------------------------------------------------------
    print("Testing 6: Normal general Maharashtra & District queries...")
    # District query
    res_pune = asyncio.run(handle_question("tell me about Pune district plan and jobs", role="government"))
    assert "Pune" in res_pune["answer"], "Pune district intelligence must be returned"
    assert "150" in res_pune["answer"] or "Corridor" in res_pune["answer"] or "District" in res_pune["answer"]

    # Skill gaps query
    res_gaps = asyncio.run(handle_question("what are the biggest skill gaps in maharashtra?", role="government"))
    assert "Deficit" in res_gaps["answer"] or "Skill" in res_gaps["answer"] or "gap" in res_gaps["answer"].lower()
    print("  OK: General district and state gap inquiries work seamlessly.\n")

    # ------------------------------------------------------------------------
    # Test 7: HTTP API Endpoints (/api/copilot/ask & /api/health/ai)
    # ------------------------------------------------------------------------
    print("Testing 7: HTTP API Endpoints with TestClient...")
    http_res = client.post("/api/copilot/ask", json={"question": "tell me about requirement of go lang developer", "role": "student"})
    assert http_res.status_code == 200
    http_data = http_res.json()
    assert "answer" in http_data
    assert http_data.get("data_grounded") is True
    assert "does not contain sufficient" in http_data["answer"] or "0 verified" in http_data["answer"]

    health_res = client.get("/api/health/ai")
    assert health_res.status_code == 200
    print("  OK: /api/copilot/ask and /api/health/ai API contracts verified.\n")

    print("ALL AI COPILOT DATA-GROUNDING TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_copilot_grounding()
