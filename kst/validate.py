"""Check that an analyzer's stdout is a usable JSON report.

Usage: python3 -m kst.validate FILE   (prints the problem and exits 1, or exits 0)
Both analyzers exit non-zero whenever they find problems, so the exit code says nothing
about a crash. A crash shows as empty or non-JSON stdout instead.
"""
import json
import sys


def output_problem(path):
    """None if the file holds a JSON array or object, otherwise a short reason."""
    with open(path) as f:
        text = f.read()
    if not text.strip():
        return "empty output"
    try:
        data = json.loads(text)
    except ValueError:
        return "not JSON"
    if not isinstance(data, (list, dict)):
        return "not a JSON array or object"
    return None


if __name__ == "__main__":
    problem = output_problem(sys.argv[1])
    if problem:
        print(problem)
        sys.exit(1)
