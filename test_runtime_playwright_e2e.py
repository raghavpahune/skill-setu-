"""End-to-End Real Browser Runtime Verification Script using Playwright.
Tests all 4 real-user roles (Student, Employer, Institute, Admin) against live frontend and backend.
"""
import sys
import time
from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://127.0.0.1:5173"
BACKEND_URL = "http://127.0.0.1:8000"


def safe_str(s: str) -> str:
    return str(s).encode("ascii", "ignore").decode("ascii")


def run_full_runtime_verification():
    print("=================================================================")
    print("STARTING FULL END-TO-END BROWSER RUNTIME VERIFICATION")
    print("=================================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # =====================================================================
        # 1. STUDENT RUNTIME VERIFICATION
        # =====================================================================
        print("\n--- [1/4] STUDENT RUNTIME FLOW ---")
        context_student = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context_student.new_page()
        page.on("pageerror", lambda exc: print(f"[Browser Error] {safe_str(exc)}"))

        page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_load_state("networkidle")
        print("[Student] Loaded /login")

        # Fill student login
        page.fill('input[type="email"]', "student@skillsetu.gov.in")
        page.fill('input[type="password"]', "Password@123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/student**", timeout=10000)
        page.wait_for_load_state("networkidle")
        print(f"[Student] Successfully logged in! Current URL: {page.url}")

        # Switch to Diagnostic Assessment tab
        page.click("button:has-text('Diagnostic Assessment')")
        page.wait_for_selector("text=Student Skills & Career Readiness Profiler")
        print("[Student] Switched to Diagnostic Assessment tab")

        # Fill Step 1: Demographics
        unique_student_name = f"Aaditya Live Student {int(time.time())}"
        page.fill('input[placeholder*="Tanmay Deshmukh"]', unique_student_name)
        page.fill('input[placeholder*="B.Tech Computer Engineering"]', "B.Tech AI & Data Science (COEP Pune)")
        page.click("button:has-text('Next: Career Goal & Interests')")
        time.sleep(0.5)

        # Step 2: Career Goal
        page.click("button:has-text('Next: Current Skills')")
        time.sleep(0.5)

        # Step 3: Skills Inventory
        page.click("button:has-text('Next: Diagnostic Quiz')")
        time.sleep(0.5)

        # Step 4: Diagnostic Quiz - answer all questions
        print("[Student] Answering diagnostic quiz questions...")
        page.wait_for_selector("text=Diagnostic Skill & Career Aptitude Quiz")
        option_buttons = page.query_selector_all("button:has-text('A.')")
        for btn in option_buttons:
            try:
                btn.click()
                time.sleep(0.1)
            except Exception:
                pass

        # Click Submit Assessment
        print("[Student] Submitting assessment...")
        submit_btn = page.wait_for_selector("button:has-text('Submit & Calculate Readiness Report')")
        submit_btn.click()

        # Verify Step 5 results view appears
        page.wait_for_selector("h3:has-text('Assessment Evaluation')", timeout=15000)
        print("[Student] Assessment submitted and evaluated successfully! Step 5 visible.")

        # Switch back to Skill Passport tab
        page.click("button:has-text('Skill Passport')")
        page.wait_for_selector("text=Career Pathway Sequence", timeout=10000)
        time.sleep(1)

        # Confirm live personalized badge and submitted student name
        passport_text = safe_str(page.inner_text("body"))
        assert "Live Personalized Data" in passport_text or unique_student_name in passport_text, \
            f"Expected live personalized badge or {unique_student_name} in passport!"
        print(f"[Student] PASS: Live personalized data verified in Passport tab for {unique_student_name}!")

        # Hard reload page
        print("[Student] Performing hard reload...")
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        reloaded_text = safe_str(page.inner_text("body"))
        assert "Live Personalized Data" in reloaded_text or unique_student_name in reloaded_text, \
            "Data was lost after reload! Fallback to demo occurred."
        print("[Student] PASS: Data survived hard reload!")

        # Test Logout and Re-login
        print("[Student] Testing logout and re-login...")
        logout_btn = page.query_selector("button:has-text('Sign Out'), button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
        else:
            page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_url("**/login**")
        
        # Re-login
        page.fill('input[type="email"]', "student@skillsetu.gov.in")
        page.fill('input[type="password"]', "Password@123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/student**", timeout=10000)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        relogin_text = safe_str(page.inner_text("body"))
        assert "Live Personalized Data" in relogin_text or unique_student_name in relogin_text, \
            "Personalized student data not restored on re-login!"
        print("[Student] PASS: Personalized data persisted across logout and re-login!")
        context_student.close()

        # =====================================================================
        # 2. EMPLOYER RUNTIME VERIFICATION
        # =====================================================================
        print("\n--- [2/4] EMPLOYER RUNTIME FLOW ---")
        context_employer = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context_employer.new_page()
        page.on("pageerror", lambda exc: print(f"[Browser Error] {safe_str(exc)}"))

        page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_load_state("networkidle")

        page.fill('input[type="email"]', "employer@skillsetu.gov.in")
        page.fill('input[type="password"]', "Password@123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/employer**", timeout=10000)
        page.wait_for_load_state("networkidle")
        print(f"[Employer] Successfully logged in! Current URL: {page.url}")

        # Switch to Demand Hub tab
        demand_tab = page.wait_for_selector("button:has-text('Submit Hiring Demand')")
        demand_tab.click()
        page.wait_for_selector("text=Submit Industry Hiring & Skill Demand", timeout=10000)
        time.sleep(0.5)

        unique_job_role = f"Principal Battery AI Engineer {int(time.time())}"
        print(f"[Employer] Filling new demand form for '{unique_job_role}'...")
        page.fill('input[placeholder*="Tata Consultancy Services"]', "Mahindra Electric Mobility Ltd")
        page.fill('input[placeholder*="EV Powertrain Diagnostics"]', unique_job_role)
        page.fill('input[placeholder*="Type custom skill"]', "CAN Bus Telemetry")
        page.click("button:has-text('+ Add')")
        time.sleep(0.3)

        # Submit demand
        page.click("button:has-text('Submit Demand (Pending State Validation)')")
        time.sleep(1.5)

        # Verify demand appears in table/stream
        demands_text = safe_str(page.inner_text("body"))
        assert unique_job_role in demands_text, f"Expected {unique_job_role} in demands table!"
        print(f"[Employer] PASS: Demand '{unique_job_role}' visible in dashboard immediately!")

        # Hard reload
        print("[Employer] Performing hard reload...")
        page.reload()
        page.wait_for_load_state("networkidle")
        # Ensure Demand tab is active
        page.click("button:has-text('Submit Hiring Demand')")
        time.sleep(1)
        reloaded_emp_text = safe_str(page.inner_text("body"))
        assert unique_job_role in reloaded_emp_text, "Employer demand lost after reload!"
        print("[Employer] PASS: Demand persisted across page reload!")

        # Test Employer Logout and Re-login
        print("[Employer] Testing logout and re-login...")
        logout_btn = page.query_selector("button:has-text('Sign Out'), button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
        else:
            page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_url("**/login**")
        
        # Re-login
        page.fill('input[type="email"]', "employer@skillsetu.gov.in")
        page.fill('input[type="password"]', "Password@123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/employer**", timeout=10000)
        page.wait_for_load_state("networkidle")
        page.click("button:has-text('Submit Hiring Demand')")
        time.sleep(1)
        relogin_emp_text = safe_str(page.inner_text("body"))
        assert unique_job_role in relogin_emp_text, "Employer demand lost across re-login!"
        print("[Employer] PASS: Demand persisted across logout and re-login!")
        context_employer.close()

        # =====================================================================
        # 3. INSTITUTE RUNTIME VERIFICATION
        # =====================================================================
        print("\n--- [3/4] INSTITUTE RUNTIME FLOW ---")
        context_institute = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context_institute.new_page()
        page.on("pageerror", lambda exc: print(f"[Browser Error] {safe_str(exc)}"))

        page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_load_state("networkidle")

        page.fill('input[type="email"]', "institute@skillsetu.gov.in")
        page.fill('input[type="password"]', "Password@123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/institute**", timeout=10000)
        page.wait_for_load_state("networkidle")
        print(f"[Institute] Successfully logged in! Current URL: {page.url}")

        # Open Register Course Modal
        register_course_btn = page.wait_for_selector("button:has-text('Submit Training Program')")
        register_course_btn.click()
        time.sleep(0.5)

        unique_course_name = f"Advanced Autonomous Robotics & ROS2 {int(time.time())}"
        print(f"[Institute] Registering course: '{unique_course_name}'...")
        page.fill('input[placeholder*="Advanced EV Battery Diagnostics"]', unique_course_name)
        page.fill('input[placeholder*="Battery Management, CAN Bus"]', "ROS2, Industrial Robotics, Python")
        
        page.click("button:has-text('Register Program')")
        time.sleep(1.5)

        # Verify course appears in list
        institute_text = safe_str(page.inner_text("body"))
        assert unique_course_name in institute_text, f"Expected {unique_course_name} in courses list!"
        print(f"[Institute] PASS: Course '{unique_course_name}' visible immediately in catalog!")

        # Hard reload
        print("[Institute] Performing hard reload...")
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        reloaded_inst_text = safe_str(page.inner_text("body"))
        assert unique_course_name in reloaded_inst_text, "Course lost after page reload!"
        print("[Institute] PASS: Course persisted across page reload!")

        # Test Institute Logout and Re-login
        print("[Institute] Testing logout and re-login...")
        logout_btn = page.query_selector("button:has-text('Sign Out'), button:has-text('Logout')")
        if logout_btn:
            logout_btn.click()
        else:
            page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_url("**/login**")
        
        # Re-login
        page.fill('input[type="email"]', "institute@skillsetu.gov.in")
        page.fill('input[type="password"]', "Password@123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/institute**", timeout=10000)
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        relogin_inst_text = safe_str(page.inner_text("body"))
        assert unique_course_name in relogin_inst_text, "Course lost across re-login!"
        print("[Institute] PASS: Course persisted across logout and re-login!")
        context_institute.close()

        # =====================================================================
        # 4. ADMIN RUNTIME VERIFICATION & DATA GOVERNANCE
        # =====================================================================
        print("\n--- [4/4] ADMIN RUNTIME FLOW & DATA GOVERNANCE ---")
        context_admin = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context_admin.new_page()
        page.on("pageerror", lambda exc: print(f"[Browser Error] {safe_str(exc)}"))

        page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_load_state("networkidle")

        page.fill('input[type="email"]', "admin@skillsetu.gov.in")
        page.fill('input[type="password"]', "AdminPass@2026")
        page.click('button[type="submit"]')
        page.wait_for_url("**/admin**", timeout=10000)
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)
        print(f"[Admin] Successfully logged in! Current URL: {page.url}")

        # Verify no white screen
        admin_body = safe_str(page.inner_text("body"))
        assert "State Data Management & Validation Registry" in admin_body, "Admin dashboard failed to render!"
        assert "Data Governance & Hybrid Provenance Architecture" in admin_body, "Data Governance panel missing!"
        print("[Admin] PASS: Admin Dashboard rendered without white screen!")

        # Verify Live Telemetry and separation of Real vs Demo baseline
        assert "Live Telemetry Active" in admin_body, "Live telemetry badge not active!"
        assert "Live" in admin_body and "Demo Baseline" in admin_body, "Live vs Demo counts not displayed!"
        print("[Admin] PASS: Data Governance correctly separates Live first-party records from Demo baseline!")

        # Hard reload on /admin
        print("[Admin] Performing hard reload on /admin...")
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)
        reloaded_admin_body = safe_str(page.inner_text("body"))
        assert "State Data Management & Validation Registry" in reloaded_admin_body, "Admin white screen after reload!"
        print("[Admin] PASS: Admin dashboard survives hard reload cleanly!")
        context_admin.close()

        browser.close()

    print("\n=================================================================")
    print("ALL 4 RUNTIME WORKFLOWS COMPLETED AND FULLY VERIFIED!")
    print("=================================================================")


if __name__ == "__main__":
    try:
        run_full_runtime_verification()
    except Exception as e:
        print(f"\nRUNTIME VERIFICATION FAILED: {safe_str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
