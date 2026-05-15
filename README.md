# Reddit China Travel Opportunity Finder V1

Local Python tool for finding recent Reddit posts where a careful, manual China travel reply may be useful for the ChinaTripReview / foreigner China trip planning project.

This tool only discovers opportunities, scores posts, and drafts possible English replies. It never comments, sends private messages, votes, creates posts, or submits links to Reddit.

## Safety Boundary

- This is a private local read-only tool.
- It does not automatically comment.
- It does not send messages.
- It does not vote.
- It does not submit links.
- It does not store Reddit usernames or user profiles.
- All Reddit replies must be reviewed and posted manually by a human user.
- `.env` must never be committed.

## What It Does

- Reads recent posts from configured subreddits using the official Reddit API in read-only mode.
- Filters by subreddit, keyword group, age, exclusions, and comment count.
- Classifies posts into itinerary, preparation, payment/app, transport, entry/visa, hotel/arrival, or skip categories.
- Scores each opportunity from 0 to 100.
- Suggests whether a reply is appropriate and whether any CTA should be avoided, soft, checklist-oriented, or service-oriented.
- Generates manual-review English comment drafts with no URLs by default.
- Exports Markdown and CSV files.
- Tracks seen post IDs to avoid repeat processing.

## What It Does Not Do

- No automatic Reddit comments.
- No private messages.
- No upvotes or downvotes.
- No Reddit posts.
- No automatic website links.
- No Reddit username or password.
- No author saving.
- No user profile saving.
- No comment scraping.
- No political debate targeting.

## Install

```cmd
cd /d D:\codex\reddit-china-travel-monitor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

If `python` is not available but the Windows launcher is installed, use `py`:

```powershell
Set-Location D:\codex\reddit-china-travel-monitor
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

## Reddit API App Setup

1. Go to [Reddit app preferences](https://www.reddit.com/prefs/apps).
2. Choose `create another app`.
3. Select `script`.
4. Add a clear app name such as `ChinaTripReviewOpportunityFinder`.
5. Use any valid redirect URI, for example `http://localhost:8080`.
6. Save the app.
7. Copy the app client ID and client secret into `.env`.

Only these fields are required:

```env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=ChinaTripReviewOpportunityFinder/0.1 by your_reddit_username
```

Do not add Reddit username or password. This tool is read-only.

## Run

Demo mode works without Reddit credentials:

```powershell
python reddit_opportunity_finder.py --demo
```

Live read-only mode:

```powershell
python reddit_opportunity_finder.py --hours 72 --limit 80 --top 15
```

Other options:

```powershell
python reddit_opportunity_finder.py --hours 24 --limit 50 --top 10
python reddit_opportunity_finder.py --hours 72 --limit 80 --top 15 --include-seen
python reddit_opportunity_finder.py --hours 72 --limit 80 --top 15 --dry-run
```

## Output Files

Each run writes:

- `outputs/reddit-opportunities-YYYY-MM-DD.md`
- `outputs/reddit-opportunities-YYYY-MM-DD.csv`

The Markdown file is for manual review. The CSV file is for filtering, sorting, or sending selected rows into a second review pass.

`data/seen_posts.json` stores only:

- `post_id`
- `first_seen_at`
- `last_processed_at`
- `title`
- `permalink`

It does not store authors, profiles, comments, or long Reddit bodies.

## Using GPT For A Second Pass

Open the Markdown or CSV output and send a small number of selected rows to GPT with a prompt like:

```text
Review these Reddit reply opportunities. Remove anything that feels promotional, risky, political, legally uncertain, or unlikely to help. Improve the remaining draft replies so they sound natural and do not include links by default.
```

Keep final posting decisions manual. Check the subreddit rules and the actual thread context before replying.

## Configuration

Edit `config.yaml` to change:

- monitored subreddits
- keyword groups
- excluded topics
- scoring thresholds
- internal link recommendations

Internal links are exported as suggestions only. The generated `draft_reply` field intentionally does not include URLs.

## Safety Reminders

- Review every draft manually before using it.
- Do not post links unless the thread clearly asks for a resource and the subreddit allows it.
- Avoid politics, legal disputes, immigration debates, relationship posts, job posts, and old/high-conflict threads.
- Do not treat Reddit replies as visa or legal advice. For entry and transit questions, point users to official sources.
- Clean old files from `outputs/` periodically. Outputs may contain post titles and draft replies, so keep only what you need.
