---
name: trader-budget
description: >-
  Budget Manager. Sizes every position to your budget and your max loss per
  trade. Reads the trade plan from trader-exit (entry, stop, target), finds
  the whole shares that fit inside four limits (max loss per trade, position
  cap, max order, cash after your buffer), says which limit decided it, and
  writes ONE bracket order (entry, stop-loss, take-profit) to
  trader/orders.json as a paper bracket order. A stop
  too far away for your max loss is a plain refusal, not a smaller order.
  Nothing is placed. Use when the user says "how many shares", "size this
  trade", "how much should I buy", "I have Rs 1 lakh", "I only want to risk Rs 1,000
  a trade", "set my rules", "keep 10% in cash", or after /trader-exit writes
  a plan.
argument-hint: "[budget in dollars]"
---

# trader-budget

The Budget Manager turns a plan ("buy RELIANCE at 1174.30, stop 1163.35") into an
exact order ("buy 8 shares"), inside rules the user sets once. The stop
decides the size: the further away the stop, the fewer shares. It writes a
proposal only. trader-risk checks it and trader-broker asks the user yes or
no. Day trading loses most people money. Sizing to a max loss keeps each
loss small; it does not make a trade win.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py"                        # trader/plan.json + trader/config.json
python3 "${CLAUDE_SKILL_DIR}/size.py" --write                # write trader/orders.json
python3 "${CLAUDE_SKILL_DIR}/size.py" --limit --write        # a limit order at the plan's entry
python3 "${CLAUDE_SKILL_DIR}/size.py" --limit 364.00 --json  # a limit order at 364.00
python3 "${CLAUDE_SKILL_DIR}/size.py" --weights INFY=40,KO=60 --config split.json   # weights mode, below
```

`--now "2026-10-29 10:15"` pins the clock (India time (IST)). A plan for
another day is refused: make a new one with trader-exit.

## What it reads and writes

| file | what |
| --- | --- |
| `trader/config.json` | the rules (start from `config.example.json` in this folder) |
| `trader/plan.json` | the trade: entry, stop, target, setup, flat-by time (trader-exit writes it) |
| `trader/prices.json` | optional: a fresh price above the plan's entry means a bigger risk (trader-alerts writes it) |
| `trader/portfolio.json` | optional: its cash caps the size (trader-broker keeps it) |
| `trader/orders.json` | the one proposed bracket order it writes with `--write` |

## Step 1: set the rules once

If `trader/config.json` does not exist, copy `config.example.json` into
`trader/config.json` and ask the user for each value in plain words:

- **budget**: how much money this is for. Only money they can afford to lose.
- **cash_buffer_pct**: how much always stays in cash (default 10).
- **max_loss_per_trade_usd**: the most one trade may lose if the stop fills at the stop (default 50).
- **max_position_pct**, **max_order_usd**, **min_order_usd**: the biggest position (75% of the
  budget), the biggest order (Rs 80,000) and the smallest order (Rs 100). All amounts are
  rupees; the `_usd` key names are kept from the original pack.
- The day limits trader-risk enforces: **max_daily_loss_usd** (3000), **max_trades_per_day** (3),
  **min_reward_risk** (1.0), **require_stop** (true), **no_entries_before** / **no_entries_after**
  ("09:30" / "15:00") and **flat_by** ("15:15"), all India time (IST).
- **blocked**: tickers they never want to trade.
- **paper** stays true: this edition only paper trades.

## Step 2: size the trade

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py" --write
```

Whole shares only: NSE cash-market trades are in whole shares. The size is
the smallest of four limits:

| limit | shares |
| --- | --- |
| max loss | `max_loss_per_trade_usd` / risk a share (entry minus stop) |
| position cap | budget x `max_position_pct` / entry |
| max order | `max_order_usd` / entry |
| cash | (budget minus the cash buffer) / entry, never more than the cash in `trader/portfolio.json` |

The entry it sizes at: the limit price with `--limit`. For a market order, the
plan's entry, or the price in `trader/prices.json` if it is fresh (under 15
minutes old) and higher. A price that ran up since the plan means a bigger
loss at the same stop, so fewer shares. A lower price never shrinks the risk.

It refuses, and writes no order, when: the size is zero shares, the order is
under the minimum, reward:risk is under `min_reward_risk`, the stop is not
below the entry, the target is not above it (the move already happened), the
plan is for another day, the ticker is blocked, or the plan is a short. Say
the reason to the user in one line.

## Step 3: show the user

Show the four limits, which one decided the size, the shares, the dollars
and the max loss at the stop. Say plainly that a stop is an order, not a
promise: in a fast market it can fill below the stop. Then hand over to
`/trader-risk`.

## Example: RELIANCE, Thursday 29 October 2026

Opening-range breakout: entry 1,174.30 at 9:40 AM, stop 1,163.35 (the
opening-range midpoint), target 1,185.25 (1R). Risk 10.95 a share. The
example config: Rs 1,00,000 budget, 10% cash buffer, Rs 1,000 max loss.

| limit | the math | shares |
| --- | --- | --- |
| max loss | Rs 1,000 / 10.95 | 91 |
| position cap | 75% of Rs 1,00,000 = Rs 75,000 / 1,174.30 | **63 (decides it)** |
| max order | Rs 80,000 / 1,174.30 | 68 |
| cash | Rs 1,00,000 minus Rs 10,000 = Rs 90,000 / 1,174.30 | 76 |

```
Size: 63 shares of RELIANCE.NS = Rs 73,980.90 at 1174.30. Max loss at the stop: 63 x 10.95 = Rs 689.85.
Proposed bracket order (paper trade, nothing has been placed):
  buy 63 RELIANCE.NS, market, day, take-profit 1185.25, stop-loss 1163.35
Flat by 15:15 IST: anything still open then gets closed (trader-alerts rings, trader-broker flatten).
```

The order is written to `trader/orders.json` with `why` and `plan` notes for
trader-risk and trader-broker.

## Weights mode

`--weights RELIANCE=25,HDFCBANK=25,INFY=50` or `--targets FILE`
(`targets.example.json` here, five Nifty names as an illustration) splits a
budget across a list by weight: the cash buffer comes off the top, weights
are renormalised to 100, any stock over `max_position_pct` is pinned at the
cap and its excess shared out, slices under the minimum order are dropped,
and amounts round to whole rupees. With `"fractional": false` (the example
config) it buys whole shares and needs prices (`--prices trader/prices.json`,
from `trader-alerts quote --write`). These are plain buys with no stop:
trader-risk blocks them while `require_stop` is true and counts each one
against `max_trades_per_day`. Use a separate config (`--config`) for a
long-term split.

## Rules

- Proposals only. This skill never calls a broker tool.
- Never size money the user has not said is for this. Ask for the budget and the max loss.
- Every number comes from the config, the plan or the prices. Nothing is guessed.
- No projections: never say what a trade will make. A target is a plan, not a forecast.
- Free Yahoo prices are unofficial and can lag. The broker's price is the one that fills.

## What it never does

It never places, approves or schedules an order, never raises a limit on its
own, never shrinks a stop to fit more shares, and never sizes options,
margin or short positions.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- NSE edition: paper trading only. No broker is connected, and nothing in this pack sends an order
  anywhere. trader-broker records a paper trade only when trader-risk passed that exact order today and
  the user typed an explicit yes for that one order in the chat.
- Cash-market stocks and ETFs only: no options, futures, margin, short selling or leverage.
- If a real broker (for example Angel One SmartAPI) is ever connected, its keys live in environment
  variables on the user's computer, never in the chat, and every order still needs the user's yes.
