"""
fetch_videos.py
Runs in GitHub Actions. Reads all playlists from your YouTube channel,
fetches videos from each, and writes videos.json.

Categories are driven entirely by your YouTube playlist names.
Add a playlist  → new category appears on the site.
Delete playlist → category disappears from the site.
"""

import os, json, requests

API_KEY    = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]

BASE = "https://www.googleapis.com/youtube/v3"

# ── Emoji map: playlist name keyword → icon ─────────────────────────────────
# Add more as you create new playlists. Case-insensitive match.
EMOJI_MAP = {
    "tech":        "💻",
    "religious":   "🕌",
    "comedy":      "😄",
    "gaming":      "🎮",
    "informative": "📚",
    "documentary": "🎞️",
    "promotion":   "📣",
    "lifestyle":   "✨",
    "motion":      "🎨",
    "longform":    "🎬",
    "long-form":   "🎬",
    "long form":   "🎬",
    "music":       "🎵",
    "motivation":  "🔥",
    "cinematic":   "🎥",
    "education":   "🎓",
    "event":       "🎉",
}

def get_emoji(name):
    lower = name.lower()
    for keyword, emoji in EMOJI_MAP.items():
        if keyword in lower:
            return emoji
    return "▶️"

def paginate(url, params):
    """Fetch all pages from a YouTube list endpoint."""
    items = []
    while True:
        r = requests.get(url, params=params).json()
        items.extend(r.get("items", []))
        token = r.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token
    return items

# ── 1. Get all playlists on the channel ──────────────────────────────────────
print("Fetching playlists...")
playlists_raw = paginate(f"{BASE}/playlists", {
    "key":        API_KEY,
    "channelId":  CHANNEL_ID,
    "part":       "snippet",
    "maxResults": 50,
})

categories = []

for pl in playlists_raw:
    pl_id    = pl["id"]
    pl_name  = pl["snippet"]["title"]

    # Skip "Liked videos" or hidden system playlists
    if pl_name.startswith("LL") or pl_name == "Liked videos":
        continue

    print(f"  → Playlist: {pl_name} ({pl_id})")

    # ── 2. Get videos in this playlist ───────────────────────────────────────
    items_raw = paginate(f"{BASE}/playlistItems", {
        "key":        API_KEY,
        "playlistId": pl_id,
        "part":       "snippet,contentDetails",
        "maxResults": 50,
    })

    videos = []
    for item in items_raw:
        snippet  = item["snippet"]
        vid_id   = snippet["resourceId"]["videoId"]
        title    = snippet["title"]
        thumb    = (snippet.get("thumbnails", {})
                           .get("high", {})
                           .get("url", ""))
        desc     = snippet.get("description", "")[:120]
        published = snippet.get("publishedAt", "")[:10]

        videos.append({
            "id":          vid_id,
            "title":       title,
            "description": desc,
            "thumbnail":   thumb,
            "published":   published,
            "embed":       f"https://www.youtube.com/embed/{vid_id}",
            "url":         f"https://www.youtube.com/shorts/{vid_id}",
        })

    if not videos:
        continue   # skip empty playlists

    categories.append({
        "id":       pl_id,
        "name":     pl_name,
        "emoji":    get_emoji(pl_name),
        "slug":     pl_name.lower().replace(" ", "-"),
        "count":    len(videos),
        "videos":   videos,
    })

# ── 3. Write videos.json ─────────────────────────────────────────────────────
output = {
    "updated":    __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d"),
    "categories": categories,
}

with open("videos.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

total = sum(c["count"] for c in categories)
print(f"\n✅ videos.json written — {len(categories)} categories, {total} videos total")
