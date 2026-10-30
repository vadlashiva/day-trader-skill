---
name: trader-alerts
description: >-
  Price Alerts. Rings when a price, a stop or the opening bell hits. Turns
  the trade plan into three alerts in one go (the stop, the target and "flat
  by close" at your flat-by time), plus above / below / stop / target levels,
  percent moves from the previous close, any time of day, and the NSE
  opening bell, each ringing once so you are not spammed. Knows NSE hours
  with the 2026 holidays, works out India time itself, fetches free delayed
  quotes (Yahoo chart JSON, .NS symbols) one ticker at a time, and writes trader/prices.json for sizing and the
  risk check. Use when the user says "alert me when", "tell me if RELIANCE hits",
  "watch my stop", "watch my trade", "remind me to close by 3:15", "is the
  market open", "when does the market open", "get me a price", or right
  after /trader-exit writes a plan.
argument-hint: "[ticker] [price]"
---

# trader-alerts

Price Alerts watches the numbers so the user does not have to stare at a
chart. An alert is information, never an order: when a stop alert rings,
nothing is sold by this skill. With a bracket order the stop-loss and the
take-profit already sit at the broker and do the work; the alerts tell the
user what happened and when it is time to be flat.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/alerts.py" clock                          # NSE open or closed, next open
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --from-plan                # stop, target, flat by close from trader/plan.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --opening-bell
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol RELIANCE --stop 1163.35
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol RELIANCE --target 1185.25
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --at 15:15 --label "flat by close" --before-close
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol KO --pct 3
python3 "${CLAUDE_SKILL_DIR}/alerts.py" check                          # exit 0 = something rang
python3 "${CLAUDE_SKILL_DIR}/alerts.py" quote RELIANCE --write             # -> trader/prices.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" quote --holdings --write       # portfolio + plan tickers
python3 "${CLAUDE_SKILL_DIR}/alerts.py" list
python3 "${CLAUDE_SKILL_DIR}/alerts.py" reset reliance.ns-plan-stop
```

`--now "2026-10-29 15:15"` pins the clock (India time (IST)); `--offline DIR`
reads saved quote files instead of the network.

## What it reads and writes

| file | what |
| --- | --- |
| `trader/plan.json` | the trade from trader-exit, for `add --from-plan` |
| `trader/alerts.json` | the rules (`alerts.example.json` in this folder) |
| `trader/state/alerts.json` | which rules rang and when, so each rings once |
| `trader/prices.json` | the latest quotes, merged in, for trader-budget and trader-risk |
| `trader/portfolio.json` | the tickers held, for `quote --holdings` |

## Rule types

| type | rings when | rings again |
| --- | --- | --- |
| `above` / `target` | price at or above `price` | after `reset`, or on its own if `"rearm": true` and the price fell back |
| `below` / `stop` | price at or below `price` | same |
| `pct_move` | moved `pct` percent from the previous close (or `ref`), optional `direction` up or down | once per day at most |
| `time` | the IST clock passed `at` ("15:15") on a trading day | once per trading day |
| `opening_bell` | the NSE is open | once per trading day |

A rule with `"date"` is watched on that IST date only; `--from-plan`
rules carry the plan's date, so yesterday's stop never rings today.  NSE has no
scheduled half days, so a `time` rule rings at its own time.

## Quotes

- `yahoo` (default): `query2.finance.yahoo.com/v8/finance/chart/<TICKER>.NS`, an
  unofficial free JSON endpoint, one request per ticker, half a second apart.
  On a 429 it waits and tries once more; on a 429 or a 5xx after that it
  tries `query1`. It identifies itself as `day-trader-skill/2.0`.
- `stooq`: a US-only fallback kept from the original pack; it has no NSE
  quotes, so leave the source on `yahoo`.
- Free quotes are unofficial, delayed and can lag. They are fine for alerts
  and for checking a size, not for timing an order. The broker's price is the
  one that fills. Each price in `trader/prices.json` keeps its quote time, and
  trader-risk only uses one under 15 minutes old.
- If Yahoo is down, the user can read the price from their broker app (for
  example Angel One) and Claude writes it into `trader/prices.json` as
  `{"as_of": "...Z", "prices": {"RELIANCE": 1159.80}}`.

## The NSE clock

Regular session 9:15 a.m. to 3:30 p.m. India time (IST, UTC+5:30, no
daylight saving), closed on weekends and on the NSE equity trading holidays
for 2026 (NSE circular): Jan 15, Jan 26, Mar 3 (Holi), Mar 26, Mar 31, Apr 3
(Good Friday), Apr 14, May 1, May 28, Jun 26, Sep 14, Oct 2, Oct 20
(Dussehra), Nov 10 (Diwali Balipratipada), Nov 24, Dec 25. Muhurat trading
(Diwali, Sunday 8 Nov 2026) is a special evening session the tool does not
model. For 2027 it says the holiday list is unknown until NSE's circular is
added.

## Steps

1. Right after trader-exit writes the plan, run `add --from-plan`. Confirm
   the three alerts back to the user: the stop, the target and the flat-by time.
2. Run `check` while the trade is open: every few minutes from a Claude
   scheduled task or `/loop`. Each run fetches only the tickers in today's
   rules and rings each alert once. A check reads the latest delayed quote;
   it is not a live feed, and a price can pass a level between two checks.
3. Tell the user what rang in one line each. A stop or target alert means the
   bracket order has probably filled: check `get_open_position` and record the
   fill with trader-broker. "Flat by close" means close anything still open:
   trader-broker `flatten`, then trader-risk, then the user's yes. Never act
   for them.

## Example: RELIANCE, Thursday 29 October 2026

Entry 1,174.30 at 9:40 AM, stop 1,163.35, target 1,185.25, flat by 15:15.
`add --from-plan` writes three alerts for that day:

```
Added reliance.ns-plan-stop: ... "type": "stop", "price": 1163.35 ...
Added reliance.ns-plan-target: ... "type": "target", "price": 1185.25 ...
Added reliance.ns-flat-by: ... "type": "time", "at": "15:15", "label": "flat by close" ...
```

`alerts.py clock` at 9:45 that morning: `IST 2026-10-29 09:45 (Thursday): NSE
OPEN, regular session. Today's session: 09:15 to 15:30.` On 20 October
(Dussehra) it says the market is closed for the holiday. `check` rings each
alert once; with `add --opening-bell`, the bell rings at 9:15.

## Rules

- An alert is a fact about a price or the clock. Say it as a fact.
- Never present a quote as live. Free quotes are delayed and unofficial.
- Confirm every new rule back to the user: ticker, type, level, day.

## What it never does

It never places, cancels or changes an order, never claims a quote is
live, and never predicts where a price is going.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- NSE edition: paper trading only. No broker is connected, and nothing in this pack sends an order
  anywhere. trader-broker records a paper trade only when trader-risk passed that exact order today and
  the user typed an explicit yes for that one order in the chat.
- Cash-market stocks and ETFs only: no options, futures, margin, short selling or leverage.
- If a real broker (for example Angel One SmartAPI) is ever connected, its keys live in environment
  variables on the user's computer, never in the chat, and every order still needs the user's yes.
