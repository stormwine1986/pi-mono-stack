name: twitter
description: Twitter/X data retrieval tool powered by twitterapi.io. Use to fetch user profiles and latest posts.
role: Tools
---

# Twitter/X Skill (twapi)

This skill allows you to interact with X (formerly Twitter) using the `twapi` CLI tool, which interfaces with `twitterapi.io`.

## Capabilities

- **User Info**: Fetch detailed profile information for any Twitter user.
- **Latest Posts**: Retrieve the most recent tweets/posts from a specific user.
- **Articles**: Fetch the full content of long Twitter articles (Notes) by their tweet ID.
- **Advanced Search**: Search for tweets using keywords, users, and date ranges.

## Usage

This skill is executed via a Docker container. Authentication is handled via the `TWITTERAPI_KEY` environment variable.

### Docker Container

```bash
docker exec twitter twapi <command> [options]
```

### Commands

- `twapi user <username>`: Get user profile information.
- `twapi tweets <username>`: Get a user's latest tweets.
- `twapi article <tweet_id>`: Get the full content of a long article.
- `twapi search "<query>"`: Perform advanced search (wrap query in quotes).

### Output Format (Tweets)

When fetching tweets, the tool returns a JSON object with a `tweets` array. Each tweet contains:
- `id`: The unique ID of the tweet.
- `text`: The content of the tweet.
- `type`: The type of post (e.g., tweet, retweet).
- `url`: Direct link to the post.
- `createdAt`: Timestamp of the post.

## Examples

**User:** "Show me info about @elonmusk"
**Action:**
```bash
docker exec twitter twapi user elonmusk
```

**User:** "What was the latest tweet from @vitalikbuterin?"
**Action:**
```bash
docker exec twitter twapi tweets vitalikbuterin
```

**User:** "Read the content of this long article (ID: 1905545699552375179)"
**Action:**
```bash
docker exec twitter twapi article 1905545699552375179
```

**User:** "Find tweets from @elonmusk on January 1, 2024"
**Action:**
```bash
docker exec twitter twapi search "from:elonmusk since:2024-01-01 until:2024-01-02"
```

**User:** "检索特定用户在某一天的推文 (例如检索 2024-02-20 当天)"
**Action:**
```bash
# 格式：since:起始日期 until:起始日的后一天
docker exec twitter twapi search "from:username since:2024-02-20 until:2024-02-21"
```
