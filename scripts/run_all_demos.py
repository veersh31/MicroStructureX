"""
Run all demo scripts in sequence.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import subprocess
import time


def run_demo(script_name: str, description: str):
    """Run a single demo script"""
    print("\n" + "🚀 " + "=" * 58)
    print(f"   Running: {description}")
    print("=" * 60)
    print()

    time.sleep(1)

    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / script_name)],
        capture_output=False
    )

    if result.returncode != 0:
        print(f"\n❌ Demo failed with exit code {result.returncode}")
        return False

    print("\n⏸️  Press Enter to continue to next demo...")
    input()

    return True


def main():
    print("=" * 60)
    print("   Market Microstructure - Demo Suite")
    print("=" * 60)
    print()
    print("This will run all demonstration scripts in sequence.")
    print("Each demo showcases different aspects of the system.")
    print()
    print("Press Enter to start...")
    input()

    demos = [
        ("demo_basic_matching.py", "Basic Order Matching"),
        ("demo_market_replay.py", "Market Replay Engine"),
        ("demo_twap_strategy.py", "TWAP Execution Strategy"),
    ]

    for script, description in demos:
        success = run_demo(script, description)
        if not success:
            print("\n❌ Demo suite stopped due to error.")
            sys.exit(1)

    print("\n" + "✅ " + "=" * 58)
    print("   All Demos Completed Successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  • Explore the Jupyter notebooks in notebooks/")
    print("  • Review the API documentation at http://localhost:8000/docs")
    print("  • Check out the test suite in tests/")
    print("  • Read the README.md for more information")
    print()


if __name__ == "__main__":
    main()
