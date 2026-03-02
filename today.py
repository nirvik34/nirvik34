from dotenv import load_dotenv
load_dotenv()

import os
import json
import time
import requests
from datetime import date
from lxml import etree

TOKEN = os.environ.get("ACCESS_TOKEN")
if not TOKEN:
    raise RuntimeError("ACCESS_TOKEN not set")

USER_NAME = os.environ.get("USER_NAME", "nirvik34")

CACHE_FILE = "cache_daily.json"
API_CALLS = 0

def gql(query, variables):
    global API_CALLS
    API_CALLS += 1
    
    # Using 'token' prefix often works more reliably for classic PATs in GraphQL
    headers = {"Authorization": f"token {TOKEN}"}
    
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=20,
    )
    
    if r.status_code == 401:
        raise RuntimeError(
            "\n[!] GitHub API Error: Bad credentials (401).\n"
            "This usually means your ACCESS_TOKEN is expired or invalid.\n"
            "Verify the secret in your repository settings and ensure it has 'repo' and 'read:user' scopes."
        )
    
    if r.status_code != 200:
        raise RuntimeError(f"GitHub API Error ({r.status_code}): {r.text}")
        
    res = r.json()
    if "errors" in res:
        raise RuntimeError(f"GraphQL Errors: {json.dumps(res['errors'], indent=2)}")
        
    return res["data"]


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    with open(CACHE_FILE, "r") as f:
        data = json.load(f)
    if data.get("date") == str(date.today()):
        return data["stats"]
    return None


def save_cache(stats):
    with open(CACHE_FILE, "w") as f:
        json.dump(
            {"date": str(date.today()), "stats": stats},
            f,
            indent=2,
        )


def fetch_stats(username):
    stars = 0
    cursor = None

    while True:
        q = """
        query($login: String!, $cursor: String) {
          user(login: $login) {
            repositories(
              first: 100,
              after: $cursor,
              ownerAffiliations: OWNER
            ) {
              totalCount
              nodes { stargazerCount }
              pageInfo { hasNextPage endCursor }
            }
            repositoriesContributedTo {
              totalCount
            }
            followers { totalCount }
            following { totalCount }
            contributionsCollection {
              totalCommitContributions
            }
          }
        }
        """
        d = gql(q, {"login": username, "cursor": cursor})["user"]

        for r in d["repositories"]["nodes"]:
            stars += r["stargazerCount"]

        if not d["repositories"]["pageInfo"]["hasNextPage"]:
            break

        cursor = d["repositories"]["pageInfo"]["endCursor"]

    return {
        "repos": d["repositories"]["totalCount"],
        "contrib": d["repositoriesContributedTo"]["totalCount"],
        "followers": d["followers"]["totalCount"],
        "following": d["following"]["totalCount"],
        "commits": d["contributionsCollection"]["totalCommitContributions"],
        "stars": stars,
    }


def safe_svg_update(filename, stats):
    if not os.path.exists(filename):
        return
    tree = etree.parse(filename)
    root = tree.getroot()

    mapping = {
        "commit_data": stats["commits"],
        "star_data": stats["stars"],
        "repo_data": stats["repos"],
        "contrib_data": stats["contrib"],
        "follower_data": stats["followers"],
        "following_data": stats["following"],
    }

    for k, v in mapping.items():
        el = root.find(f".//*[@id='{k}']")
        if el is not None:
            el.text = f"{v:,}"

    tree.write(filename, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    start = time.perf_counter()

    force = os.environ.get("FORCE_UPDATE") == "true"
    stats = load_cache() if not force else None
    
    if not stats:
        print("Fetching fresh stats from GitHub...")
        stats = fetch_stats(USER_NAME)
        save_cache(stats)
    else:
        print("Using cached stats (skipping API calls).")

    safe_svg_update("dark_mode.svg", stats)
    safe_svg_update("light_mode.svg", stats)

    print("API calls:", API_CALLS)
    print("Time:", round(time.perf_counter() - start, 3), "s")
