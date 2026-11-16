#!/usr/bin/env python3
"""Write the Pull Request description: one section per queued post, with previews.

Usage: pr_body.py <owner/repo> <commit-sha>  > body.md
Images use raw.githubusercontent.com URLs at that commit (repo must be public).
"""
import json
import sys
from datetime import datetime

from common import ROOT, load_post, queue_dirs

repo, sha = sys.argv[1], sys.argv[2]
raw = f"https://raw.githubusercontent.com/{repo}/{sha}"
blob = f"https://github.com/{repo}/blob/{sha}"
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

out = ["## Lot à valider",
       "",
       "**Fusionner cette PR = approuver la publication** de tous les posts ci-dessous, "
       "chacun à son heure. Pour retirer un post : supprime son dossier dans la PR, "
       "ou demande à Claude de le réécrire. Ne rien faire = rien n'est publié.",
       ""]
for d in queue_dirs():
    p = load_post(d)
    rel = d.relative_to(ROOT).as_posix()
    when = datetime.fromisoformat(p["publish_at"])
    val = json.loads((d / "validation.json").read_text()) if (d / "validation.json").exists() else {}
    status = "❌ bloqué" if val.get("errors") else "✅ prêt"
    out += [f"---", f"### {JOURS[when.weekday()].capitalize()} {when:%d/%m %H:%M} · {p['type']} · {status}",
            f"**Accroche** ({val.get('hook_score', '?')}/100) : {p['hook']}", ""]
    if p["type"] == "carousel" and (d / "slides").exists():
        imgs = sorted((d / "slides").glob("*.jpg"))
        out.append(" ".join(f'<img src="{raw}/{rel}/slides/{i.name}" width="180">' for i in imgs))
    if p["type"] == "reel":
        if (d / "cover.jpg").exists():
            out.append(f'<img src="{raw}/{rel}/cover.jpg" width="200">')
        if (d / "reel.mp4").exists():
            meta = json.loads((d / "render.json").read_text()) if (d / "render.json").exists() else {}
            warn = " ⚠️ voix de secours" if meta.get("engine") and meta["engine"] != ["piper"] else ""
            out.append(f"\n▶️ [Voir le reel ({meta.get('seconds', '?')} s)]({blob}/{rel}/reel.mp4?raw=true){warn}")
        out.append("\n<details><summary>Script</summary>\n")
        for b in p["reel"]["beats"]:
            out.append(f"- **{b['screen'].replace('**', '')}** : {b['voice']}")
        out.append("\n</details>")
    out += ["", "<details><summary>Légende</summary>\n", "```", p["caption"], "```", "</details>", ""]
    out.append("**Sources** : " + " · ".join(f"[{s['title']}]({s['url']})" for s in p["sources"]))
    notes = p.get("verification", {}).get("notes", [])
    if notes:
        out.append("\n<details><summary>Vérification</summary>\n")
        out += [f"- {n}" for n in notes]
        out.append("\n</details>")
    for e in val.get("errors", []):
        out.append(f"- ❌ {e}")
    for w in val.get("warnings", []):
        out.append(f"- ⚠️ {w}")
    out.append("")
print("\n".join(out))
