import csv
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
CONFIG = yaml.safe_load((ROOT / "config" / "channel.yaml").read_text(encoding="utf-8"))

def clamp(n, low=0, high=100):
    return max(low, min(high, n))

def score_video(video, keyword_list, cutoff):
    stats = video.get("statistics", {})
    snippet = video.get("snippet", {})
    title = snippet.get("title", "")
    description = snippet.get("description", "")
    text = f"{title} {description}".lower()
    views = int(stats.get("viewCount", 0) or 0)
    published = snippet.get("publishedAt", "")
    try:
        pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        age_days = max(0, (datetime.now(timezone.utc) - pub_dt).days)
    except Exception:
        age_days = 999

    # Transparent heuristics; tune only after observing your own channel data.
    demand = clamp(int(min(25, (views + 1).bit_length() * 2.3)))
    freshness = clamp(int(20 * max(0, 1 - age_days / max(cutoff, 1))))
    fit_hits = sum(1 for kw in keyword_list if kw.lower() in text)
    fit = clamp(int(min(20, fit_hits * 4)))
    competition = 15 if views < 100_000 else (10 if views < 1_000_000 else 5)
    specificity = 15 if len(title.split()) >= 5 and any(ch.isdigit() for ch in title) else 10
    feasibility = 5 if title.strip() and views >= 100 else 2
    total = demand + freshness + fit + competition + specificity + feasibility
    return {
        "score": min(100, total),
        "title": title,
        "channel_title": snippet.get("channelTitle", ""),
        "published_at": published,
        "age_days": age_days,
        "view_count": views,
        "video_id": video.get("id", {}).get("videoId", ""),
        "url": "https://www.youtube.com/watch?v=" + video.get("id", {}).get("videoId", ""),
        "score_breakdown": {
            "demand_proxy": demand,
            "freshness_proxy": freshness,
            "keyword_fit": fit,
            "competition_proxy": competition,
            "specificity_proxy": specificity,
            "feasibility": feasibility,
        },
        "note": "Heuristic research signal only; not a prediction of virality."
    }

def main():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("Missing YOUTUBE_API_KEY environment variable.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    api = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
    research = CONFIG.get("research", {})
    queries = research.get("search_queries", [])
    max_results = int(research.get("max_results_per_query", 25))
    lookback = int(research.get("lookback_days", 30))
    keywords = research.get("target_topic_keywords", [])
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback)

    seen = set()
    raw = []
    for query in queries:
        response = api.search().list(
            part="snippet", q=query, type="video", order="date",
            maxResults=min(50, max_results),
            publishedAfter=cutoff.isoformat().replace("+00:00", "Z")
        ).execute()
        for item in response.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if vid and vid not in seen:
                seen.add(vid)
                raw.append(item)

    videos = []
    for start in range(0, len(raw), 50):
        ids = [v["id"]["videoId"] for v in raw[start:start+50]]
        if not ids:
            continue
        details = api.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()
        videos.extend(details.get("items", []))

    scored = [score_video(v, keywords, lookback) for v in videos]
    scored.sort(key=lambda x: x["score"], reverse=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel_config": CONFIG.get("channel", {}),
        "candidate_count": len(scored),
        "candidates": scored,
        "disclaimer": "Public search metrics are incomplete proxies. Review originality, source quality, audience fit and rights before production."
    }
    (OUTPUT / "topics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUTPUT / "topics.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["score", "title", "channel_title", "published_at", "age_days", "view_count", "url"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in scored:
            writer.writerow({k: item.get(k, "") for k in fields})
    print(f"Saved {len(scored)} candidates to output/topics.json and output/topics.csv")

if __name__ == "__main__":
    main()
