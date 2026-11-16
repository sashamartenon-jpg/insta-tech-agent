#!/usr/bin/env python3
"""Hard checks on every post in content/queue before it can be rendered or published.

Exit 1 if any post has an ERROR. WARN lines are reported but do not block.
Writes content/queue/<post>/validation.json for the PR summary.
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from common import CONFIG, ROOT, load_post, queue_dirs

SK = ROOT / ".claude" / "skills"
sys.path.insert(0, str(SK / "ig-reel"))
sys.path.insert(0, str(SK / "ig-human"))
import hookscore  # noqa: E402

GATES = CONFIG["quality_gates"]
HASHTAG_RE = re.compile(r"(?:^|\s)(#[\wÀ-ÿ]+)")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def slots():
    return {(s["day"], s["time"]) for s in CONFIG["weekly_slots"]}


def check(post_dir):
    errs, warns = [], []
    try:
        p = load_post(post_dir)
    except Exception as e:
        return {"errors": [f"post.json illisible : {e}"], "warnings": []}
    for key in ("id", "type", "publish_at", "topic", "hook", "caption", "sources"):
        if not p.get(key):
            errs.append(f"champ manquant : {key}")
    if p.get("type") not in ("carousel", "reel"):
        errs.append("type doit être carousel ou reel")
    # schedule
    try:
        when = datetime.fromisoformat(p["publish_at"])
        if when.tzinfo is None:
            errs.append("publish_at doit avoir un fuseau (ex. -05:00)")
        elif (DAYS[when.weekday()], when.strftime("%H:%M")) not in slots():
            warns.append(f"publish_at {p['publish_at']} ne correspond à aucun créneau de config.json")
    except Exception:
        errs.append("publish_at invalide (ISO 8601 attendu)")
    # sources
    for s in p.get("sources", []):
        if not str(s.get("url", "")).startswith("http"):
            errs.append(f"source sans URL : {s}")
    # verification gate
    v = p.get("verification", {})
    if v.get("verdict") != "pass":
        errs.append(f"vérification non passée (verdict = {v.get('verdict', 'absent')})")
    # caption
    cap = p.get("caption", "")
    if len(cap) > 2200:
        errs.append(f"légende trop longue : {len(cap)}/2200")
    tags = HASHTAG_RE.findall(cap)
    if len(tags) > GATES["max_hashtags"]:
        errs.append(f"{len(tags)} hashtags, maximum {GATES['max_hashtags']}")
    first = cap.split("\n", 1)[0]
    if len(first) > 125:
        warns.append(f"1re ligne de légende = {len(first)} car., coupée à 125 dans le fil")
    if "{{" in cap or "{{" in json.dumps(p, ensure_ascii=False):
        errs.append("placeholder {{...}} non rempli")
    if "—" in json.dumps(p, ensure_ascii=False):
        warns.append("tiret cadratin présent : passe le texte dans humanize.py")
    # hook
    _, score, verdict, flags = hookscore.run(p.get("hook", ""))
    if score < GATES["min_hook_score"]:
        errs.append(f"accroche {score:.0f} < {GATES['min_hook_score']} ({verdict})")
    for f in flags:
        errs.append(f"accroche : {f}")
    # format specific
    if p.get("type") == "carousel":
        slides = p.get("carousel", {}).get("slides", [])
        n = len(slides)
        if not (GATES["carousel_min_slides"] <= n <= GATES["carousel_max_slides"]):
            errs.append(f"{n} slides (attendu {GATES['carousel_min_slides']}-{GATES['carousel_max_slides']})")
        if slides and slides[0].get("kind") != "cover":
            errs.append("la 1re slide doit être kind=cover")
        if slides and slides[-1].get("kind") != "cta":
            errs.append("la dernière slide doit être kind=cta")
        for i, s in enumerate(slides, 1):
            if s.get("kind") not in ("cover", "text", "list", "code", "stat", "cta"):
                errs.append(f"slide {i} : kind inconnu {s.get('kind')}")
            if len(s.get("body", "").split()) > 40:
                warns.append(f"slide {i} : {len(s['body'].split())} mots, vise 25 max")
    if p.get("type") == "reel":
        beats = p.get("reel", {}).get("beats", [])
        if len(beats) < 3:
            errs.append("au moins 3 beats")
        words = sum(len(b.get("voice", "").split()) for b in beats)
        est = words / 2.75
        if est > GATES["reel_max_seconds"]:
            errs.append(f"~{est:.0f} s de voix estimés, max {GATES['reel_max_seconds']} s")
        for i, b in enumerate(beats, 1):
            if not b.get("voice") or not b.get("screen"):
                errs.append(f"beat {i} : voice et screen requis")
            if len(b.get("screen", "").split()) > 8 and b.get("kind") != "code":
                warns.append(f"beat {i} : texte écran > 8 mots")
            if len(b.get("voice", "").split()) / 2.75 > 6:
                warns.append(f"beat {i} : >6 s sur un seul plan, découpe-le")
        if beats and beats[0].get("role") != "hook":
            errs.append("le 1er beat doit avoir role=hook")
    return {"errors": errs, "warnings": warns, "hook_score": round(score, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*", help="post dirs (default: all of content/queue)")
    args = ap.parse_args()
    dirs = [Path(d) for d in args.dirs] or queue_dirs()
    bad = 0
    for d in dirs:
        r = check(d)
        (d / "validation.json").write_text(json.dumps(r, ensure_ascii=False, indent=2))
        status = "ERREUR" if r["errors"] else "OK"
        print(f"[{status}] {d.name}  (accroche {r.get('hook_score', '?')})")
        for e in r["errors"]:
            print(f"    ERREUR  {e}")
        for w in r["warnings"]:
            print(f"    WARN    {w}")
        bad += bool(r["errors"])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
