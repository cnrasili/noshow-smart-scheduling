"""Delete outdated branches: each person keeps only their most recently updated branch.

Owner of a branch is the GitHub user (or email) of its latest commit. Branches in KEEP and
branches of EXEMPT_LOGINS are never touched. Unmerged work is saved as an archive tag first.
"""

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

API = "https://api.github.com"
KEEP = {"main"}


@dataclass(frozen=True)
class Branch:
    name: str
    sha: str
    owner: str
    updated: datetime


def call(method: str, path: str, body: dict | None = None) -> object:
    request = urllib.request.Request(
        f"{API}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "branch-cleanup"},
    )
    token = os.getenv("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:
        raw = response.read()
    return json.loads(raw) if raw else None


def list_branches(repo: str) -> list[Branch]:
    branches = []
    page = 1
    while True:
        batch = call("GET", f"/repos/{repo}/branches?per_page=100&page={page}")
        if not batch:
            return branches
        for item in batch:
            if item["name"] in KEEP:
                continue
            commit = call("GET", f"/repos/{repo}/commits/{item['commit']['sha']}")
            author = commit.get("author") or {}
            owner = author.get("login") or commit["commit"]["author"]["email"].lower()
            updated = datetime.fromisoformat(commit["commit"]["committer"]["date"])
            branches.append(Branch(item["name"], item["commit"]["sha"], owner, updated))
        page += 1


def select_outdated(branches: list[Branch], exempt: set[str]) -> list[Branch]:
    """Every branch except the most recently updated one of each owner."""
    latest: dict[str, Branch] = {}
    for branch in branches:
        if branch.owner in exempt:
            continue
        current = latest.get(branch.owner)
        if current is None or branch.updated > current.updated:
            latest[branch.owner] = branch
    keep = {branch.name for branch in latest.values()}
    return [b for b in branches if b.owner not in exempt and b.name not in keep]


def is_merged(repo: str, branch: Branch) -> bool:
    compare = call("GET", f"/repos/{repo}/compare/main...{branch.sha}")
    return compare["ahead_by"] == 0


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    exempt = {login for login in os.getenv("EXEMPT_LOGINS", "").split(",") if login}

    branches = list_branches(repo)
    for branch in sorted(branches, key=lambda b: (b.owner, b.updated)):
        print(f"{branch.owner:24} {branch.updated:%Y-%m-%d %H:%M}  {branch.name}")

    outdated = select_outdated(branches, exempt)
    if not outdated:
        print("No outdated branches.")
        return

    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M")
    for branch in outdated:
        merged = is_merged(repo, branch)
        action = "delete" if merged else f"archive as tag archive/{branch.name}-{stamp}, delete"
        print(f"{'[dry run] ' if dry_run else ''}{branch.name}: {action}")
        if dry_run:
            continue
        if not merged:
            call(
                "POST",
                f"/repos/{repo}/git/refs",
                {"ref": f"refs/tags/archive/{branch.name}-{stamp}", "sha": branch.sha},
            )
        call("DELETE", f"/repos/{repo}/git/refs/heads/{urllib.parse.quote(branch.name)}")


if __name__ == "__main__":
    main()
