#!/usr/bin/env python3
"""SkillSetu Production Backend Warm-Up & Health Probe Utility (Phase 36).

Used before SIH live demonstrations to ensure the cloud backend on Render
and Supabase database are hot and ready for zero-latency presentation.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_HEALTH_URL = "https://skill-setu-backend-jklo.onrender.com/api/health"


def probe_backend(url: str = DEFAULT_HEALTH_URL, max_retries: int = 5, retry_delay: float = 4.0):
    print("=" * 65)
    print("SKILLSETU DEMO WARM-UP & HEALTH PROBE")
    print(f"Target URL : {url}")
    print(f"Max Retries: {max_retries}")
    print("=" * 65)

    for attempt in range(1, max_retries + 1):
        t0 = time.time()
        print(f"\n[Attempt {attempt}/{max_retries}] Pinging canonical health endpoint...")
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SkillSetu-Warmup-Probe/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=25) as response:
                elapsed_ms = (time.time() - t0) * 1000
                status_code = response.status
                body = response.read().decode("utf-8")

                if status_code == 200:
                    data = json.loads(body)
                    print(f"  --> HTTP {status_code} OK ({elapsed_ms:.1f} ms)")
                    print("-" * 65)
                    print(f"  Service Status     : {data.get('status', 'unknown').upper()}")
                    print(f"  Supabase Connected : {data.get('supabase_connected', False)}")
                    print(f"  AI Available       : {data.get('ai_available', False)}")
                    print(f"  Records In-Memory  : {data.get('records_loaded', 0)}")
                    print(f"  Demo Mode Overlay  : {data.get('demo_mode', False)}")
                    print(f"  Active Districts   : {data.get('districts_count', 0)}")
                    print("-" * 65)
                    print("SUCCESS: Production backend is warm and ready for presentation!")
                    print("=" * 65)
                    return True, data, elapsed_ms
                else:
                    print(f"  --> HTTP {status_code} returned. Retrying in {retry_delay}s...")
        except urllib.error.HTTPError as e:
            elapsed_ms = (time.time() - t0) * 1000
            print(f"  --> HTTP Error {e.code}: {e.reason} ({elapsed_ms:.1f} ms)")
        except urllib.error.URLError as e:
            elapsed_ms = (time.time() - t0) * 1000
            print(f"  --> Connection Error: {e.reason} (Server likely spinning up from cold state: {elapsed_ms:.1f} ms)")
        except Exception as e:
            elapsed_ms = (time.time() - t0) * 1000
            print(f"  --> Unexpected error: {e} ({elapsed_ms:.1f} ms)")

        if attempt < max_retries:
            time.sleep(retry_delay)

    print("\nFAILED: Backend could not be reached or confirmed within specified retries.")
    return False, {}, 0.0


def main():
    parser = argparse.ArgumentParser(description="SkillSetu Production Warm-Up Utility")
    parser.add_argument(
        "--url",
        default=os.getenv("SKILLSETU_BACKEND_URL", DEFAULT_HEALTH_URL),
        help="Health endpoint URL (default: live Render backend)",
    )
    parser.add_argument("--retries", type=int, default=4, help="Maximum probe retries (default: 4)")
    parser.add_argument("--delay", type=float, default=4.0, help="Delay between retries in seconds (default: 4.0)")
    args = parser.parse_args()

    success, _, _ = probe_backend(url=args.url, max_retries=args.retries, retry_delay=args.delay)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
