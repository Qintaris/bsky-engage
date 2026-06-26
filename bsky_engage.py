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

import json, sys, os, urllib.request, urllib.error, urllib.parse, datetime, random, shlex

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
        reason = data.get("error") if isinstance(data, dict) else "unknown error"
        print(f"❌ Login failed: {status} {reason}")
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


# ── Historique pour l'analyse des horaires ──────────────────────────
def get_author_feed(token, did, limit=50):
    """Récupère les posts récents de l'utilisateur."""
    status, data = api("GET", "/xrpc/app.bsky.feed.getAuthorFeed",
                       headers={"Authorization": f"Bearer {token}"},
                       params={"actor": did, "limit": min(limit, 100)})
    if status != 200:
        return []
    return data.get("feed", [])


def get_post_likes_count(token, uri, cid):
    """Compte les likes d'un post."""
    status, data = api("GET", "/xrpc/app.bsky.feed.getLikes",
                       headers={"Authorization": f"Bearer {token}"},
                       params={"uri": uri, "limit": 1})
    if status == 200:
        return data.get("likeCount", 0)
    return 0


def get_post_thread_engagement(token, uri):
    """Compte les réponses à un post."""
    status, data = api("GET", "/xrpc/app.bsky.feed.getPostThread",
                       headers={"Authorization": f"Bearer {token}"},
                       params={"uri": uri, "depth": 1})
    if status != 200:
        return 0
    thread = data.get("thread", {})
    replies = thread.get("replies", [])
    return len(replies)


def analyze_best_times(token, did, max_posts=50):
    """Analyse les horaires de publication pour trouver les meilleurs créneaux."""
    print(f"\n📊 Analyse des horaires de publication...")
    feed = get_author_feed(token, did, limit=max_posts)
    if not feed:
        print("  ❌ Aucun post trouvé. Publie d'abord pour avoir des données.")
        return

    print(f"  📖 {len(feed)} posts récupérés")

    from collections import defaultdict
    hour_data = defaultdict(lambda: {"count": 0, "likes": 0, "replies": 0, "total": 0})

    for item in feed:
        post = item.get("post", {})
        record = post.get("record", {})
        uri = post.get("uri", "")
        cid = post.get("cid", "")
        like_count = post.get("likeCount", 0)
        reply_count = post.get("replyCount", 0)
        repost_count = post.get("repostCount", 0)

        created_at = record.get("createdAt", "")
        if not created_at:
            continue

        try:
            dt = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            hour = dt.hour
        except Exception:
            continue

        # Score d'engagement pondéré
        engagement = like_count + (reply_count * 2) + repost_count

        hour_data[hour]["count"] += 1
        hour_data[hour]["likes"] += like_count
        hour_data[hour]["replies"] += reply_count
        hour_data[hour]["total"] += engagement

        # Si le post a peu de données du feed, on va chercher plus loin
        if like_count == 0 and reply_count == 0:
            extra_likes = get_post_likes_count(token, uri, cid)
            extra_replies = get_post_thread_engagement(token, uri)
            if extra_likes: hour_data[hour]["likes"] += extra_likes
            if extra_replies: hour_data[hour]["replies"] += extra_replies
            hour_data[hour]["total"] += extra_likes + (extra_replies * 2)

    # Calcul des moyennes et classement
    if not hour_data:
        print("  ❌ Impossible d'analyser les données.")
        return

    print(f"\n  {'Heure':<8} {'Posts':<7} {'Likes':<7} {'Replies':<9} {'Eng./post':<11} {'Note':<6}")
    print(f"  {'-'*48}")

    ranked = []
    for hour in sorted(hour_data.keys()):
        d = hour_data[hour]
        eng_per_post = d["total"] / d["count"] if d["count"] > 0 else 0
        ranked.append((hour, eng_per_post, d["count"], d["likes"], d["replies"]))

        h = f"{hour:02d}h"
        bar = "█" * min(int(eng_per_post * 2) + 1, 20)
        note = f"{eng_per_post:.1f}"
        print(f"  {h:<8} {d['count']:<7} {d['likes']:<7} {d['replies']:<9} {note:<11} {bar}")

    # Top 3
    ranked.sort(key=lambda x: x[1], reverse=True)
    top3 = [r for r in ranked if r[2] >= 2][:3]  # besoin d'au moins 2 posts dans ce créneau
    if not top3 and ranked:
        top3 = ranked[:3]  # fallback

    print(f"\n  🏆 Meilleurs créneaux :")
    for i, (hour, score, count, likes, replies) in enumerate(top3, 1):
        print(f"    {i}. {hour:02d}h — {score:.1f} engagement/post ({count} posts, {likes} likes, {replies} replies)")

    # Format utilisable avec --at
    best_hour = top3[0][0] if top3 else None
    if best_hour is not None:
        print(f"\n  💡 Essaye de poster vers {best_hour:02d}h00 pour maximiser l'engagement !")
        print(f"     → python3 bsky_engage.py --mode post --message \"Ton message\" --at \"{best_hour}:00\"")


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


# ── Thread support ──────────────────────────────────────────────────────

def get_last_post_uri(token, did):
    """Get the URI of your most recent post."""
    status, data = api("GET", "/xrpc/com.atproto.repo.listRecords",
                       headers={"Authorization": f"Bearer {token}"},
                       params={"repo": did, "collection": "app.bsky.feed.post", "limit": 1})
    if status != 200:
        return None, None
    records = data.get("records", [])
    if not records:
        return None, None
    r = records[0]
    return r.get("uri"), r.get("cid")


# ── Scheduling ─────────────────────────────────────────────────────────

def schedule_command(cmd, schedule_str):
    """Schedule a shell command using `at` on Linux/macOS."""
    import subprocess, shlex
    try:
        proc = subprocess.run(["which", "at"], capture_output=True, text=True)
        if proc.returncode != 0:
            print("  ⚠️  `at` command not found. Install it: sudo apt install at (Linux) or brew install at (macOS)")
            return False
        # Wrap the Python command
        full_cmd = f"cd {shlex.quote(os.getcwd())} && {cmd}"
        proc = subprocess.run(["at", schedule_str], input=full_cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"  ✅ Scheduled: {schedule_str}")
            print(f"  📋 {proc.stdout.strip()}")
            return True
        else:
            print(f"  ❌ Schedule failed: {proc.stderr.strip()}")
            return False
    except Exception as e:
        print(f"  ❌ Schedule error: {e}")
        return False


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
    parser.add_argument("--thread", action="store_true",
                        help="Reply to your last post (thread mode)")
    parser.add_argument("--reply-to", type=str, default="",
                        help="URI of a post to reply to (e.g. at://did:plc:xxx/app.bsky.feed.post/yyy)")
    parser.add_argument("--stats", action="store_true", default=True,
                        help="Show session stats at the end (default: on)")
    parser.add_argument("--best-time", action="store_true",
                        help="Analyse les horaires de publication pour trouver le meilleur moment")
    parser.add_argument("--best-time-posts", type=int, default=50,
                        help="Nombre de posts à analyser (default: 50)")
    parser.add_argument("--no-stats", action="store_false", dest="stats",
                        help="Hide session stats")
    parser.add_argument("--in", type=str, default="", dest="schedule_in",
                        help="Schedule post in e.g. '5min', '2h', '1day' (uses `at` on Linux)")
    parser.add_argument("--at", type=str, default="", dest="schedule_at",
                        help="Schedule post at e.g. '14:00', 'tomorrow 9am' (uses `at` on Linux)")
    args = parser.parse_args()

    # ── Read message from stdin if available ──
    stdin_msg = ""
    if not args.message and not sys.stdin.isatty():
        try:
            stdin_msg = sys.stdin.read().strip()
        except Exception:
            pass

    msg = args.message or stdin_msg or ""

    # ── Dry-run (before HANDLE check) ──
    if args.dry_run:
        print("🔍 DRY RUN — No real actions\n")
        if args.best_time:
            print(f"📊 Would analyze best posting times (last {args.best_time_posts} posts)")
        else:
            if args.mode in ("post", "all"):
                display = msg if msg else "(auto-generated if empty)"
                print(f"📝 Would post: {display}")
            if args.mode in ("engage", "all"):
                print(f"👥 Would engage: {args.max_follows} follows, {args.max_likes} likes, {args.max_comments} comments")
            if args.mode == "comment":
                print(f"💬 Would comment: {args.max_comments} comments")
            if args.mode == "photo":
                img = args.image if args.image else "(none)"
                print(f"📸 Would post photo: {img}")
            if args.thread:
                print(f"🔗 Thread mode: would reply to last post")
            if args.schedule_in:
                print(f"⏰ Would schedule in: {args.schedule_in}")
            if args.schedule_at:
                print(f"⏰ Would schedule at: {args.schedule_at}")
        print("\n✅ Dry run complete.")
        sys.exit(0)

    if not HANDLE:
        print("❌ BSKY_HANDLE not set. Set it in .env or export it.")
        sys.exit(1)

    # ── Handle scheduling ──
    if args.schedule_in or args.schedule_at:
        schedule_str = args.schedule_in if args.schedule_in else args.schedule_at
        cmd = f"echo {shlex.quote(msg)} | python3 {shlex.quote(os.path.abspath(__file__))} --mode {args.mode}"
        if args.image:
            cmd += f" --image {shlex.quote(args.image)}"
        if args.max_follows != 5:
            cmd += f" --max-follows {args.max_follows}"
        if args.max_likes != 3:
            cmd += f" --max-likes {args.max_likes}"
        if args.max_comments != 1:
            cmd += f" --max-comments {args.max_comments}"
        sched_arg = args.schedule_in if args.schedule_in else args.schedule_at
        schedule_command(cmd, sched_arg)
        return

    # ── Stats tracker ──
    stats = {"posts": 0, "replies": 0, "follows": 0, "likes": 0, "comments": 0}

    # ── Login ──
    print(f"🔐 Connecting as @{HANDLE}...")
    token, did = login()
    print(f"  ✅ Connected")

    # ── Mode best-time (analyse indépendante) ──
    if args.best_time:
        analyze_best_times(token, did, max_posts=args.best_time_posts)
        print(f"\n✅ Done.")
        return

    result = ""  # track last action URI

    # ── Mode post ──
    if args.mode in ("post", "all"):
        print(f"\n📝 Preparing post...")
        if not msg:
            print("  ℹ️  No message provided. Pipe text in: echo 'Hello' | python3 bsky_engage.py --mode post")
            print("  Or use: --message \"Your text\"")
        else:
            # Thread? Reply to last post
            target_uri, target_cid = None, None
            if args.thread:
                target_uri, target_cid = get_last_post_uri(token, did)
                if target_uri:
                    print(f"  🔗 Replying to previous post (thread mode)")
                else:
                    print("  ℹ️  No previous post found, posting fresh")
            if args.reply_to:
                # Resolve reply_to to get CID
                parts = args.reply_to.split("/")
                rkey = parts[-1]
                repo = parts[2] if len(parts) > 2 else did
                status, data = api("GET", "/xrpc/com.atproto.repo.getRecord",
                                   headers={"Authorization": f"Bearer {token}"},
                                   params={"repo": repo, "collection": "app.bsky.feed.post", "rkey": rkey})
                if status == 200:
                    target_uri, target_cid = args.reply_to, data.get("cid")
                    print(f"  🔗 Replying to specified post")
                else:
                    print(f"  ⚠️  Could not resolve --reply-to URI, posting fresh")

            if target_uri and target_cid:
                success, result = reply_to_post(msg, target_uri, target_cid, token, did)
                if success:
                    stats["replies"] += 1
            else:
                print(f"\nMessage:\n{msg}\n")
                success, result = post_message(msg, token, did)
                if success:
                    stats["posts"] += 1

            if not success:
                print(f"  {result}")

    # ── Mode engage ──
    if args.mode in ("engage", "all"):
        print(f"\n👥 Finding relevant accounts to follow...")
        n = find_people_to_follow(token, did, max_new=args.max_follows)
        stats["follows"] += n

        print(f"\n❤️ Engaging with timeline...")
        old_engage = engage_with_timeline
        # Track likes/comments by wrapping the function
        like_count = [0]
        comment_count = [0]
        original_like = like_post
        original_reply = reply_to_post

        def counting_like(uri, cid, tok, d):
            r = original_like(uri, cid, tok, d)
            if r: like_count[0] += 1
            return r

        def counting_reply(text, uri, cid, tok, d):
            r = original_reply(text, uri, cid, tok, d)
            if r and r[0]: comment_count[0] += 1
            return r

        import types
        like_post_ref = globals()["like_post"]
        reply_to_post_ref = globals()["reply_to_post"]
        globals()["like_post"] = counting_like
        globals()["reply_to_post"] = counting_reply

        engage_with_timeline(token, did, max_likes=args.max_likes, max_comments=args.max_comments)

        globals()["like_post"] = like_post_ref
        globals()["reply_to_post"] = reply_to_post_ref
        stats["likes"] += like_count[0]
        stats["comments"] += comment_count[0]

    # ── Mode comment ──
    if args.mode == "comment":
        print(f"\n💬 Commenting on timeline...")
        engage_with_timeline(token, did, max_likes=0, max_comments=args.max_comments)
        # Can't easily track here without wrapping again

    # ── Mode photo ──
    if args.mode == "photo":
        print(f"\n📸 Posting photo...")
        image_path = args.image if args.image else ""
        if not image_path:
            print("  ℹ️  No image path provided. Use --image <path>")
        elif not msg:
            print("  ℹ️  No message. Use --message or pipe text in.")
        else:
            print(f"  Image: {image_path}")
            success, result = post_with_image(msg, image_path, token, did)
            if success:
                stats["posts"] += 1
            if not success:
                print(f"  {result}")

    # ── Recap ──
    if args.stats and any(v > 0 for v in stats.values()):
        print(f"\n📊 Session recap:")
        parts = []
        if stats["posts"]: parts.append(f"📝 {stats['posts']} post(s)")
        if stats["replies"]: parts.append(f"🔗 {stats['replies']} reply/ies in thread")
        if stats["follows"]: parts.append(f"👤 {stats['follows']} new follow(s)")
        if stats["likes"]: parts.append(f"❤️ {stats['likes']} like(s)")
        if stats["comments"]: parts.append(f"💬 {stats['comments']} comment(s)")
        print(f"  {' | '.join(parts)}")
    print(f"\n✅ Done.")

    # ── Save last post URI for potential scheduling ──
    last_uri_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".last_post")
    try:
        if isinstance(result, str) and result:
            with open(last_uri_file, "w") as f:
                f.write(result)
    except Exception:
        pass


if __name__ == "__main__":
    main()
