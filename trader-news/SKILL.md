---
name: trader-news
description: >-
  News Monitor (NSE edition). Tracks breaking news on every NSE stock you
  watch and flags what moves it: Yahoo Finance headlines per ticker (.NS
  feeds) and how far each stock is from yesterday's close. Shows only what is
  new since the last check, newest first, in India time (IST), tags each item
  (earnings, analyst, deal, capital, halt, regulatory/SEBI, macro/RBI...)
  and never repeats one. Use when the user says "any news on RELIANCE", "why
  is this moving", "what's the news on my watchlist", "morning briefing",
  "pre-market news", "monitor the news", "did anything break", or after
  /trader-scanner finds setups.
argument-hint: "[tickers]"
---

# trader-news

A chart can look perfect and still be about to gap on a results date, a SEBI
order or a block deal. Before a setup becomes a trade, this skill reads the
headlines for every stock on the watchlist and tells you only what is new.
It also prints how far each stock has moved today, so a headline and a move
sit side by side.

Tool in this folder (standard library Python, no keys):

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py"                         # watchlist + plan + portfolio
python3 "${CLAUDE_SKILL_DIR}/news.py" --tickers RELIANCE HDFCBANK --hours 12
python3 "${CLAUDE_SKILL_DIR}/news.py" --tickers TCS --all --json
```

## What it reads and writes

| file / feed | what |
| --- | --- |
| `--tickers`, else `trader/watchlist.json` | the scanner's hits (trader-scanner) |
| `trader/plan.json` | the trade you are planning (trader-exit) |
| `trader/portfolio.json` | what you hold (trader-broker records paper fills there) |
| Yahoo Finance headline RSS | `https://feeds.finance.yahoo.com/rss/2.0/headline?s=RELIANCE.NS&region=IN&lang=en-IN` |
| Yahoo Finance chart endpoint | the last price against yesterday's close (unofficial, can lag) |
| `trader/state/news.json` | what has been shown (kept 30 days) |

Company announcements (results, board meetings, dividends, bonus, splits,
QIPs) are filed on nseindia.com and bseindia.com, not in this feed. For a
stock with results or a board meeting coming up, tell the user to check the
exchange's corporate announcements page; Claude can also look it up with web
search.

## The rules

- **Headlines are leads, not facts.** Before telling the user something
  happened, open the story and read it. Quote the source and link it. Never
  summarise a paywalled story you could not read: say so.
- **Exchange filings beat headlines.** If a headline and the company's
  NSE/BSE announcement disagree, the announcement is what the company said.
- **Say what it touches.** Every item lists the tickers it touches and its
  tags: earnings, analyst, legal, deal, capital (dividend, buyback, bonus,
  split, QIP, rights, OFS, block deal), people, risk, halt, regulatory (SEBI,
  USFDA, CCI, TRAI), macro (RBI, MPC, repo rate, CPI, GDP, Budget, FII/FPI).
- **MOVING** marks a stock 3 % or more from yesterday's close (`--move-pct`).
  A move with no headline is worth saying out loud too.
- **No predictions.** Report what was published and how far the price is from
  yesterday's close. Never say what the stock will do next.

## Steps

1. Run the check: `python3 "${CLAUDE_SKILL_DIR}/news.py"`. Exit code 1 means
   nothing new. `--all` shows items already seen, `--json` gives everything
   machine readable, `--dry-run` leaves the state alone.
2. Read the items that matter: anything tagged earnings, halt, legal,
   regulatory or risk, and every MOVING ticker first.
3. Write a short brief, per ticker: what happened, the source and link, the
   move, and one line on why it matters to the setup (for example "results
   are this week: an overnight gap can jump past any stop").
4. If a story changes the picture, say so before `/trader-entry` and
   `/trader-exit`: a results date, a halt, a block deal, an F&O ban. Never
   act on a headline alone.

During the session: `/loop 15m /trader-news`, or a scheduled task each
morning before 9:15 IST.

## Example

`news.py --tickers RELIANCE` reads Yahoo Finance's RELIANCE.NS headline feed
and the price line. A headline like "RBI holds repo rate; Reliance gains" is
tagged macro; "SEBI order on block deal" is tagged regulatory and capital.
The price line reads like `RELIANCE 1159.80 -0.65% vs yesterday's close
1167.40`. Results, board meetings and corporate actions are filed on
nseindia.com and bseindia.com; this tool does not read those, so tell the
user to check there before a results day. When a ticker has no news, say so
rather than padding the brief.

## What it never does

- Never invents or embellishes a story, a quote or a number.
- Never trades on news, and never tells the user to buy or sell because of a
  headline.
- Never hammers a server: one request per feed per ticker, a pause between
  calls,.

## Safety

Education and tooling, not financial advice. This skill only reads and
reports. This edition is paper trading only: `/trader-broker` records a paper
trade after `/trader-risk` passes and the user types an explicit yes.
