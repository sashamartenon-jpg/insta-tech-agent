#!/usr/bin/env python3
"""Pull per-post metrics into data/insights.json for the Strategist.

Computes the outlier multiple (views / account median views) the ig-audit skill
ranks on. Metrics Instagram refuses for a media type are skipped, not fatal.
"""
import json
import statistics
from datetime import datetime, timezone

import ig_api
from common import ROOT

METRICS = ["views", "reach", "saved", "shares", "likes", "comments", "total_interactions", "follows"]
REEL_EXTRA = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]


def metric(media_id, name):
    try:
        res = ig_api.get(f"{media_id}/insights", metric=name)
        vals = res.get("data", [{}])[0].get("values", [{}])
        return vals[0].get("value")
    except ig_api.IGError:
        return None


def main():
    me = ig_api.me()
    ig_id = me["user_id"]
    media = ig_api.get(f"{ig_id}/media", limit=50,
                       fields="id,caption,media_type,media_product_type,timestamp,permalink")
    rows = []
    for m in media.get("data", []):
        names = METRICS + (REEL_EXTRA if m.get("media_product_type") == "REELS" else [])
        stats = {n: metric(m["id"], n) for n in names}
        rows.append({**m, "caption": (m.get("caption") or "")[:140], "metrics": stats})
    views = [r["metrics"]["views"] for r in rows if isinstance(r["metrics"].get("views"), (int, float))]
    med = statistics.median(views) if views else None
    for r in rows:
        v = r["metrics"].get("views")
        r["outlier_multiple"] = round(v / med, 2) if med and isinstance(v, (int, float)) else None
        reach, shares = r["metrics"].get("reach"), r["metrics"].get("shares")
        r["shares_per_1k_reach"] = round(1000 * shares / reach, 2) if reach and shares is not None else None
    try:
        account = ig_api.get(ig_id, fields="username,followers_count,media_count")
    except ig_api.IGError:
        account = {"username": me.get("username")}
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "account": account,
           "median_views": med, "posts": rows}
    path = ROOT / "data" / "insights.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"{len(rows)} posts, médiane vues = {med}")


if __name__ == "__main__":
    main()
