# Today at COP31: automated briefing

`tools/briefing.py` builds `data/briefing.json`, the automated layer of the Hoje na COP31 page: links to public
reporting and analysis that the monitoring agents already collected from registry sources into `data/feed.json`.
It fetches nothing and writes no analysis of its own. Human-approved original contributions (`data/today.json`) keep
their own approval gate and appear separately on the page under "Da comunidade".

## What each story carries

Original headline (posts: the account and the start of the post), canonical URL, publisher, author when known, the
publisher's date (never the discovery time), language, tracks, content type (reporting, analysis, position, official
statement, document), a short description (the monitor's summary of that source, cut to about 300 characters) with its
machine translations labelled as such, the collection timestamp, and the other reports grouped under the same event.

## Selection

- Candidates: publisher date within the last 72 hours; https links to a single article or post (profile pages,
  listing pages and plain http are dropped); sources currently active in the registry. Social posts only from
  official accounts, ENB and CAN, with tracks; recorded YouTube side events stay in Pulso social.
- Same event: reports sharing enough distinctive words within two days are grouped; the best-scored one leads and
  the others appear as "Também cobriram".
- Ranking: source (the editor's priority publishers first, then registry priority), timeliness, type (articles and
  official texts above posts), relevance to negotiations and implementation, independent coverage of the same event,
  and novelty against the last seven days of top stories. Top stories (at most 8) favour different voices; the
  presidency's accounts count as one. No quotas per section.
- Sections: Leitura essencial, Negociações, Ação e implementação, Sociedade civil em foco. Empty sections are hidden.

## Freshness and failure

The hourly sync rebuilds the briefing after merging the feed. A new edition is validated and written atomically; any
error keeps the previous edition. If the agents' latest rounds are older than 12 hours the edition is flagged stale and
the page says so instead of presenting a quiet day. The page shows the last update time, story and source counts, and
the priority publishers whose access is currently limited.

## Known limits

- Links are checked for form, not fetched again: each one is the URL an agent read when collecting the item.
- Coverage depends on the agents' access. Sites whose robots.txt disallows Anthropic's agents (for example ENB and
  ECCO) are not fetched; ENB is followed through its Bluesky account, and email-only newsletters are not linked.
- Descriptions are summaries written by the monitor, attributed to each source; headlines are not translated.
