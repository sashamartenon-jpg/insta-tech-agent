"""Minimal client for the Instagram API with Instagram Login (graph.instagram.com).

Stdlib only. Token comes from the IG_ACCESS_TOKEN environment variable.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from common import CONFIG

BASE = f"https://graph.instagram.com/{CONFIG.get('graph_api_version', 'v26.0')}"


class IGError(RuntimeError):
    pass


def token():
    t = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not t:
        raise IGError("IG_ACCESS_TOKEN manquant (secret GitHub non configuré ?)")
    return t


def _request(method, url, params=None, data=None, headers=None):
    params = dict(params or {})
    if "access_token" not in params and not (headers and "Authorization" in headers):
        params["access_token"] = token()
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(full, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise IGError(f"{method} {url} -> HTTP {e.code}: {body[:800]}") from None


def get(path, **params):
    return _request("GET", f"{BASE}/{path.lstrip('/')}", params)


def post(path, **params):
    return _request("POST", f"{BASE}/{path.lstrip('/')}", params, data=b"")


def me():
    return get("me", fields="user_id,username,account_type")


def wait_finished(container_id, timeout=900):
    start = time.time()
    while time.time() - start < timeout:
        st = get(container_id, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise IGError(f"conteneur {container_id} : {st}")
        time.sleep(8)
    raise IGError(f"conteneur {container_id} toujours en traitement après {timeout}s")


def upload_video(upload_uri, path):
    """Resumable upload of a local file to the rupload URI returned by the container."""
    data = open(path, "rb").read()
    headers = {"Authorization": f"OAuth {token()}", "offset": "0",
               "file_size": str(len(data)), "Content-Type": "application/octet-stream"}
    req = urllib.request.Request(upload_uri, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise IGError(f"upload vidéo -> HTTP {e.code}: {e.read().decode(errors='replace')[:800]}") from None


def publish_container(ig_id, creation_id):
    res = post(f"{ig_id}/media_publish", creation_id=creation_id)
    media_id = res["id"]
    info = get(media_id, fields="permalink,timestamp")
    return media_id, info.get("permalink")


def publish_carousel(ig_id, image_urls, caption):
    children = []
    for url in image_urls:
        c = post(f"{ig_id}/media", image_url=url, is_carousel_item="true")
        children.append(c["id"])
    for c in children:
        wait_finished(c, timeout=300)
    parent = post(f"{ig_id}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)
    wait_finished(parent["id"], timeout=300)
    return publish_container(ig_id, parent["id"])


def publish_reel(ig_id, video_path, caption, cover_url=None):
    params = {"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true"}
    if cover_url:
        params["cover_url"] = cover_url
    c = post(f"{ig_id}/media", **params)
    upload_video(c["uri"], video_path)
    wait_finished(c["id"])
    return publish_container(ig_id, c["id"])
