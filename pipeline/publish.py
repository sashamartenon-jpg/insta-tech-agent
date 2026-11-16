#!/usr/bin/env python3
"""Publish every approved post whose publish_at has passed.

Approved = present in content/queue on the main branch (it got there by a merged PR).
On success the folder moves to content/published/ with a published.json receipt.
One post per run at most, so a backlog never floods the account.

  python pipeline/publish.py --due            # what the cron runs
  python pipeline/publish.py --due --dry-run  # show what would go out
  python pipeline/publish.py --check          # verify the token and account
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import ig_api
from common import ROOT, load_post, queue_dirs


def raw_url(path):
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA")
    if not (repo and sha):
        raise SystemExit("GITHUB_REPOSITORY / GITHUB_SHA absents : le publisher tourne dans GitHub Actions")
    return f"https://raw.githubusercontent.com/{repo}/{sha}/{Path(path).relative_to(ROOT).as_posix()}"


def due_posts(now):
    out = []
    for d in queue_dirs():
        p = load_post(d)
        if datetime.fromisoformat(p["publish_at"]) <= now:
            out.append((d, p))
    return sorted(out, key=lambda x: x[1]["publish_at"])


def ready(d, p):
    val = json.loads((d / "validation.json").read_text()) if (d / "validation.json").exists() else None
    if not val or val.get("errors"):
        return "validation absente ou en erreur"
    if p["type"] == "carousel" and not list((d / "slides").glob("*.jpg")):
        return "slides non rendues"
    if p["type"] == "reel" and not (d / "reel.mp4").exists():
        return "reel.mp4 non rendu"
    return None


def publish_one(d, p, ig_id):
    if p["type"] == "carousel":
        urls = [raw_url(f) for f in sorted((d / "slides").glob("*.jpg"))]
        return ig_api.publish_carousel(ig_id, urls, p["caption"])
    cover = raw_url(d / "cover.jpg") if (d / "cover.jpg").exists() else None
    return ig_api.publish_reel(ig_id, d / "reel.mp4", p["caption"], cover)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        info = ig_api.me()
        limit = ig_api.get(f"{info['user_id']}/content_publishing_limit", fields="quota_usage,config")
        print(json.dumps({"account": info, "publishing_limit": limit}, indent=2))
        return

    now = datetime.now(timezone.utc)
    due = due_posts(now)
    if not due:
        print("rien à publier")
        return
    blocked = []
    for d, p in due:
        problem = ready(d, p)
        if not problem:
            break
        blocked.append(f"{d.name} : {problem}")
        print(f"::error::{d.name} échu mais pas prêt : {problem}")
    else:
        sys.exit(1)
    if args.dry_run:
        print(f"publierait {d.name} ({p['type']}, prévu {p['publish_at']})")
        return
    info = ig_api.me()
    media_id, permalink = publish_one(d, p, info["user_id"])
    receipt = {"media_id": media_id, "permalink": permalink,
               "published_at": datetime.now(timezone.utc).isoformat(), "account": info.get("username")}
    (d / "published.json").write_text(json.dumps(receipt, indent=2))
    dest = ROOT / "content" / "published" / d.name
    shutil.move(str(d), str(dest))
    print(f"publié : {d.name} -> {permalink}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"Publié **{d.name}** : {permalink}\n")


if __name__ == "__main__":
    main()
