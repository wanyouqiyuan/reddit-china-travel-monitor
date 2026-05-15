# Reddit China Travel Topic Monitor

Private local read-only topic research tool for monitoring public Reddit discussions about China travel.

This tool is for manual research and topic monitoring only. It reads public Reddit post metadata, classifies broad travel topics, assigns a conservative research score, and exports local Markdown/CSV review files for a human to inspect.

## Safety Boundary

- This is a private local read-only topic research tool.
- It only reads public Reddit post metadata.
- It is for manual research and topic monitoring.
- It does not automatically post, comment, message, vote, submit links, moderate, or interact with users.
- It does not generate automated contact or promotional messaging.
- It does not generate replies by default.
- It does not recommend promotional links by default.
- It does not store Reddit usernames, user profiles, private messages, comment histories, or author information.
- Any Reddit participation must be written, reviewed, and posted manually by a human user.
- `.env` and secrets must never be committed.

## What It Does

- Reads recent public posts from configured subreddits using the official Reddit API in read-only mode.
- Filters by subreddit, keyword group, age, exclusions, and comment count.
- Classifies posts into itinerary, preparation, payment/app, transport, entry/visa, hotel/arrival, or low-fit categories.
- Assigns a `research_score` from 0 to 100 for private review prioritization.
- Exports Markdown and CSV files for manual review notes.
- Tracks seen post IDs locally to avoid repeat processing.

## What It Does Not Do

- No automatic Reddit comments.
- No private messages.
- No upvotes or downvotes.
- No Reddit posts.
- No automatic website links.
- No generated replies by default.
- No Reddit username or password.
- No author saving.
- No user profile saving.
- No private message reading or saving.
- No comment history reading or saving.
- No comment scraping.
- No political debate targeting.

## Install

```cmd
cd /d D:\github-safe\reddit-china-travel-monitor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

If `python` is not available but the Windows launcher is installed, use `py`:

```powershell
Set-Location D:\github-safe\reddit-china-travel-monitor
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

## Reddit API App Setup

1. Go to [Reddit app preferences](https://www.reddit.com/prefs/apps).
2. Choose `create another app`.
3. Select `script`.
4. Add a clear app name such as `ChinaTripReviewTopicMonitor`.
5. Use any valid redirect URI, for example `http://localhost:8080`.
6. Save the app.
7. Copy the app client ID and client secret into `.env`.

Only these fields are required:

```env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=ChinaTripReviewTopicMonitor/0.1 by your_reddit_username
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

- `outputs/reddit-topic-monitor-YYYY-MM-DD.md`
- `outputs/reddit-topic-monitor-YYYY-MM-DD.csv`

The Markdown file is for manual review. The CSV file is for filtering, sorting, or sending selected rows into a second manual research pass.

Markdown entries use these fields:

- Title
- Subreddit
- URL
- Posted
- Age
- Reddit score
- Comment count
- Research score
- Category
- Detected topic
- Why this may be useful for research
- Manual review notes
- Risk notes
- Status

CSV exports use these fields:

- `date`
- `subreddit`
- `title`
- `url`
- `created_utc`
- `age_hours`
- `reddit_score`
- `num_comments`
- `category`
- `matched_keyword_group`
- `research_score`
- `detected_topic`
- `manual_review_notes`
- `risk_notes`
- `status`

Default outputs do not include generated replies, promotional action recommendations, or website link recommendations.

`data/seen_posts.json` stores only:

- `post_id`
- `first_seen_at`
- `last_processed_at`
- `title`
- `permalink`

It does not store authors, profiles, comments, private messages, comment histories, or long Reddit bodies.

## Using GPT For A Second Pass

Open the Markdown or CSV output and send a small number of selected rows to GPT with a prompt like:

```text
Review these Reddit China travel topic-monitoring notes. Remove anything that feels promotional, risky, political, legally uncertain, or outside the stated read-only research purpose. Improve the manual review notes so they are neutral and useful for private topic research.
```

Keep any Reddit participation fully manual. Check the subreddit rules and actual thread context before writing anything on Reddit.

## Configuration

Edit `config.yaml` to change:

- monitored subreddits
- keyword groups
- excluded topics
- scoring thresholds

The default configuration does not include website links. The tool does not insert links into Reddit posts or comments.

## Safety Reminders

- Keep this tool private and local.
- Treat outputs as private manual research notes.
- Do not use the tool to automate Reddit participation.
- Do not post links unless you independently decide to do so manually and the subreddit clearly allows it.
- Avoid politics, legal disputes, immigration debates, relationship posts, job posts, and old/high-conflict threads.
- Do not treat Reddit discussions as visa or legal advice. For entry and transit questions, verify official sources.
- Clean old files from `outputs/` periodically. Outputs may contain public post titles, so keep only what you need.
- Never commit `.env`, secrets, output files, or `data/seen_posts.json`.
