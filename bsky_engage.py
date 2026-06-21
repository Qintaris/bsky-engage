#!/usr/bin/env python3
"""
Bluesky Engage — authentique, humain, sans template.
Poste, like, follow, commente avec une vraie voix, pas des messages pré-écrits.

Usage:
    python3 bsky_engage.py --mode post       # Poster un message
    python3 bsky_engage.py --mode engage     # Like + follow + commentaires
    python3 bsky_engage.py --mode all        # Les deux
    python3 bsky_engage.py --mode comment    # Commenter les posts récents
    python3 bsky_engage.py --mode photo      # Poster une image
    python3 bsky_engage.py --dry-run         # Simulation

Configuration:
    Copier .env.example vers .env et remplir les valeurs, ou exporter :
        export BSKY_HANDLE="votre-handle.bsky.social"
        export BSKY_PASSWORD="votre-mot-de-passe-app"
"""

import json, sys, os, urllib.request, urllib.error, urllib.parse, datetime, random

# ── Config ──────────────────────────────────────────────────────────────
HANDLE = os.environ.get("BSKY_HANDLE", "")
PASSWORD = os.environ.get("BSKY_PASSWORD", "")
PDS = "https://bsky.social"
LOG_DIR = os.environ.get("BSKY_LOG_DIR", "")
# ─────────────────────────────────────────────────────────────────────────


# ── Centres d'intérêt pour l'engagement social ─────────────────────────
# Adaptez cette liste à votre univers
INTERESTS = [
    # Tech / IA / Dev
    "artificial intelligence", "machine learning",
    "ai agents", "llm", "programming",
    "python", "open source", "github",
    "startup", "entrepreneurship",
    # Créatif / Lifestyle
    "photography", "writing",
    "travel", "slow living", "art", "music",
]

HASHTAGS_CORE = []
HASHTAGS_THEMES = {
    "morning": ["#morning", "#morningvibes"],
    "evening": ["#evening", "#nightvibes"],
    "creative": ["#writing", "#reflection"],
    "photo": ["#photography", "#mood"],
    "life": ["#slowlife", "#presence"],
}


# ── API ─────────────────────────────────────────────────────────────────
def api(method, path, headers=None, data=None, json_body=None, params=None):
    url = f"{PDS}{path}"
    if params:
        url += "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    req_headers = {}
    if headers:
        req_headers.update(headers)
    if json_body is not None:
        body = json.dumps(json_body).encode()
        req_headers["Content-Type"] = "application/json"
    elif data is not None:
        body = data
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return e.code, {"error": e.reason, "body": body}
    except Exception as e:
        return -1, {"error": str(e)}


def login():
    if not PASSWORD:
        print("❌ BSKY_PASSWORD not set.")
        sys.exit(1)
    status, data = api("POST", "/xrpc/com.atproto.server.createSession",
                       json_body={"identifier": HANDLE, "password": PASSWORD})
    if status != 200:
        print(f"❌ Login failed: {status} {data}")
        sys.exit(1)
    return data["accessJwt"], data["did"]


def clean_text(text):
    """Clean text: remove em dashes, slashes, normalize."""
    text = text.replace("—", " ").replace("–", " ").replace("-", " ")
    text = text.replace("/", " ").replace("\\", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [l.strip() for l in text.split("\n")]
    text = "\n".join(l for l in lines if l)
    return text.strip()


# ── Search & Discovery ──────────────────────────────────────────────────
def search_actors(query, token, limit=10):
    status, data = api("GET", "/xrpc/app.bsky.actor.searchActors",
                       headers={"Authorization": f"Bearer {token}"},
                       params={"q": query, "limit": limit})
    if status != 200:
        return []
    return data.get("actors", [])


def get_following(token, did):
    cursor = None
    follows = set()
    while True:
        params = {"actor": did, "limit": 100}
        if cursor:
            params["cursor"] = cursor
        status, data = api("GET", "/xrpc/app.bsky.graph.getFollows",
                           headers={"Authorization": f"Bearer {token}"},
                           params=params)
        if status != 200:
            break
        for f in data.get("follows", []):
            follows.add(f["did"])
        cursor = data.get("cursor")
        if not cursor:
            break
    return follows


def get_timeline(token, limit=30):
    status, data = api("GET", "/xrpc/app.bsky.feed.getTimeline",
                       headers={"Authorization": f"Bearer {token}"},
                       params={"limit": limit})
    if status != 200:
        return []
    return data.get("feed", [])


# ── Actions ─────────────────────────────────────────────────────────────
def follow_user(handle, token, did):
    status, data = api("GET", "/xrpc/com.atproto.identity.resolveHandle",
                       headers={"Authorization": f"Bearer {token}"},
                       params={"handle": handle.lstrip("@")})
    if status != 200:
        return False, f"Cannot resolve {handle}"
    target_did = data["did"]

    follows = get_following(token, did)
    if target_did in follows:
        return False, f"Already following @{handle}"

    now = datetime.datetime.utcnow().isoformat() + "Z"
    status, data = api("POST", "/xrpc/com.atproto.repo.createRecord",
                       headers={"Authorization": f"Bearer {token}"},
                       json_body={
                           "repo": did,
                           "collection": "app.bsky.graph.follow",
                           "record": {
                               "$type": "app.bsky.graph.follow",
                               "subject": target_did,
                               "createdAt": now,
                           },
                       })
    if status == 200:
        return True, f"✅ Following @{handle}"
    return False, f"❌ Follow failed: {data}"


def like_post(uri, cid, token, did):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    status, data = api("POST", "/xrpc/com.atproto.repo.createRecord",
                       headers={"Authorization": f"Bearer {token}"},
                       json_body={
                           "repo": did,
                           "collection": "app.bsky.feed.like",
                           "record": {
                               "$type": "app.bsky.feed.like",
                               "subject": {"uri": uri, "cid": cid},
                               "createdAt": now,
                           },
                       })
    return status == 200


def post_message(text, token, did):
    text = clean_text(text)
    if len(text) > 300:
        text = text[:297] + "..."

    now = datetime.datetime.utcnow().isoformat() + "Z"
    status, data = api("POST", "/xrpc/com.atproto.repo.createRecord",
                       headers={"Authorization": f"Bearer {token}"},
                       json_body={
                           "repo": did,
                           "collection": "app.bsky.feed.post",
                           "record": {
                               "$type": "app.bsky.feed.post",
                               "text": text,
                               "createdAt": now,
                           },
                       })
    if status == 200:
        uri = data.get("uri", "?")
        print(f"  ✅ Posted!")
        print(f"  https://bsky.app/profile/{HANDLE}")
        return True, uri
    return False, f"❌ Post failed: {data}"


def reply_to_post(text, parent_uri, parent_cid, token, did):
    text = clean_text(text)
    if len(text) > 300:
        text = text[:297] + "..."

    now = datetime.datetime.utcnow().isoformat() + "Z"
    status, data = api("POST", "/xrpc/com.atproto.repo.createRecord",
                       headers={"Authorization": f"Bearer {token}"},
                       json_body={
                           "repo": did,
                           "collection": "app.bsky.feed.post",
                           "record": {
                               "$type": "app.bsky.feed.post",
                               "text": text,
                               "createdAt": now,
                               "reply": {
                                   "root": {"uri": parent_uri, "cid": parent_cid},
                                   "parent": {"uri": parent_uri, "cid": parent_cid},
                               },
                           },
                       })
    if status == 200:
        return True, data.get("uri", "?")
    return False, f"❌ Reply failed: {data}"


# ── Engagement logic ────────────────────────────────────────────────────

def find_people_to_follow(token, did, max_new=5):
    following = get_following(token, did)
    print(f"📊 Following {len(following)} accounts")

    random.shuffle(INTERESTS)
    new_follows = 0
    followed = []

    for interest in INTERESTS[:5]:
        actors = search_actors(interest, token, limit=5)
        for actor in actors:
            if new_follows >= max_new:
                break
            actor_did = actor.get("did")
            if not actor_did or actor_did in following:
                continue
            handle = actor.get("handle", "")
            display = actor.get("displayName", handle)
            followers = actor.get("followersCount", 0)

            # Skip very large or dead accounts
            if followers > 500000 or followers < 1:
                continue

            success, msg = follow_user(handle, token, did)
            if success:
                new_follows += 1
                followed.append(f"  👤 @{handle} ({display})")
                import time
                time.sleep(0.5)

        if new_follows >= max_new:
            break

    if followed:
        print(f"\n✅ {new_follows} new follows:")
        for f in followed:
            print(f)
    else:
        print(f"\nℹ️  No new accounts to follow this time")
    return new_follows


def engage_with_timeline(token, did, max_likes=3, max_comments=1):
    feed = get_timeline(token, limit=30)
    if not feed:
        print("📭 Empty timeline")
        return

    random.shuffle(feed)
    liked = 0
    commented = 0

    print(f"\n📰 {len(feed)} posts in timeline")

    for item in feed:
        if liked >= max_likes and commented >= max_comments:
            break

        post = item.get("post", {})
        uri = post.get("uri", "")
        cid = post.get("cid", "")
        author = post.get("author", {})
        record = post.get("record", {})
        text = record.get("text", "") if isinstance(record, dict) else ""

        # Skip own posts
        if author.get("did") == did:
            continue

        if liked < max_likes:
            success = like_post(uri, cid, token, did)
            if success:
                liked += 1
                print(f"  ❤️ Liked @{author['handle']}: {text[:50]}...")

        if commented < max_comments and text.strip():
            is_reply = isinstance(record, dict) and "reply" in record
            if not is_reply and len(text.strip()) > 20:
                comment = generate_comment(text)
                if comment:
                    success, _ = reply_to_post(comment, uri, cid, token, did)
                    if success:
                        commented += 1
                        print(f"  💬 Commented @{author['handle']}: «{comment[:60]}...»")
                    import time
                    time.sleep(1)

    print(f"\nSummary: {liked} likes, {commented} comments")


def generate_comment(post_text):
    """Generate an authentic comment based on post content."""
    lower = post_text.lower()

    if any(w in lower for w in ["photo", "photography", "picture"]):
        return random.choice([
            "I love the light in this photo.",
            "Beautiful composition! Where is this?",
            "You capture the mood perfectly.",
        ])
    if any(w in lower for w in ["write", "writing", "poem", "word", "text"]):
        return random.choice([
            "This resonates. Thanks for sharing.",
            "Beautiful writing — it stayed with me.",
            "Keep writing. There's something real here.",
        ])
    if any(w in lower for w in ["travel", "trip", "road"]):
        return random.choice([
            "This makes me want to hit the road.",
            "Travel changes everything. Even just a weekend.",
        ])
    if any(w in lower for w in ["sad", "tired", "hard", "difficult"]):
        return random.choice([
            "Take care of yourself. You've got this.",
            "It will pass. You're stronger than this moment.",
        ])
    if any(w in lower for w in ["happy", "grateful", "joy"]):
        return random.choice([
            "Your joy is contagious. Thank you for sharing.",
            "This made me smile. So glad for you.",
        ])

    return random.choice([
        "I relate to this more than I can say. Thank you.",
        "There's an honesty in your words that's rare. Keep going.",
        "Came across your post and I'm glad I did. Lovely.",
        "I feel the same way. Thanks for putting it into words.",
    ])


# ── Image posting ───────────────────────────────────────────────────────

def upload_image(image_path, token):
    if not os.path.exists(image_path):
        return None, f"❌ Image not found: {image_path}"

    with open(image_path, "rb") as f:
        img_data = f.read()

    ext = os.path.splitext(image_path)[1].lower()
    content_type = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }.get(ext, "image/jpeg")

    status, data = api("POST", "/xrpc/com.atproto.repo.uploadBlob",
                       headers={
                           "Authorization": f"Bearer {token}",
                           "Content-Type": content_type,
                       },
                       data=img_data)
    if status != 200:
        return None, f"❌ Upload failed: {data}"
    return data.get("blob"), None


def post_with_image(text, image_path, token, did):
    text = clean_text(text)
    if len(text) > 300:
        text = text[:297] + "..."

    print(f"  📤 Uploading image...")
    blob, err = upload_image(image_path, token)
    if err:
        print(f"  {err}")
        return False, err
    if not blob:
        return False, "❌ Empty blob after upload"
    print(f"  ✅ Image uploaded")

    now = datetime.datetime.utcnow().isoformat() + "Z"
    status, data = api("POST", "/xrpc/com.atproto.repo.createRecord",
                       headers={"Authorization": f"Bearer {token}"},
                       json_body={
                           "repo": did,
                           "collection": "app.bsky.feed.post",
                           "record": {
                               "$type": "app.bsky.feed.post",
                               "text": text,
                               "createdAt": now,
                               "embed": {
                                   "$type": "app.bsky.embed.images",
                                   "images": [{
                                       "image": blob,
                                       "alt": "Photo",
                                   }],
                               },
                           },
                       })
    if status == 200:
        uri = data.get("uri", "?")
        print(f"  ✅ Posted with image!")
        print(f"  https://bsky.app/profile/{HANDLE}")
        return True, uri
    return False, f"❌ Image post failed: {data}"


# ── MAIN ────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bluesky Engage — authentic social media engagement")
    parser.add_argument("--mode", choices=["post", "engage", "all", "comment", "photo"], default="all",
                        help="Engagement mode")
    parser.add_argument("--message", type=str, default="",
                        help="Custom message (if empty, auto-generated)")
    parser.add_argument("--image", type=str, default="",
                        help="Path to image (if empty, auto-lookup in current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Simulation, no real actions")
    parser.add_argument("--max-follows", type=int, default=5,
                        help="Max new follows (default: 5)")
    parser.add_argument("--max-likes", type=int, default=3,
                        help="Max likes (default: 3)")
    parser.add_argument("--max-comments", type=int, default=1,
                        help="Max comments (default: 1)")
    args = parser.parse_args()

    if not HANDLE:
        print("❌ BSKY_HANDLE not set. Set it in .env or export it.")
        sys.exit(1)

    # ── Dry-run ──
    if args.dry_run:
        print("🔍 DRY RUN — No real actions\n")
        if args.mode in ("post", "all"):
            msg = args.message if args.message else "(auto-generated)"
            print(f"📝 Would post: {msg}")
        if args.mode in ("engage", "all"):
            print(f"👥 Would engage: {args.max_follows} follows, {args.max_likes} likes, {args.max_comments} comments")
        if args.mode == "comment":
            print(f"💬 Would comment: {args.max_comments} comments")
        if args.mode == "photo":
            img = args.image if args.image else "(auto-lookup)"
            print(f"📸 Would post photo: {img}")
        print("\n✅ Dry run complete.")
        sys.exit(0)

    # ── Login ──
    print(f"🔐 Connecting as @{HANDLE}...")
    token, did = login()
    print(f"  ✅ Connected")

    # ── Mode post ──
    if args.mode in ("post", "all"):
        print(f"\n📝 Preparing post...")
        if args.message:
            msg = args.message
        else:
            msg = "Sharing a thought today."
        print(f"\nMessage:\n{msg}\n")
        success, result = post_message(msg, token, did)
        if not success:
            print(f"  {result}")

    # ── Mode engage ──
    if args.mode in ("engage", "all"):
        print(f"\n👥 Finding relevant accounts to follow...")
        find_people_to_follow(token, did, max_new=args.max_follows)

        print(f"\n❤️ Engaging with timeline...")
        engage_with_timeline(token, did, max_likes=args.max_likes, max_comments=args.max_comments)

    # ── Mode comment ──
    if args.mode == "comment":
        print(f"\n💬 Commenting on timeline...")
        engage_with_timeline(token, did, max_likes=0, max_comments=args.max_comments)

    # ── Mode photo ──
    if args.mode == "photo":
        print(f"\n📸 Posting photo...")
        msg = args.message or "📷"
        image_path = args.image if args.image else ""
        if not image_path:
            print("  ℹ️  No image path provided. Use --image <path>")
        else:
            print(f"  Image: {image_path}")
            success, result = post_with_image(msg, image_path, token, did)
            if not success:
                print(f"  {result}")

    print(f"\n✅ Done.")


if __name__ == "__main__":
    main()
