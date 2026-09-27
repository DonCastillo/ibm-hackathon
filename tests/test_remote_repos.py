"""
Network tests: clone real public repos covering the edge cases we care about.

    pytest -m network            # everything except the huge repos
    pytest -m slow -s            # huge repos (hundreds/thousands of branches) — minutes each

Commit counts on live repos change over time, so assertions stick to things
that should stay true (e.g. octocat/Hello-World hasn't changed since 2018).
"""

import time

import pytest

from backend.git_extractor import RepoAccessError, extract_commits

pytestmark = pytest.mark.network

HELLO_WORLD = "https://github.com/octocat/Hello-World"


def _assert_well_formed(commits):
    for c in commits:
        assert len(c["hash"]) == 40
        assert c["author"] and c["branch"] and c["timestamp"]
        assert not c["branch"].startswith(("refs/", "origin/"))


# ── Frozen repos: exact expectations ──────────────────────────────────────────

def test_hello_world_all_branches_captured():
    commits = extract_commits(HELLO_WORLD, "2000-01-01")
    _assert_well_formed(commits)
    # The two non-default branches each carry a commit that is not on master
    assert {c["branch"] for c in commits} == {"master", "test", "octocat-patch-1"}
    assert len({c["hash"] for c in commits}) == len(commits), "a commit was returned twice"


def test_git_suffix_url_behaves_the_same():
    plain = {c["hash"] for c in extract_commits(HELLO_WORLD, "2000-01-01")}
    suffixed = {c["hash"] for c in extract_commits(HELLO_WORLD + ".git", "2000-01-01")}
    assert plain == suffixed


@pytest.mark.parametrize("since", ["24 hours ago", "48 hours ago", "7 days ago", "14 days ago", "30 days ago"])
def test_every_preset_range_finds_nothing_in_a_dormant_repo(since):
    assert extract_commits(HELLO_WORLD, since) == []


def test_custom_range_around_known_history():
    commits = extract_commits(HELLO_WORLD, "2011-01-01", "2018-12-31")
    assert commits
    assert all("2011" <= c["timestamp"][:4] <= "2018" for c in commits)


def test_spoon_knife_is_dormant():
    assert extract_commits("https://github.com/octocat/Spoon-Knife", "30 days ago") == []


# ── Live repos: shape and sanity ──────────────────────────────────────────────

@pytest.mark.parametrize("repo, since", [
    ("https://github.com/fastapi/fastapi", "30 days ago"),
    ("https://github.com/expressjs/express", "30 days ago"),
])
def test_active_repo_has_recent_commits(repo, since):
    commits = extract_commits(repo, since)
    assert commits, f"expected recent activity in {repo}"
    _assert_well_formed(commits)
    assert len({c["hash"] for c in commits}) == len(commits)


@pytest.mark.parametrize("repo", [
    "https://github.com/pallets/flask",
    "https://github.com/sindresorhus/awesome",
])
def test_quiet_repo_does_not_error(repo):
    _assert_well_formed(extract_commits(repo, "7 days ago"))


# ── Access errors ──────────────────────────────────────────────────────────────

def test_nonexistent_repo_reads_as_private():
    with pytest.raises(RepoAccessError, match="appears to be private"):
        extract_commits("https://github.com/octocat/does-not-exist-xyz", "7 days ago")


def test_bad_token_gets_token_message():
    with pytest.raises(RepoAccessError, match="Personal Access Token provided"):
        extract_commits("https://github.com/octocat/does-not-exist-xyz", "7 days ago", token="ghp_fake123")


def test_unreachable_host_is_a_plain_error():
    with pytest.raises(RuntimeError) as exc:
        extract_commits("https://notarealhost.example/repo", "7 days ago")
    assert not isinstance(exc.value, RepoAccessError)


def test_ssh_url_clones_or_fails_cleanly():
    """Passes whether or not this machine has a GitHub SSH key — it must just never hang."""
    try:
        commits = extract_commits("git@github.com:octocat/Hello-World.git", "2000-01-01")
    except RepoAccessError as e:
        assert "SSH" in str(e)
    except RuntimeError as e:
        assert "Host key verification failed" in str(e)
    else:
        assert {c["branch"] for c in commits} == {"master", "test", "octocat-patch-1"}


# ── Huge repos: performance of all-branches cloning (opt-in) ──────────────────

@pytest.mark.slow
@pytest.mark.parametrize("repo", [
    "https://github.com/kubernetes/kubernetes",       # ~60 branches, very large history
    "https://gitlab.com/gitlab-org/cli",              # ~460 branches, GitLab host
    "https://github.com/dependabot/dependabot-core",  # ~550 branches, bot-heavy
    "https://github.com/facebook/react",              # ~970 branches
    "https://github.com/microsoft/vscode",            # ~5,300 branches — worst case
])
def test_large_repo_all_branches(repo):
    start = time.monotonic()
    commits = extract_commits(repo, "7 days ago")
    elapsed = time.monotonic() - start
    print(f"\n{repo}: {len(commits)} commits across "
          f"{len({c['branch'] for c in commits})} branches in {elapsed:.0f}s")
    _assert_well_formed(commits)
    assert len({c["hash"] for c in commits}) == len(commits)
