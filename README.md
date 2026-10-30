# The Day Trader skill: NSE edition

9 Claude skills for intraday trading on India's NSE: scan the Nifty 50,
track the news, time every entry and exit, and replay the outcomes before
you risk a rupee. **Paper trading only.**

A fork of [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)
(MIT), adapted for the National Stock Exchange of India:

| | original | this fork |
| --- | --- | --- |
| market | NYSE / Nasdaq, 9:30–16:00 New York | NSE, 9:15–15:30 IST (UTC+5:30) |
| universe | ~5,900 US stocks (Nasdaq Trader) | Nifty 50 (niftyindices.com, built-in fallback) |
| symbols | TSLA | RELIANCE (`.NS` added for Yahoo); M&M, BAJAJ-AUTO work |
| holidays | NYSE 2026–2027 | NSE equity trading holidays 2026 |
| entry window / flat by | 9:45–15:30 / 15:55 | 9:30–15:00 / 15:15 (brokers square off intraday from ~15:20) |
| money | dollars | rupees (example config: Rs 1,00,000 budget, Rs 1,000 max loss a trade) |
| news | Yahoo + SEC 8-K filings | Yahoo .NS headlines, Indian tags (RBI, SEBI, results, block deals) |
| broker | Alpaca / IBKR | **paper only**, no broker connected |
| removed | | trader-pelosi (US Congress trades), trader-analyst (SEC filings) |

Free, MIT, no signup, no API key. The tools are plain Python (3.8+, standard
library only) that read Yahoo Finance's free, unofficial chart data.

## Install

In Claude Code:

```bash
git clone https://github.com/vadlashiva/day-trader-skill.git
cp -r day-trader-skill/trader-* ~/.claude/skills/
```

Or project-local: copy the same folders into your repo's `.claude/skills/`.
In the Claude app, upload each `trader-*` folder as a zip in your skills
settings. No Claude Code at all? Paste any single SKILL.md at the top of a
chat and it runs as a mode; you lose the Python tools, but the method works.

Copy `trader-budget/config.example.json` to `trader/config.json` in your
project and set your own budget and limits (amounts are rupees; the `_usd`
key names are kept from the original pack).

## The nine

| command | job | what it does |
| --- | --- | --- |
| `/trader-scanner` | Chart Scanner | Scans the Nifty 50 for setups: opening-range breakouts, flags, oversold bounces. |
| `/trader-news` | News Monitor | Tracks headlines on every stock you watch and flags what moves it. |
| `/trader-entry` | Entry Timer | Watches a setup bar by bar and tells you the moment to get in. |
| `/trader-exit` | Exit Planner | Sets your stop and your target before you enter. |
| `/trader-timemachine` | Time Machine | Replays the rest of the session 10,000 times from the stock's own recent bars, plus every past day the setup fired. |
| `/trader-budget` | Budget Manager | Sizes every position to your budget and your max loss per trade. |
| `/trader-risk` | Risk Manager | Checks every trade against your limits and blocks anything over them. |
| `/trader-broker` | Order Executor | Records approved trades as paper fills, never without your yes. |
| `/trader-alerts` | Price Alerts | Rings when a price, a stop, the flat-by time or the opening bell hits. |

## How to use it

Everything lands in a `trader/` folder in your project, and each skill reads
what the last one wrote:

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker (one paper trade)
alerts: stop, target, flat by 15:15 (while it is open)
```

An example on real data: RELIANCE, Thursday 29 October 2026.

- `/trader-scanner orb` at 10:15 IST: RELIANCE's opening range (9:15–9:30)
  was 1,156.20 to 1,170.50; the 9:35 bar closed at 1,174.30, 0.32 % over the top.
- `/trader-entry RELIANCE`: triggered at 9:40 AM, 1,174.30.
- `/trader-exit`: stop at the range midpoint, 1,163.35 (10.95 a share at risk);
  target 1R, 1,185.25; flat by 15:15.
- `/trader-timemachine`: replays the rest of the day from RELIANCE's last 60
  days of 5-minute bars and gives the odds of target first, stop first or neither.
- `/trader-budget` with Rs 1,00,000 and a Rs 1,000 max loss: 63 shares
  (bound by the 75 % position cap), Rs 73,980.90; loss at the stop Rs 689.85.
- `/trader-risk`: PASS.
- `/trader-broker`: you type yes; the paper fill is recorded.
- `/trader-alerts`: rings on the stop, the target and at 15:15.

## The tools

```bash
python3 trader-scanner/scan.py universe                  # the Nifty 50 -> trader/universe.txt
python3 trader-scanner/scan.py daily                     # pre-market setups
python3 trader-scanner/scan.py orb --at 10:15            # opening-range breakouts so far
python3 trader-news/news.py --tickers RELIANCE --hours 12
python3 trader-entry/entry.py check RELIANCE --setup orb
python3 trader-entry/entry.py watch RELIANCE --every 30
python3 trader-exit/exit.py plan --stop or-mid --target 1R --write
python3 trader-timemachine/timemachine.py run --write
python3 trader-budget/size.py --write
python3 trader-risk/check.py
python3 trader-broker/ticket.py show
python3 trader-alerts/alerts.py add --from-plan
python3 trader-alerts/alerts.py clock                    # is NSE open?
python3 -m unittest discover -s tests -v
```

The tests run offline on Yahoo's real 5-minute bars for RELIANCE.NS
(29–30 October 2026) and walk a full paper trade end to end.

## NSE notes

- **The last bars of the day.** Yahoo's 15:15–15:25 five-minute bars for NSE
  stocks are empty on most days, so the Time Machine treats 9:15–15:15
  (72 bars) as a full session and ends every replay at 15:15.
- **Holidays.** 2026 is built in. Add 2027 to the `NYSE_HOLIDAYS` lists (the
  name is kept from the original) when NSE publishes its circular, usually in
  December. Muhurat trading is not modelled.
- **Nifty 50 membership** changes in March and September. `scan.py universe`
  refreshes it from niftyindices.com; the built-in list is as of the
  September 2026 review (BSE in, Wipro out).
- **Company announcements** (results, board meetings, dividends) are on
  nseindia.com and bseindia.com; the news skill does not read them.

## Fine print

Not financial advice. This is software that reads public data and does
arithmetic. It does not know your situation and it cannot see the future.
SEBI's studies show that most individual intraday traders in equities lose
money. You can lose money. Decide for yourself, and talk to a SEBI-registered
adviser if you need advice.

**Paper only.** No broker is connected. Nothing in this pack sends an order
anywhere; `/trader-broker` records simulated fills after `/trader-risk`
passes and you type yes. If you later connect a real broker (for example
Angel One's SmartAPI), keep keys in environment variables, never in the chat,
and keep every order behind the same two gates.

**The Time Machine is a simulation, not a prediction.** The future can do
things the last 60 days never did: results, a block deal, a circuit, a
headline.

**A stop is a plan, not a guarantee.** In a fast market or across a gap, a
stop can fill well past its price.

**The data is free and unofficial.** Yahoo's chart endpoint can lag, change
or rate-limit you. Check anything that matters against your broker before
you act on it.

**Taxes.** Intraday equity gains are speculative business income in India.
Nothing here is tax advice.

MIT. Original by Jake Schincariol; NSE adaptation by Shiva Kumar V.
