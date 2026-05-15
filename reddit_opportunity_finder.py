from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only before dependencies are installed
    yaml = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
SEEN_PATH = BASE_DIR / "data" / "seen_posts.json"
OUTPUT_DIR = BASE_DIR / "outputs"
REDDIT_URL_BASE = "https://www.reddit.com"


@dataclass
class Post:
    id: str
    title: str
    selftext: str
    subreddit: str
    permalink: str
    created_utc: float
    score: int
    num_comments: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize(text: str) -> str:
    text = text.lower().replace("'", "")
    return re.sub(r"\s+", " ", text).strip()


def compact_text(text: str, max_chars: int = 700) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def require_yaml() -> None:
    if yaml is None:
        print(
            "Missing dependency: PyYAML. Install dependencies first:\n"
            "  pip install -r requirements.txt\n"
            "Demo and live runs both need config.yaml parsing."
        )
        raise SystemExit(1)


def load_config() -> dict[str, Any]:
    require_yaml()
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_seen() -> dict[str, dict[str, Any]]:
    if not SEEN_PATH.exists():
        return {}
    try:
        raw = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = SEEN_PATH.with_suffix(f".broken-{utc_now().strftime('%Y%m%d%H%M%S')}.json")
        SEEN_PATH.replace(backup)
        print(f"Warning: invalid seen_posts.json moved to {backup}")
        return {}

    if isinstance(raw, dict) and "posts" in raw:
        raw = raw["posts"]
    if not isinstance(raw, list):
        return {}

    seen: dict[str, dict[str, Any]] = {}
    for item in raw:
        if isinstance(item, dict) and item.get("post_id"):
            seen[item["post_id"]] = item
    return seen


def save_seen(seen: dict[str, dict[str, Any]]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(seen.values(), key=lambda item: item.get("first_seen_at", ""))
    SEEN_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_seen(seen: dict[str, dict[str, Any]], posts: list[Post]) -> None:
    now_iso = utc_now().isoformat()
    for post in posts:
        existing = seen.get(post.id)
        record = {
            "post_id": post.id,
            "first_seen_at": existing.get("first_seen_at", now_iso) if existing else now_iso,
            "last_processed_at": now_iso,
            "title": compact_text(post.title, 220),
            "permalink": post.permalink,
        }
        seen[post.id] = record


def post_url(post: Post) -> str:
    if post.permalink.startswith("http"):
        return post.permalink
    return REDDIT_URL_BASE + post.permalink


def age_hours(post: Post) -> float:
    return max(0.0, (utc_now().timestamp() - post.created_utc) / 3600)


def text_blob(post: Post) -> str:
    return normalize(f"{post.title} {compact_text(post.selftext, 1200)}")


def contains_any(text: str, phrases: list[str]) -> bool:
    return any(normalize(phrase) in text for phrase in phrases)


def matched_keyword_groups(post: Post, keyword_groups: dict[str, list[str]]) -> list[str]:
    blob = text_blob(post)
    matches = []
    for group, phrases in keyword_groups.items():
        if contains_any(blob, phrases):
            matches.append(group)
    return matches


def has_question_intent(blob: str) -> bool:
    question_terms = [
        "?",
        "advice",
        "help",
        "recommend",
        "suggest",
        "reasonable",
        "possible",
        "too rushed",
        "worth it",
        "how do i",
        "what should",
        "first time",
        "is this",
        "can i",
    ]
    return any(term in blob for term in question_terms)


def is_photo_or_news_low_value(post: Post) -> bool:
    blob = text_blob(post)
    title = normalize(post.title)
    body_short = len(compact_text(post.selftext, 300)) < 80
    photo_terms = ["photo", "photos", "pic", "pics", "picture", "pictures", "shot from", "view of"]
    news_terms = ["breaking", "article:", "report:", "news:"]
    if body_short and any(term in title for term in photo_terms):
        return True
    if any(term in title for term in news_terms) and not has_question_intent(blob):
        return True
    return False


def classify_post(post: Post, groups: list[str]) -> str:
    blob = text_blob(post)

    itinerary_terms = [
        "itinerary",
        "route",
        "days",
        "beijing",
        "shanghai",
        "xian",
        "xi an",
        "xi'an",
        "chengdu",
        "suzhou",
        "hangzhou",
        "too rushed",
        "first time",
        "trip plan",
    ]
    payment_terms = [
        "alipay",
        "wechat pay",
        "foreign card",
        "payment",
        "esim",
        "sim card",
        "vpn",
        "google maps",
        "apps",
    ]
    transport_terms = [
        "high speed rail",
        "high-speed rail",
        "train station",
        "12306",
        "trip.com train",
        "hongqiao",
        "beijing south",
        "xian north",
        "xi'an north",
        "chengdu east",
    ]
    hotel_terms = [
        "hotel",
        "check in",
        "check-in",
        "airport to hotel",
        "chinese address",
        "taxi",
    ]
    entry_terms = ["visa-free", "visa free", "240 hour", "240-hour", "transit", "entry", "arrival card"]
    prep_terms = ["prepare", "before arrival", "packing", "onebag", "backpacking", "first china trip"]

    city_terms = ["beijing", "shanghai", "xian", "xi an", "xi'an", "chengdu", "suzhou", "hangzhou"]
    city_hits = sum(1 for term in city_terms if term in blob)
    explicit_itinerary_terms = ["itinerary", "route", "trip plan", "too rushed", "first time"]
    has_day_count = bool(re.search(r"\b\d+\s*-?\s*days?\b", blob))
    itinerary_intent = (
        contains_any(blob, explicit_itinerary_terms)
        or (has_day_count and city_hits >= 2)
        or contains_any(blob, ["beijing xian shanghai", "beijing xi an shanghai", "beijing xian shanghai"])
    )

    if itinerary_intent:
        return "Itinerary Review"
    if "payment_apps" in groups or contains_any(blob, payment_terms):
        return "Payment / Apps"
    if "transport" in groups or contains_any(blob, transport_terms):
        return "Transport"
    if "hotel_arrival" in groups or contains_any(blob, hotel_terms):
        return "Hotel / Arrival"
    if "entry" in groups or contains_any(blob, entry_terms):
        return "Entry / Visa"
    if contains_any(blob, prep_terms) or has_question_intent(blob):
        return "Travel Prep"
    return "Low Value / Skip"


def pain_point(post: Post, category: str) -> str:
    blob = text_blob(post)
    if category == "Itinerary Review":
        if "too rushed" in blob or "rushed" in blob:
            return "Route may be too rushed for a first China trip."
        if "first time" in blob:
            return "First-time China itinerary needs pacing and transfer sanity checks."
        return "User is asking for route or itinerary validation."
    if category == "Payment / Apps":
        return "User may be unsure about payment, maps, SIM/eSIM, VPN, or app setup before arrival."
    if category == "Transport":
        return "User needs practical train station, booking, or transfer guidance."
    if category == "Entry / Visa":
        return "User needs cautious entry or transit guidance with official-rule caveats."
    if category == "Hotel / Arrival":
        return "User may need arrival logistics, hotel check-in, address, or taxi guidance."
    if category == "Travel Prep":
        return "User is asking a general China trip preparation question."
    return "Low intent or weak fit for a helpful reply."


def detected_topic(post: Post, category: str) -> str:
    topic = pain_point(post, category)
    return topic.replace("User ", "").replace("Route ", "Route ")


def score_post(post: Post, category: str, groups: list[str], config: dict[str, Any]) -> dict[str, Any]:
    rules = config["scoring_rules"]
    blob = text_blob(post)
    comments = post.num_comments

    relevance_score = min(30, 8 + 8 * len(groups))
    if category == "Itinerary Review":
        relevance_score = max(relevance_score, 26)
    elif category in {"Payment / Apps", "Transport", "Entry / Visa", "Hotel / Arrival"}:
        relevance_score = max(relevance_score, 22)
    elif category == "Travel Prep":
        relevance_score = max(relevance_score, 15)
    elif category == "Low Value / Skip":
        relevance_score = min(relevance_score, 8)

    pain_terms = ["confused", "worried", "stuck", "help", "advice", "too rushed", "first time", "possible", "?"]
    pain_point_score = min(20, 6 + sum(3 for term in pain_terms if term in blob))

    research_fit_map = {
        "Itinerary Review": 20,
        "Payment / Apps": 16,
        "Transport": 16,
        "Hotel / Arrival": 15,
        "Entry / Visa": 12,
        "Travel Prep": 12,
        "Low Value / Skip": 3,
    }
    research_fit_score = research_fit_map.get(category, 3)

    if comments <= rules["preferred_comment_max"]:
        discussion_window_score = 10
    elif comments <= rules["comment_soft_max"]:
        discussion_window_score = 7
    elif comments < 200:
        discussion_window_score = 4
    else:
        discussion_window_score = 1

    hours_old = age_hours(post)
    if hours_old <= 24:
        discussion_window_score = min(10, discussion_window_score + 1)
    elif hours_old > rules["default_hours"]:
        discussion_window_score = max(1, discussion_window_score - 2)

    risk_score = 10
    if category == "Entry / Visa":
        risk_score = 7
    if any(term in blob for term in ["legal", "overstay", "denied entry", "passport", "embassy"]):
        risk_score = min(risk_score, 5)
    if comments >= 200:
        risk_score = min(risk_score, 6)

    topic_clarity_score = 4
    if category == "Itinerary Review" and any(term in blob for term in ["review", "check", "too rushed", "reasonable", "help"]):
        topic_clarity_score = 10
    elif category in {"Payment / Apps", "Travel Prep"} and any(
        term in blob for term in ["checklist", "prepare", "setup", "what apps", "before arrival"]
    ):
        topic_clarity_score = 8
    elif category in {"Payment / Apps", "Transport", "Hotel / Arrival"}:
        topic_clarity_score = 6
    elif category == "Entry / Visa":
        topic_clarity_score = 3

    total = min(
        100,
        relevance_score
        + pain_point_score
        + research_fit_score
        + discussion_window_score
        + risk_score
        + topic_clarity_score,
    )

    return {
        "relevance_score": relevance_score,
        "pain_point_score": pain_point_score,
        "research_fit_score": research_fit_score,
        "discussion_window_score": discussion_window_score,
        "risk_score": risk_score,
        "topic_clarity_score": topic_clarity_score,
        "research_score": int(total),
    }


def risk_level(risk_score: int) -> str:
    if risk_score >= 8:
        return "Low"
    if risk_score >= 6:
        return "Medium"
    return "High"


def why_research(post: Post, category: str, scores: dict[str, Any]) -> str:
    if scores["research_score"] >= 80:
        return "Specific travel-planning intent, clear topic fit, and recent enough to be useful for topic monitoring."
    if category in {"Payment / Apps", "Transport", "Hotel / Arrival"}:
        return "Concrete operational question that may reveal recurring planning friction."
    if category == "Entry / Visa":
        return "Useful only as a research signal because official-source verification is required."
    return "Moderate relevance for topic monitoring; review manually before keeping."


def manual_review_notes(post: Post, category: str, scores: dict[str, Any]) -> str:
    return (
        f"{why_research(post, category, scores)} "
        f"Score parts: relevance {scores['relevance_score']}, pain {scores['pain_point_score']}, "
        f"fit {scores['research_fit_score']}, discussion window {scores['discussion_window_score']}, "
        f"safety {scores['risk_score']}, topic clarity {scores['topic_clarity_score']}."
    )


def risk_notes(post: Post, category: str, scores: dict[str, Any]) -> str:
    notes = [f"Risk level: {risk_level(scores['risk_score'])}."]
    if category == "Entry / Visa":
        notes.append("Entry and transit topics require official-source verification.")
    if post.num_comments >= 200:
        notes.append("High comment count may indicate a noisy or high-conflict thread.")
    if scores["risk_score"] <= 5:
        notes.append("Manual review should discard this item if it touches legal, political, or sensitive personal issues.")
    return " ".join(notes)


def analyze_posts(
    posts: list[Post],
    config: dict[str, Any],
    hours: int,
    top: int,
    include_seen: bool,
    seen: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[Post]]:
    rules = config["scoring_rules"]
    keyword_groups = config["keyword_groups"]
    exclude_keywords = config["exclude_keywords"]

    rows: list[dict[str, Any]] = []
    processed_posts: list[Post] = []

    for post in posts:
        current_age = age_hours(post)
        if current_age > hours or current_age > rules["max_post_age_hours"]:
            continue

        processed_posts.append(post)

        if post.id in seen and not include_seen:
            continue

        blob = text_blob(post)
        if contains_any(blob, exclude_keywords):
            continue
        if is_photo_or_news_low_value(post):
            continue

        groups = matched_keyword_groups(post, keyword_groups)
        if not groups:
            category_probe = classify_post(post, groups)
            if category_probe == "Low Value / Skip":
                continue
            category = category_probe
        else:
            category = classify_post(post, groups)

        scores = score_post(post, category, groups, config)
        if scores["research_score"] < rules["min_research_score"]:
            continue

        row = {
            "date": utc_now().date().isoformat(),
            "subreddit": post.subreddit,
            "title": post.title,
            "url": post_url(post),
            "created_utc": datetime.fromtimestamp(post.created_utc, timezone.utc).isoformat(),
            "age_hours": round(current_age, 1),
            "reddit_score": post.score,
            "num_comments": post.num_comments,
            "category": category,
            "matched_keyword_group": ", ".join(groups) if groups else "heuristic",
            "research_score": scores["research_score"],
            "detected_topic": detected_topic(post, category),
            "why_this_may_be_useful_for_research": why_research(post, category, scores),
            "manual_review_notes": manual_review_notes(post, category, scores),
            "risk_notes": risk_notes(post, category, scores),
            "status": "pending",
        }
        rows.append(row)

    rows.sort(key=lambda row: (row["research_score"], -row["age_hours"]), reverse=True)
    return rows[:top], processed_posts


def write_markdown(rows: list[dict[str, Any]], output_path: Path) -> None:
    lines: list[str] = []
    title = f"Reddit China Travel Topic Monitor - {utc_now().date().isoformat()}"
    lines.append(title)
    lines.append("=" * len(title))
    lines.append("")
    lines.append("Safety note: read-only research notes. Do not auto-comment, auto-DM, vote, post, or submit links.")
    lines.append("")

    if not rows:
        lines.append("No matching topic-monitoring items found for this run.")
        lines.append("")

    for idx, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"# {idx}. Title: {row['title']}",
                "",
                f"Subreddit: r/{row['subreddit']}",
                f"URL: {row['url']}",
                f"Posted: {row['created_utc']}",
                f"Age: {row['age_hours']} hours",
                f"Reddit score: {row['reddit_score']}",
                f"Comment count: {row['num_comments']}",
                f"Research score: {row['research_score']}",
                f"Category: {row['category']}",
                f"Detected topic: {row['detected_topic']}",
                f"Why this may be useful for research: {row['why_this_may_be_useful_for_research']}",
                f"Manual review notes: {row['manual_review_notes']}",
                f"Risk notes: {row['risk_notes']}",
                f"Status: {row['status']}",
                "",
            ]
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    csv_fields = [
        "date",
        "subreddit",
        "title",
        "url",
        "created_utc",
        "age_hours",
        "reddit_score",
        "num_comments",
        "category",
        "matched_keyword_group",
        "research_score",
        "detected_topic",
        "manual_review_notes",
        "risk_notes",
        "status",
    ]

    export_rows = [{field: row.get(field, "") for field in csv_fields} for row in rows]
    if pd is not None:
        pd.DataFrame(export_rows, columns=csv_fields).to_csv(output_path, index=False)
        return

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(export_rows)


def export_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().date().isoformat()
    markdown_path = OUTPUT_DIR / f"reddit-topic-monitor-{stamp}.md"
    csv_path = OUTPUT_DIR / f"reddit-topic-monitor-{stamp}.csv"
    write_markdown(rows, markdown_path)
    write_csv(rows, csv_path)
    return markdown_path, csv_path


def demo_posts() -> list[Post]:
    now = utc_now().timestamp()
    return [
        Post(
            id="demo_itinerary_001",
            title="First time China itinerary - Beijing, Xi'an, Chengdu and Shanghai in 10 days?",
            selftext="I am planning my first time China trip and wondering if this route is too rushed. Any advice?",
            subreddit="ChinaTravel",
            permalink="/r/ChinaTravel/comments/demo_itinerary_001/",
            created_utc=now - 9 * 3600,
            score=12,
            num_comments=8,
        ),
        Post(
            id="demo_payment_002",
            title="Alipay China setup with foreign card and eSIM before arrival",
            selftext="Do I need WeChat Pay too? Also confused about Google Maps China and VPN for a 14 day China trip.",
            subreddit="travel",
            permalink="/r/travel/comments/demo_payment_002/",
            created_utc=now - 18 * 3600,
            score=23,
            num_comments=27,
        ),
        Post(
            id="demo_train_003",
            title="China high speed rail: Beijing South to Shanghai Hongqiao transfer timing",
            selftext="Using Trip.com China train booking as a foreigner. How early should I arrive at the station?",
            subreddit="ChinaTravel",
            permalink="/r/ChinaTravel/comments/demo_train_003/",
            created_utc=now - 35 * 3600,
            score=18,
            num_comments=42,
        ),
        Post(
            id="demo_entry_004",
            title="240 hour China visa free transit question",
            selftext="Trying to understand if my routing qualifies for China transit visa free entry. Any issues I should check?",
            subreddit="solotravel",
            permalink="/r/solotravel/comments/demo_entry_004/",
            created_utc=now - 21 * 3600,
            score=5,
            num_comments=12,
        ),
        Post(
            id="demo_skip_005",
            title="China politics news article discussion",
            selftext="News link and geopolitical argument.",
            subreddit="travel",
            permalink="/r/travel/comments/demo_skip_005/",
            created_utc=now - 4 * 3600,
            score=101,
            num_comments=250,
        ),
    ]


def fetch_reddit_posts(config: dict[str, Any], limit: int) -> list[Post]:
    if load_dotenv is not None:
        load_dotenv(BASE_DIR / ".env")

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    if not client_id or not client_secret or not user_agent:
        print(
            "Reddit credentials are not configured. Create .env from .env.example, or run demo mode:\n"
            "  copy .env.example .env\n"
            "  python reddit_opportunity_finder.py --demo"
        )
        raise SystemExit(0)

    try:
        import praw
    except ImportError:
        print("Missing dependency: praw. Install dependencies first:\n  pip install -r requirements.txt")
        raise SystemExit(1)

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        check_for_async=False,
    )

    posts: list[Post] = []
    for subreddit_name in config["subreddits"]:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            for submission in subreddit.new(limit=limit):
                posts.append(
                    Post(
                        id=str(submission.id),
                        title=str(submission.title or ""),
                        selftext=compact_text(str(getattr(submission, "selftext", "") or ""), 1200),
                        subreddit=str(subreddit_name),
                        permalink=str(submission.permalink or ""),
                        created_utc=float(submission.created_utc),
                        score=int(submission.score or 0),
                        num_comments=int(submission.num_comments or 0),
                    )
                )
        except Exception as exc:  # PRAW exceptions vary by auth/network state.
            print(f"Warning: could not read r/{subreddit_name}: {exc}")
    return posts


def parse_args(config: dict[str, Any]) -> argparse.Namespace:
    rules = config["scoring_rules"]
    parser = argparse.ArgumentParser(description="Monitor public Reddit China travel topics for private read-only research.")
    parser.add_argument("--hours", type=int, default=rules["default_hours"], help="Only include posts newer than this many hours.")
    parser.add_argument("--limit", type=int, default=80, help="Posts to read from each subreddit via subreddit.new().")
    parser.add_argument("--top", type=int, default=rules["top_results"], help="Maximum number of topic-monitoring items to export.")
    parser.add_argument("--include-seen", action="store_true", help="Include posts already recorded in data/seen_posts.json.")
    parser.add_argument("--dry-run", action="store_true", help="Generate outputs but do not update seen_posts.json.")
    parser.add_argument("--demo", action="store_true", help="Use built-in sample posts and do not call Reddit.")
    return parser.parse_args()


def main() -> int:
    config = load_config()
    args = parse_args(config)

    seen = load_seen()
    posts = demo_posts() if args.demo else fetch_reddit_posts(config, args.limit)
    rows, processed_posts = analyze_posts(
        posts=posts,
        config=config,
        hours=args.hours,
        top=args.top,
        include_seen=args.include_seen,
        seen=seen,
    )

    markdown_path, csv_path = export_outputs(rows)

    if not args.dry_run and not args.demo:
        update_seen(seen, processed_posts)
        save_seen(seen)

    mode = "demo" if args.demo else "live"
    print(f"Mode: {mode}")
    print(f"Fetched posts: {len(posts)}")
    print(f"Exported topic-monitoring items: {len(rows)}")
    print(f"Markdown: {markdown_path}")
    print(f"CSV: {csv_path}")
    if args.demo:
        print("Demo mode did not update data/seen_posts.json.")
    elif args.dry_run:
        print("Dry run did not update data/seen_posts.json.")
    else:
        print(f"Updated seen posts: {SEEN_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)
