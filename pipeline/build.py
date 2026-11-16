#!/usr/bin/env python3
"""Validate and render every post in content/queue whose media is missing or stale.

A post is stale when post.json is newer (by content hash) than its last render,
recorded in .render_hash. Run by the drafts workflow; safe to run locally.
"""
import hashlib
import json
import sys
from pathlib import Path

from common import load_post, queue_dirs
import render_carousel
import render_reel
import validate


def digest(post_dir):
    return hashlib.sha256((post_dir / "post.json").read_bytes()).hexdigest()


def main():
    failed = 0
    for d in queue_dirs():
        r = validate.check(d)
        (d / "validation.json").write_text(json.dumps(r, ensure_ascii=False, indent=2))
        if r["errors"]:
            print(f"[ERREUR] {d.name}: " + "; ".join(r["errors"]))
            failed += 1
            continue
        stamp = d / ".render_hash"
        h = digest(d)
        if stamp.exists() and stamp.read_text().strip() == h:
            print(f"[à jour] {d.name}")
            continue
        post = load_post(d)
        if post["type"] == "carousel":
            render_carousel.render(d)
        else:
            render_reel.render(d)
        stamp.write_text(h)
        print(f"[rendu]  {d.name}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
