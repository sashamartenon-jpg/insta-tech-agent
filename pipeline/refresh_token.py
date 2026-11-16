#!/usr/bin/env python3
"""Refresh the long-lived Instagram token (valid 60 days) and print the new one.

The workflow stores the result back into the IG_ACCESS_TOKEN secret when a
GH_PAT secret (fine-grained, "Secrets: read and write" on this repo) exists.
"""
import json
import os
import urllib.parse
import urllib.request

tok = os.environ["IG_ACCESS_TOKEN"].strip()
url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": tok})
with urllib.request.urlopen(url, timeout=60) as r:
    res = json.loads(r.read().decode())
new = res["access_token"]
days = int(res.get("expires_in", 0)) // 86400
out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a") as f:
        f.write(f"changed={'true' if new != tok else 'false'}\n")
        f.write(f"days={days}\n")
# Write the token to a file the next step reads, never to the log.
with open(os.environ.get("TOKEN_OUT", "new_token.txt"), "w") as f:
    f.write(new)
print(f"jeton rafraîchi, valide {days} jours, {'nouveau' if new != tok else 'inchangé'}")
