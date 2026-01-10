"""
Master test runner for all agent and subagent tests.
Runs all individual test scripts and provides a summary.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_test_script(script_path):
    """Run a single test script and return results."""
    script_name = script_path.name

    print(f"\n{'=' * 70}")
    print(f"Running: {script_name}")
    print(f"{'=' * 70}")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Print output
        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("STDERR:", result.stderr)

        return {
            "script": script_name,
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except subprocess.TimeoutExpired:
        print(f"X TIMEOUT: {script_name} exceeded 60 seconds")
        return {
            "script": script_name,
            "passed": False,
            "returncode": -1,
            "error": "Timeout"
        }
    except Exception as e:
        print(f"X ERROR running {script_name}: {e}")
        return {
            "script": script_name,
            "passed": False,
            "returncode": -1,
            "error": str(e)
        }


def main():
    """Run all agent test scripts."""
    print("=" * 70)
    print("WEATHER AGENT TEST SUITE - MASTER RUNNER")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Get the tests directory
    tests_dir = Path(__file__).parent

    # Define test scripts in execution order
    test_scripts = [
        "test_forecast_writer_agent.py",
        "test_forecast_speaker_agent.py",
        "test_forecast_photographer_agent.py",
        "test_weather_studio_team.py",
        "test_root_agent.py"
    ]

    results = []

    # Run each test script
    for script_name in test_scripts:
        script_path = tests_dir / script_name

        if not script_path.exists():
            print(f"\nX WARNING: {script_name} not found, skipping...")
            results.append({
                "script": script_name,
                "passed": False,
                "error": "File not found"
            })
            continue

        result = run_test_script(script_path)
        results.append(result)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    for result in results:
        status = "* PASSED" if result["passed"] else "X FAILED"
        print(f"{status:12} {result['script']}")

        if not result["passed"] and "error" in result:
            print(f"             Error: {result['error']}")

    print("\n" + "-" * 70)
    print(f"Results: {passed_count}/{total_count} tests passed")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Exit with appropriate code
    if passed_count == total_count:
        print("\n*** ALL TESTS PASSED! ***\n")
        sys.exit(0)
    else:
        print(f"\nWARNING  {total_count - passed_count} TEST(S) FAILED WARNING\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
