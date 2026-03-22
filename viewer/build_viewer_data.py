#!/usr/bin/env python3

import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
VIEWER_DIR = ROOT / "viewer"
DOWNLOADS_DIR = VIEWER_DIR / "downloads"
MANIFEST_PATH = DOWNLOADS_DIR / "index.json"
LIKED_MEDIA_DIR = DOWNLOADS_DIR / "liked_media"
PROFILE_IMAGES_DIR = DOWNLOADS_DIR / "profile_images"
MANAGED_DIR = DOWNLOADS_DIR / "managed"
MANAGED_RAW_DATA_DIR = MANAGED_DIR / "raw_data"
MANAGED_LIKED_MEDIA_DIR = MANAGED_DIR / "liked_media"
MANAGED_PROFILE_IMAGES_DIR = MANAGED_DIR / "profile_images"

IGNORED_DIRS = {
    ".git",
    ".pytest_cache",
    ".vscode",
    "athena",
    "lambda",
    "lambdas",
    "lambdas copy",
    "layers",
    "local",
    "tmp",
    "twitter-responses",
    "volume",
}


def is_hydrated_tweet(payload):
    return (
        isinstance(payload, dict)
        and "id" in payload
        and "text" in payload
        and "timestamp" in payload
        and isinstance(payload.get("author"), dict)
        and "username" in payload["author"]
    )


def tweet_score(tweet, source_path):
    media = tweet.get("media") or []
    author = tweet.get("author") or {}
    return (
        0 if source_path.parent == DOWNLOADS_DIR else 1,
        sum(1 for item in media if item.get("s3_url")),
        1 if author.get("profile_image_s3") else 0,
        len(media),
        len(tweet.get("mentions") or []),
        len(tweet.get("external_links") or []),
    )


def summarize_tweet(tweet, source_path):
    media = tweet.get("media") or []
    author = tweet.get("author") or {}
    text = " ".join(str(tweet.get("text", "")).split())
    source_kind = tweet.get("_viewer_source_kind")
    if not source_kind:
        source_kind = "managed" if MANAGED_DIR in source_path.parents else "cache"

    return {
        "id": str(tweet["id"]),
        "text": tweet.get("text", ""),
        "text_preview": text[:180] + ("..." if len(text) > 180 else ""),
        "timestamp": tweet.get("timestamp", ""),
        "direct_link": tweet.get("direct_link", ""),
        "author": {
            "id": str(author.get("id", "")),
            "username": author.get("username", ""),
            "display_name": author.get("display_name", author.get("username", "")),
            "verified": bool(author.get("verified", False)),
            "profile_image_s3": author.get("profile_image_s3", ""),
            "profile_image_url": author.get("profile_image_url", ""),
        },
        "media": [
            {
                "alt_text": item.get("alt_text"),
                "media_key": item.get("media_key", ""),
                "type": item.get("type", ""),
                "url": item.get("url", ""),
                "s3_url": item.get("s3_url", ""),
            }
            for item in media
        ],
        "media_count": len(media),
        "has_video": any(item.get("type") == "video" for item in media),
        "json_path": f"downloads/{tweet['id']}.json",
        "source_kind": source_kind,
    }


def media_filename_from_url(url):
    if not url:
        return ""

    parsed = urlparse(url)
    filename = Path(parsed.path).name
    return filename


def infer_profile_image_s3(author):
    author_id = str(author.get("id", "")).strip()
    if not author_id:
        return ""

    for directory, prefix in (
        (PROFILE_IMAGES_DIR, "profile_images"),
        (MANAGED_PROFILE_IMAGES_DIR, "managed/profile_images"),
    ):
        existing = sorted(directory.glob(f"{author_id}-*"))
        if existing:
            return f"{prefix}/{existing[0].name}"

    filename = media_filename_from_url(author.get("profile_image_url", ""))
    if not filename:
        return ""

    return f"managed/profile_images/{author_id}-{filename}"


def infer_media_s3_url(tweet_id, media_item):
    url = media_item.get("url", "")
    filename = media_filename_from_url(url)
    media_key = str(media_item.get("media_key", "")).replace("/", "-")

    for directory, prefix in (
        (LIKED_MEDIA_DIR, "liked_media"),
        (MANAGED_LIKED_MEDIA_DIR, "managed/liked_media"),
    ):
        if filename:
            exact = directory / f"{tweet_id}-{filename}"
            if exact.exists():
                return f"{prefix}/{exact.name}"

            fallback_match = sorted(directory.glob(f"{tweet_id}-*{Path(filename).suffix}"))
            if fallback_match:
                return f"{prefix}/{fallback_match[0].name}"

        if media_key:
            key_match = sorted(directory.glob(f"*{media_key}*"))
            if key_match:
                return f"{prefix}/{key_match[0].name}"

    if filename:
        return f"managed/liked_media/{tweet_id}-{filename}"

    return ""


def normalize_tweet(tweet):
    normalized = json.loads(json.dumps(tweet))
    tweet_id = str(normalized.get("id", ""))
    author = normalized.get("author") or {}
    media = normalized.get("media") or []

    if author and not author.get("profile_image_s3"):
        inferred_profile = infer_profile_image_s3(author)
        if inferred_profile:
            author["profile_image_s3"] = inferred_profile

    for item in media:
        if item.get("s3_url"):
            if "/" not in str(item["s3_url"]):
                item["s3_url"] = f"liked_media/{item['s3_url']}"
            continue

        inferred_media = infer_media_s3_url(tweet_id, item)
        if inferred_media:
            item["s3_url"] = inferred_media

    normalized["author"] = author
    normalized["media"] = media
    return normalized


def discover_hydrated_tweets():
    chosen = {}

    for path in ROOT.rglob("*.json"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue

        if not is_hydrated_tweet(payload):
            continue

        tweet_id = str(payload["id"])
        candidate = {"path": path, "tweet": payload}

        current = chosen.get(tweet_id)
        if current is None or tweet_score(payload, path) > tweet_score(current["tweet"], current["path"]):
            chosen[tweet_id] = candidate

    return chosen


def build_manifest():
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    tweets = discover_hydrated_tweets()
    manifest = []

    for tweet_id, item in tweets.items():
        destination = DOWNLOADS_DIR / f"{tweet_id}.json"
        normalized_tweet = normalize_tweet(item["tweet"])
        normalized_tweet["_viewer_source_kind"] = "managed" if MANAGED_DIR in item["path"].parents else "cache"
        destination.write_text(json.dumps(normalized_tweet, indent=2))

        manifest.append(summarize_tweet(normalized_tweet, item["path"]))

    manifest.sort(key=lambda tweet: (tweet["timestamp"], tweet["id"]), reverse=True)
    MANIFEST_PATH.write_text(json.dumps({"tweets": manifest}, indent=2))

    print(f"Prepared {len(manifest)} tweets for the viewer")


if __name__ == "__main__":
    build_manifest()
