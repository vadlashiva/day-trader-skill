---
name: trader-scanner
description: >-
  Chart Scanner (NSE edition). Scans the Nifty 50 for setups: opening-range
  breakouts, flags, oversold bounces. Gets the Nifty 50 list from
  niftyindices.com (with a built-in list as fallback), runs a pre-market scan
  of daily closes (20-day closing-high breakout, bull flag, reclaimed the
  20-day average, oversold, oversold bounce) and an intraday opening-range
  breakout scan on 5-minute bars, then writes trader/watchlist.json for
  trader-news and trader-entry. Free Yahoo data (.NS symbols), bar by bar,
  times in IST. Use when the user says "scan the market", "scan Nifty",
  "find me setups", "what is breaking out", "opening range breakouts", "scan
  for bull flags", "oversold stocks", "pre-market scan", "build my
  watchlist", "what should I look at today", or at the start of a trading
  day before /trader-news.
argument-hint: "[universe | daily | orb] [--at HH:MM]"
---

# trader-scanner

The Chart Scanner is the first step of a day trade. It reads the charts of
the 50 Nifty stocks and lists the ones that match a rule. That is all it does.
A scan is a list of charts that match a rule, not a list of stocks to buy,
and a setup on a chart is not a prediction. Most people who day trade lose
money; SEBI's own studies of intraday traders say the same. The scanner does
not change that.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/scan.py" universe                       # Nifty 50 -> trader/universe.txt
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily                          # before the open -> trader/watchlist.json
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily --symbols RELIANCE,HDFCBANK,TCS  # or --watchlist FILE
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb                            # after 9:35 AM IST -> trader/watchlist.json
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --at 10:15                 # cut the clock at 10:15 AM IST
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --watchlist trader/watchlist.json --json
```

Symbols are NSE symbols (RELIANCE, M&M, BAJAJ-AUTO); the tool adds `.NS` for
Yahoo. Flags: `--min-price 5` (rupees) and `--min-volume 0`,
`--or-minutes 15`, `--max-confirm 200` (orb stage 2),
`--now "2026-10-29 10:15"` (IST) to pin the clock, `--offline PATH` to read
saved Yahoo files, `--no-write`, `--show N`, `--json`. Exit code 0 when the
scan found something, 1 when it found nothing or could not run (the reason is
one plain line).

## What it reads and writes

| file | what |
| --- | --- |
| `trader/universe.txt` | written by `universe`: one `SYMBOL\|Name` a line, read by `daily` and `orb`. Without it, the built-in Nifty 50 is used |
| `trader/watchlist.json` | written by `daily` and `orb`: `mode`, `as_of`, `universe`, `scanned`, `failed`, `hits[]`. trader-news and trader-entry read `hits[].symbol` |
| `trader/config.json` | read by `orb`: `no_entries_after` (default 15:00) |

## The universe

`universe` downloads NSE Indices' constituent file
(niftyindices.com/IndexConstituent/ind_nifty50list.csv) and keeps the EQ
series. If the site does not answer, or answers with fewer than 45 rows, it
uses the built-in list: the Nifty 50 after the September 2026 review (BSE in,
Wipro out, effective 30 September 2026). Run it after each index review
(March and September). To scan other stocks, pass `--symbols` or a file with
one NSE symbol a line (`--universe FILE`).

## The daily scan (before the open)

Yahoo's spark endpoint returns closes for 20 symbols a request, so the Nifty
50 takes 3 requests. Run it before 9:15 or after 15:30: during the session
today's daily bar is left out until the close.

The setups are computed from daily closes only (spark has no highs or lows):

| setup | the rule on closes |
| --- | --- |
| `breakout_20d` | the last close is above every close of the 20 sessions before it |
| `bull_flag` | up more than 10 % over the 10 sessions before the last 5, then the last 5 closes inside a 5 % range |
| `reclaim_ma20` | the close before was under its 20-day average, the last close is above it |
| `oversold` | RSI 14 (Wilder) under 30 |
| `oversold_bounce` | RSI 14 was under 30 yesterday and today closed up |

Hits are listed most traded first (price times volume).

## The opening-range breakout scan (during the session)

The opening range is the first `--or-minutes` (15) of the session: the 9:15,
9:20 and 9:25 five-minute bars. A hit is the first completed 5-minute bar to
CLOSE above the range high, at that bar's close time.

1. Stage 1, every symbol: spark closes of today's 5-minute bars, 20 a
   request. A chart goes on only if a completed bar after the range closed at
   or above the highest close of the range (a necessary condition, so no
   breakout is lost).
2. Stage 2, each candidate: the v8 chart with real highs and lows, one
   request each. Range high = the highest high of the range bars, range low =
   the lowest low.

A chart is usable when all its opening-range bars (9:15 onward) are there
and no more than 3 later bars are missing. Yahoo's NSE data leaves an odd
5-minute bar empty in most stocks on most days; a missing bar is skipped,
never read as a breakout, and the scan says how many usable charts had gaps.
A hit with a missing bar between the range and its breakout bar is marked
`[time uncertain: N bars missing before it]`: the breakout is real, but the
first close above may have come up to N bars earlier. Hits without the mark
have exact times. In `--json`, each hit carries `missing_before`.
A chart missing an opening-range bar is skipped (the range cannot be known). Null closes are
dropped, a bar off the 5-minute grid (the live tick) is dropped, and a bar
counts only once it is complete (start + 5 minutes). Before the range is
done, on a weekend or NSE holiday, after the close, or after
`no_entries_after` it prints one plain line and writes nothing.

## Data and limits

- Yahoo's chart and spark endpoints are free, unofficial and can lag. Bars are
  5-minute bars, bar by bar, never tick by tick. query2 first, query1 on a 429
  or 5xx, one retry after a 5-second wait on a 429.
- Partial results are said as partial ("Fetched 48 of 50 charts"). Never
  round a partial scan up to "the whole market".
- NSE trading holidays for 2026 are built in (NSE circular). Add 2027's when
  NSE publishes them (usually December); until then the tools warn that the
  holiday list does not cover the date.

## Steps

1. After each index review: `scan.py universe`.
2. Before the open: `scan.py daily`. Tell the user the counts (fetched,
   scanned, hits) and the top few by setup.
3. After 9:35 AM IST: `scan.py orb`. Tell the user how many usable charts
   broke their range and when, and that a later hit is closer to the price now.
4. The user picks one chart. Hand it on: `/trader-news TICKER` (what is moving
   it), then `/trader-entry TICKER` (the entry bar by bar). Never pick for them.

## Example: RELIANCE, Thursday 29 October 2026

Real Yahoo 5-minute bars (`tests/fixtures/nse/RELIANCE.NS.json`), scan cut at 10:15 AM IST:

```
python3 scan.py orb --offline tests/fixtures/nse --now "2026-10-29 10:15" --no-write
Opening-range breakout scan, Thu 2026-10-29 10:15 AM IST: 15-minute range (9:15 to 9:30 AM), 5-minute bars, Yahoo.
Fetched 1 of 1 charts; 1 usable; 1 candidates, 1 confirmed with real highs and lows.
1 of 1 charts closed above their opening-range high by 10:15 AM:
   9:40 AM  RELIANCE.NS Rs 1,174.30  range 1,156.20 to 1,170.50  +0.32% over
```

The range is the 9:15, 9:20 and 9:25 bars (high 1,170.50, low 1,156.20); the
9:35 bar closed at 1,174.30, 0.32 % over the high, at 9:40 AM. On a live day
the scan runs over all 50 Nifty stocks the same way. The user picks one and
Claude hands it to `/trader-news RELIANCE`, then `/trader-entry RELIANCE`.

## Rules

- Say what was scanned: how many symbols, how many charts came back, how many
  were usable, and the time of the data.
- Say "matched a rule", never "a buy", "a winner" or "a good trade".
- Never print a P&L, a return or a profit figure.
- A hit is stale once the price has moved on. Re-run before acting on it.

## What it never does

It never places, sizes or checks an order, never says which stock to buy,
never calls data real time, and never promises that a setup works.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- NSE edition: paper trading only. No broker is connected, and nothing in this pack sends an order
  anywhere. trader-broker records a paper trade only when trader-risk passed that exact order today and
  the user typed an explicit yes for that one order in the chat.
- Cash-market stocks and ETFs only: no options, futures, margin, short selling or leverage.
- If a real broker (for example Angel One SmartAPI) is ever connected, its keys live in environment
  variables on the user's computer, never in the chat, and every order still needs the user's yes.
