---
name: trader-broker
description: >-
  Order Executor, NSE edition: PAPER TRADING ONLY. Shows each approved order
  as a plain ticket (a bracket shows its stop-loss, take-profit and the max
  loss at the stop), records the user's yes word for word, then records the
  trade as a simulated paper fill in trader/portfolio.json. No broker is
  connected and nothing is sent anywhere. Builds the sell ticket that closes
  a day trade by the flat-by time (15:15 IST), records fills, and logs each
  trade's max loss so trader-risk can hold the daily limit. Use when the user
  says "place the order", "buy it", "execute", "take the trade", "paper
  trade it", "close my position", "flatten", "get me out", or after
  /trader-risk passes.
argument-hint: "[order number]"
---

# trader-broker

The Order Executor is the last step of a trade. In this NSE edition it is
paper only: no broker is connected, nothing reaches the market, and a
"placed" order is a simulated fill recorded in `trader/portfolio.json`. It is
still strict, because the habit is the point. A paper trade is recorded only
after two gates, every time, for every order:

1. **trader-risk passed this exact order today** (matched by fingerprint).
2. **The user typed an explicit yes for this one order** in the chat.

No yes, no trade.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show                     # every ticket, READY or not
python3 "${CLAUDE_SKILL_DIR}/ticket.py" approve --index 1 --reply "yes"
python3 "${CLAUDE_SKILL_DIR}/ticket.py" result --index 1 --status placed --filled-qty 63 --filled-price 1174.30
python3 "${CLAUDE_SKILL_DIR}/ticket.py" fill --symbol RELIANCE.NS --side sell --qty 63 --price 1185.25
python3 "${CLAUDE_SKILL_DIR}/ticket.py" flatten --symbol RELIANCE.NS --qty 63
python3 "${CLAUDE_SKILL_DIR}/ticket.py" log
```

`ticket.py` never talks to a broker. It renders tickets, checks that a reply
is a real yes for that order, records paper fills, builds the flatten ticket,
and keeps the log in `trader/state/broker.json`. `--now "2026-10-29 09:45"`
pins the clock (IST).

## What it reads and writes

| file | what |
| --- | --- |
| `trader/orders.json` | the proposed orders (trader-budget writes it; `flatten` replaces it) |
| `trader/state/risk.json` | trader-risk's verdicts; only a PASS from today is READY |
| `trader/state/broker.json` | every yes, no, placed, failed and filled, with each entry's max loss |
| `trader/portfolio.json` | paper cash and shares, updated by `fill` and by `result --filled-qty` |
| `trader/plan.json` | the flat-by time for `flatten` |

The paper account starts with `budget` from `trader/config.json` (example:
Rs 1,00,000) the first time a fill is recorded.

## Steps: the entry

1. `ticket.py show`. Only READY tickets go to the user. A ticket that is NOT
   READY or BLOCKED goes back to `/trader-risk`.
2. Show ONE ticket and ask: "Take this paper trade? Reply yes or no." One
   order per question. Never offer "yes to all".
3. Run `ticket.py approve --index N --reply "<the user's reply, word for word>"`.
   If it prints "Not recorded", the reply was not an explicit yes for this
   order (for example "sure", "yes to all", or a yes that names a different
   stock or amount). Ask again. Never turn a reply into a yes yourself.
4. Record the paper fill: `ticket.py result --index N --status placed
   --filled-qty Q --filled-price P`. Use the latest price (`trader-alerts
   quote SYMBOL`) or, if it is still at the trigger, the planned entry, and
   say which. `--status denied` or `--status failed --note "..."` if the
   user changed their mind. The log keeps the entry's max loss for
   trader-risk's daily limit.

## Steps: while it is open, and out by the close

- trader-alerts watches the stop, the target and the flat-by time
  (`alerts.py add --from-plan`).
- When the price reaches the stop or the target, record that exit:
  `ticket.py fill --symbol RELIANCE.NS --side sell --qty 63 --price 1163.35`.
  The other side of the bracket is then void.
- By `flat_by` (15:15 IST), anything still open gets closed:
  1. `ticket.py flatten --symbol RELIANCE.NS` writes a market sell for the
     shares in `trader/portfolio.json` to `trader/orders.json`.
  2. `/trader-risk`. A sell that only closes what the user holds is never
     blocked by the daily limits or the entry window.
  3. `ticket.py show`, then the user's yes for that one order, then
     `ticket.py result --index 1 --status placed --filled-qty Q --filled-price P`.

## Example: RELIANCE, Thursday 29 October 2026

```
ORDER 1 of 1, PAPER TRADE (simulated: no broker is connected)
  BUY 63 RELIANCE.NS, market, good for today
  stop-loss 1163.35
  take-profit 1185.25
  max loss about Rs 689.85 if the stop fills at 1163.35 (it can fill worse in a fast market)
  why: opening-range breakout on RELIANCE.NS: 63 shares, bound by your position cap (63 x 10.95 = Rs 689.85 at the stop)
  READY: trader-risk PASS, waiting for your yes
  Reply "yes" to take this paper trade, or "no" to skip it.
```

The user replies "yes". Claude records it and the fill at 1,174.30; the log
reads `2026-10-29T09:45:00+05:30  #1 placed  BUY 63 RELIANCE.NS ...` and the
paper cash drops to Rs 26,019.10.

## Real money: not in this edition

The user trades on Angel One. This edition does not connect to it. If they
ask to place real orders, say that this pack is paper only, and that a real
connection (Angel One's SmartAPI) would be a separate change to the pack with
its own review. Even then: API keys and TOTP secrets live in environment
variables on the user's computer, never in the chat; Claude never logs in to
the user's broker account for them; and every order still needs trader-risk's
PASS and the user's explicit yes.

## What it never does

- Never records a trade without both gates, and never two trades on one yes.
- Never records trades from a scheduled or background task: nobody is there to say yes.
- Never asks for, reads, stores or repeats API keys, passwords or OTPs.
- Never sends an order to a broker, website or app.
- Never promises a fill price: a real market order and a stop fill at whatever the market gives.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- NSE edition: paper trading only. No broker is connected, and nothing in this pack sends an order anywhere.
- Cash-market stocks and ETFs only: no options, futures, margin, short selling or leverage.
