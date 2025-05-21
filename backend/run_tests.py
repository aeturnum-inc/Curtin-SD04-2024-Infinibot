"""
Test runner script for the authentication and RBAC components.
"""
import sys
import subprocess
import argparse

def run_tests(test_type=None, coverage=True, verbose=True):
    """Run tests with specified options"""
    cmd = ["python", "-m", "pytest"]
    
    if test_type:
        if test_type == "unit":
            cmd.extend(["-m", "unit"])
        elif test_type == "auth":
            cmd.extend(["-m", "auth"])
        elif test_type == "rbac":
            cmd.extend(["-m", "rbac"])
    
    if coverage:
        cmd.extend(["--cov=app.core.auth", "--cov=app.services.document_permission"])
        cmd.extend(["--cov-report=term-missing", "--cov-report=html"])
    
    if verbose:
        cmd.append("-v")
    
    # Add color output
    cmd.append("--color=yes")
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="Run auth and RBAC tests")
    parser.add_argument(
        "--type", 
        choices=["unit", "auth", "rbac", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true", 
        help="Disable coverage reporting"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Run tests quietly"
    )
    
    args = parser.parse_args()
    
    test_type = args.type if args.type != "all" else None
    coverage = not args.no_coverage
    verbose = not args.quiet
    
    result = run_tests(test_type, coverage, verbose)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()