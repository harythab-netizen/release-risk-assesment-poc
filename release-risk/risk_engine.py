import argparse
import json
import subprocess
from pathlib import Path

import yaml


BASE_DIR = Path(__file__).resolve().parent
RULES_FILE = BASE_DIR / "rules.yaml"


def run_git_command(args):
    """Run a Git command and return its output."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def load_rules():
    """Load release risk rules from rules.yaml."""
    with open(RULES_FILE, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_changed_files(base, target):
    """Return files changed between two Git revisions."""
    output = run_git_command(
        ["diff", "--name-only", base, target]
    )

    if not output:
        return []

    return output.splitlines()


def get_commit_count(base, target):
    """Count commits between the baseline and target."""
    output = run_git_command(
        ["rev-list", "--count", f"{base}..{target}"]
    )

    return int(output)


def classify_risk(score, config):
    """Convert numerical score into a risk level."""

    levels = config["risk_levels"]

    for level, limits in levels.items():
        if limits["min"] <= score <= limits["max"]:
            return level.upper()

    return "CRITICAL"


def add_factor(factors, rule_name, rules):
    """Add a risk factor using its configured score."""

    rule = rules[rule_name]

    factors.append(
        {
            "rule": rule_name,
            "score": rule["score"],
            "description": rule["description"],
        }
    )


def assess_release(base, target, branch):
    """Assess release risk."""

    config = load_rules()
    rules = config["rules"]

    changed_files = get_changed_files(base, target)
    commit_count = get_commit_count(base, target)

    factors = []

    # --------------------------------------------------
    # Branch risk
    # --------------------------------------------------

    if branch.startswith("hotfix/"):
        add_factor(factors, "hotfix_branch", rules)

    # --------------------------------------------------
    # Change-set size
    # --------------------------------------------------

    file_count = len(changed_files)

    if file_count > 20:
        add_factor(factors, "large_change_set", rules)

    elif file_count >= 10:
        add_factor(factors, "medium_change_set", rules)

    # --------------------------------------------------
    # Commit volume
    # --------------------------------------------------

    if commit_count > 20:
        add_factor(factors, "large_commit_volume", rules)

    elif commit_count > 10:
        add_factor(factors, "medium_commit_volume", rules)

    # --------------------------------------------------
    # File categories
    # --------------------------------------------------

    dependency_files = {
        "requirements.txt",
        "pom.xml",
        "package.json",
        "package-lock.json",
        "build.gradle",
        "gradle.properties",
    }

    if any(Path(file).name in dependency_files for file in changed_files):
        add_factor(factors, "dependency_change", rules)

    if any(file.startswith("config/") for file in changed_files):
        add_factor(factors, "configuration_change", rules)

    if any(file.startswith(".github/workflows/") for file in changed_files):
        add_factor(factors, "workflow_change", rules)

    if any(file.startswith("src/") for file in changed_files):
        add_factor(factors, "source_code_change", rules)

    # --------------------------------------------------
    # Calculate final score
    # --------------------------------------------------

    raw_score = sum(factor["score"] for factor in factors)

    score = min(raw_score, 100)

    level = classify_risk(score, config)

    return {
        "baseline": base,
        "target": target,
        "branch": branch,
        "changed_file_count": file_count,
        "commit_count": commit_count,
        "changed_files": changed_files,
        "risk_score": score,
        "risk_level": level,
        "risk_factors": factors,
    }


def print_report(result):
    """Print human-readable release risk report."""

    print()
    print("=" * 60)
    print("RELEASEGUARD - RELEASE RISK ASSESSMENT")
    print("=" * 60)

    print(f"Baseline       : {result['baseline']}")
    print(f"Target         : {result['target']}")
    print(f"Branch         : {result['branch']}")
    print(f"Changed files  : {result['changed_file_count']}")
    print(f"Commits        : {result['commit_count']}")

    print()
    print("-" * 60)
    print(
        f"RISK RESULT: {result['risk_level']} "
        f"({result['risk_score']}/100)"
    )
    print("-" * 60)

    print()
    print("Risk contributors:")

    if not result["risk_factors"]:
        print("  No significant risk indicators detected.")

    for factor in result["risk_factors"]:
        print(
            f"  +{factor['score']:>2}  "
            f"{factor['description']}"
        )

    print()
    print("Changed files:")

    for file in result["changed_files"]:
        print(f"  - {file}")

    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Assess release risk between two Git revisions."
    )

    parser.add_argument(
        "--base",
        required=True,
        help="Baseline Git revision/tag",
    )

    parser.add_argument(
        "--target",
        required=True,
        help="Target Git revision/tag/commit",
    )

    parser.add_argument(
        "--branch",
        default="main",
        help="Release branch name",
    )

    parser.add_argument(
        "--output",
        default="release-risk-report.json",
        help="JSON output file",
    )

    args = parser.parse_args()

    result = assess_release(
        args.base,
        args.target,
        args.branch,
    )

    print_report(result)

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    print(f"JSON report written to: {args.output}")


if __name__ == "__main__":
    main()
