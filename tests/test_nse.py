"""Offline tests for the NSE edition.

The fixture tests/fixtures/nse/RELIANCE.NS.json is Yahoo's real 5-minute chart
for RELIANCE.NS (range=2d), fetched on Fri 30 Oct 2026 at 11:48 IST: the full
Thu 29 Oct session (75 slots, 9:15 to 15:25, with Yahoo's 15:20 bar empty)
plus Friday morning to 11:45.
"""

import datetime
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from _load import FIX, ROOT, load

NSE = os.path.join(FIX, "nse")
CHART = os.path.join(NSE, "RELIANCE.NS.json")
SKILLS = ["trader-alerts", "trader-broker", "trader-budget", "trader-entry", "trader-exit",
          "trader-news", "trader-risk", "trader-scanner", "trader-timemachine"]
CLOCK_MODULES = [("trader-alerts", "alerts"), ("trader-broker", "ticket"), ("trader-budget", "size"),
                 ("trader-entry", "entry"), ("trader-exit", "exit"), ("trader-risk", "check"),
                 ("trader-scanner", "scan"), ("trader-timemachine", "timemachine")]
HOLIDAY_MODULES = [("trader-alerts", "alerts"), ("trader-entry", "entry"), ("trader-exit", "exit"),
                   ("trader-risk", "check"), ("trader-scanner", "scan")]


def run(script, *args, cwd=None):
    p = subprocess.run([sys.executable, "-I", os.path.join(ROOT, script)] + list(args), cwd=cwd,
                       capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


class Repo(unittest.TestCase):
    def test_nine_skills_with_matching_names(self):
        found = sorted(d for d in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, d, "SKILL.md")))
        self.assertEqual(found, SKILLS)
        for d in found:
            with open(os.path.join(ROOT, d, "SKILL.md"), encoding="utf-8") as fh:
                head = fh.read().split("---")[1]
            self.assertIn("name: %s\n" % d, head)

    def test_us_only_skills_are_gone(self):
        for d in ("trader-pelosi", "trader-analyst"):
            self.assertFalse(os.path.exists(os.path.join(ROOT, d)))

    def test_no_sec_or_alpaca_calls_left_in_code(self):
        for d in SKILLS:
            for f in os.listdir(os.path.join(ROOT, d)):
                if f.endswith(".py"):
                    with open(os.path.join(ROOT, d, f), encoding="utf-8") as fh:
                        text = fh.read()
                    self.assertNotIn("sec.gov", text, f)
                    self.assertNotIn("nasdaqtrader.com", text, f)
                    self.assertNotIn("New York", text, f)


class Clock(unittest.TestCase):
    def test_ist_everywhere(self):
        utc = datetime.datetime(2026, 10, 29, 4, 15)  # 09:45 IST
        for folder, name in CLOCK_MODULES:
            m = load(folder, name)
            self.assertEqual(m.eastern_offset(utc), 5.5, name)
            self.assertEqual(m.to_eastern(utc), datetime.datetime(2026, 10, 29, 9, 45), name)
            if hasattr(m, "eastern_to_utc"):
                self.assertEqual(m.eastern_to_utc(datetime.datetime(2026, 10, 29, 9, 45)), utc, name)

    def test_session_hours(self):
        for folder, name in CLOCK_MODULES:
            m = load(folder, name)
            if hasattr(m, "OPEN"):
                self.assertEqual((m.OPEN, m.CLOSE), (datetime.time(9, 15), datetime.time(15, 30)), name)
        tm = load("trader-timemachine", "timemachine")
        self.assertEqual((tm.OPEN_MIN, tm.CLOSE_MIN, tm.SESSION_BARS), (555, 915, 72))

    def test_one_holiday_list(self):
        lists = [load(f, n).NYSE_HOLIDAYS for f, n in HOLIDAY_MODULES]
        for other in lists[1:]:
            self.assertEqual(other, lists[0])
        h = lists[0]
        self.assertEqual(len(h), 16)
        for day in ("2026-01-26", "2026-10-02", "2026-10-20", "2026-11-10", "2026-12-25"):
            self.assertIn(day, h)
        for day in h:
            self.assertLess(datetime.date.fromisoformat(day).weekday(), 5)

    def test_alerts_clock_on_a_holiday_and_a_trading_day(self):
        code, out = run("trader-alerts/alerts.py", "clock", "--now", "2026-10-20 10:00")
        self.assertIn("Dussehra", out)
        code, out = run("trader-alerts/alerts.py", "clock", "--now", "2026-10-29 09:45")
        self.assertIn("NSE OPEN", out)
        self.assertIn("09:15 to 15:30", out)


class Symbols(unittest.TestCase):
    def test_yahoo_suffix(self):
        m = load("trader-entry", "entry")
        self.assertEqual(m.nse_symbol("reliance"), "RELIANCE.NS")
        self.assertEqual(m.nse_symbol("RELIANCE.NS"), "RELIANCE.NS")
        self.assertEqual(m.nse_symbol("^NSEI"), "^NSEI")
        self.assertEqual(m.nse_symbol("BAJAJ-AUTO"), "BAJAJ-AUTO.NS")
        self.assertIn("M%26M.NS", m.chart_path("M&M", "1d", "5m"))

    def test_risk_assets(self):
        r = load("trader-risk", "check")
        for s in ("RELIANCE", "RELIANCE.NS", "M&M", "BAJAJ-AUTO", "NIFTYBEES"):
            self.assertTrue(r.TICKER.match(s), s)
        self.assertTrue(r.OCC.match("NIFTY26NOV25000CE"))
        self.assertTrue(r.FUTURE.search("BANKNIFTY26NOVFUT"))
        self.assertFalse(r.TICKER.match("BTC/USD"))

    def test_nifty50(self):
        s = load("trader-scanner", "scan")
        syms = [x for x, _ in s.NIFTY50]
        self.assertEqual(len(syms), 50)
        self.assertEqual(len(set(syms)), 50)
        self.assertIn("BSE", syms)
        self.assertNotIn("WIPRO", syms)
        csv_text = ("﻿Company Name,Industry,Symbol,Series,ISIN Code\n"
                    "Reliance Industries Ltd.,Oil Gas,RELIANCE,EQ,INE002A01018\n"
                    "Mahindra & Mahindra Ltd.,Automobile,M&M,EQ,INE101A01026\n")
        self.assertEqual(s.parse_nifty_csv(csv_text),
                         [("RELIANCE", "Reliance Industries Ltd."), ("M&M", "Mahindra & Mahindra Ltd.")])


class RealBars(unittest.TestCase):
    def test_entry_triggers_on_the_935_bar(self):
        code, out = run("trader-entry/entry.py", "check", "RELIANCE", "--setup", "orb",
                        "--offline", CHART, "--now", "2026-10-29 10:15")
        self.assertIn("Opening range 9:15-9:30: high Rs 1170.50, low Rs 1156.20", out)
        self.assertIn("TRIGGERED 9:40 AM at Rs 1174.30", out)

    def test_entry_waits_today(self):
        code, out = run("trader-entry/entry.py", "check", "RELIANCE", "--setup", "orb",
                        "--offline", CHART, "--now", "2026-10-30 11:50")
        self.assertIn("high Rs 1171.60, low Rs 1162.00", out)
        self.assertIn("WAITING", out)

    def test_orb_scan(self):
        code, out = run("trader-scanner/scan.py", "orb", "--offline", NSE, "--now", "2026-10-29 10:15",
                        "--no-write")
        self.assertIn("15-minute range (9:15 to", out)
        self.assertIn("RELIANCE.NS Rs 1,174.30", out)

    def test_orb_tolerates_a_few_missing_bars(self):
        s = load("trader-scanner", "scan")
        with open(CHART) as fh:
            doc = json.load(fh)
        day = datetime.date(2026, 10, 29)
        cutoff = datetime.datetime(2026, 10, 29, 11, 0)

        def with_holes(times):
            series = s.parse_chart(json.loads(json.dumps(doc)))
            for i, ts in enumerate(series["t"]):
                if s.ts_to_eastern(ts).strftime("%H:%M") in times:
                    series["c"][i] = None
            return s.session_bars(series, day, cutoff)

        full = with_holes(())
        self.assertTrue(s.usable(full, day, cutoff, 3))
        self.assertEqual(s.gaps(full, day, cutoff), 0)
        two = with_holes(("10:00", "10:30"))  # Yahoo's odd empty bars: still scanned
        self.assertTrue(s.usable(two, day, cutoff, 3))
        self.assertEqual(s.gaps(two, day, cutoff), 2)
        hit = s.orb_hit(two, 3)
        self.assertEqual((hit["price"], hit["at"], hit["bar_index"]), (1174.3, "9:40 AM", 4))
        self.assertEqual(hit["missing_before"], 0)  # the gaps came after the breakout: time is exact
        self.assertEqual(s.orb_hit(full, 3)["missing_before"], 0)
        self.assertTrue(s.usable(with_holes(("10:00", "10:30", "10:45")), day, cutoff, 3))  # three is the limit
        self.assertFalse(s.usable(with_holes(("10:00", "10:30", "10:45", "10:50")), day, cutoff, 3))  # too many
        self.assertFalse(s.usable(with_holes(("09:20",)), day, cutoff, 3))  # a range bar missing
        # a missing breakout bar is skipped, never guessed: the next bar above the high is the hit
        hit = s.orb_hit(with_holes(("09:35",)), 3)
        self.assertEqual((hit["bar_start"], hit["bar_index"], hit["missing_before"]), ("09:40", 5, 1))
        code, out = run("trader-scanner/scan.py", "orb", "--offline", NSE, "--now", "2026-10-29 10:15",
                        "--no-write")
        self.assertNotIn("time uncertain", out)

    def test_timemachine_keeps_sessions_with_empty_closing_bars(self):
        tm = load("trader-timemachine", "timemachine")
        with open(CHART) as fh:
            res = json.load(fh)["chart"]["result"][0]
        meta, bars, dropped = tm.parse_bars(res, datetime.datetime(2026, 10, 30, 6, 20))
        days = tm.split_sessions(bars)
        self.assertEqual(len(days["2026-10-29"]), 72)  # 9:15..15:10; Yahoo's empty 15:20 bar is past the cut
        full, short = tm.full_sessions(days, "2026-10-30")
        self.assertEqual([d for d, _ in full], ["2026-10-29"])


class PaperTrade(unittest.TestCase):
    """The whole pack on real bars: entry -> exit -> time machine -> budget -> risk -> broker -> alerts."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "trader"))
        shutil.copy(os.path.join(ROOT, "trader-budget", "config.example.json"),
                    os.path.join(self.dir, "trader", "config.json"))
        self.now = "2026-10-29 09:45"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def step(self, script, *args, ok=(0,)):
        code, out = run(script, *args, cwd=self.dir)
        self.assertIn(code, ok, out)
        return out

    def synthetic_history(self):
        """30 past sessions shaped like the real 29 Oct one (scaled +-3 %), then the real two days."""
        with open(CHART) as fh:
            doc = json.load(fh)
        r = doc["chart"]["result"][0]
        ts, q = r["timestamp"], r["indicators"]["quote"][0]
        day = [i for i, t in enumerate(ts) if t < 1793331900]
        rnd = random.Random(7)
        cols = {c: [] for c in ("open", "high", "low", "close", "volume")}
        stamps = []
        for k in range(30, 0, -1):
            f = 1 + rnd.uniform(-0.03, 0.03)
            for i in day:
                stamps.append(ts[i] - (k + 1) * 86400)
                for c in cols:
                    v = q[c][i]
                    cols[c].append(None if v is None else (v if c == "volume" else v * f))
        for i in range(len(ts)):
            stamps.append(ts[i])
            for c in cols:
                cols[c].append(q[c][i])
        r["timestamp"], r["indicators"]["quote"][0] = stamps, cols
        path = os.path.join(self.dir, "history.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        return path

    def test_paper_trade_end_to_end(self):
        n = self.now
        out = self.step("trader-entry/entry.py", "check", "RELIANCE", "--setup", "orb", "--offline", CHART,
                        "--now", n, "--write")
        self.assertIn("TRIGGERED", out)
        out = self.step("trader-exit/exit.py", "plan", "--from", "trader/entry.json", "--stop", "or-mid",
                        "--target", "1R", "--write", "--now", n)
        self.assertIn("Stop          Rs 1,163.35", out)
        self.assertIn("Flat by       15:15 IST", out)
        out = self.step("trader-timemachine/timemachine.py", "run", "--offline", self.synthetic_history(),
                        "--replays", "500", "--now", n)
        self.assertIn("last 30 full sessions", out)
        self.assertIn("still open at 3:15 PM", out)
        out = self.step("trader-budget/size.py", "--write", "--now", n)
        self.assertIn("Max loss at the stop: 63 x 10.95 = Rs 689.85", out)
        out = self.step("trader-risk/check.py", "--now", n)
        self.assertIn("PASS  #1 buy RELIANCE.NS 63 shares", out)
        out = self.step("trader-broker/ticket.py", "show", "--now", n)
        self.assertIn("PAPER TRADE (simulated: no broker is connected)", out)
        out = self.step("trader-broker/ticket.py", "approve", "--index", "1", "--reply", "yes all", "--now", n,
                        ok=(1,))
        self.assertIn("Not recorded", out)
        self.step("trader-broker/ticket.py", "approve", "--index", "1", "--reply", "yes", "--now", n)
        self.step("trader-broker/ticket.py", "result", "--index", "1", "--status", "placed", "--filled-qty", "63",
                  "--filled-price", "1174.30", "--now", n)
        out = self.step("trader-broker/ticket.py", "log", "--now", n)
        self.assertIn("2026-10-29T09:45:00+05:30", out)
        with open(os.path.join(self.dir, "trader", "portfolio.json")) as fh:
            port = json.load(fh)
        self.assertAlmostEqual(port["cash"], 100000 - 63 * 1174.30, places=2)
        out = self.step("trader-alerts/alerts.py", "add", "--from-plan")
        self.assertIn('"at": "15:15"', out)


class News(unittest.TestCase):
    def test_headlines_and_indian_tags(self):
        d = tempfile.mkdtemp()
        try:
            rss = ("<?xml version='1.0'?><rss><channel><item><title>RBI holds repo rate; Reliance gains"
                   "</title><link>https://example.com/a</link><guid>a</guid>"
                   "<pubDate>Fri, 30 Oct 2026 04:00:00 +0000</pubDate></item><item>"
                   "<title>SEBI order on block deal</title><link>https://example.com/b</link><guid>b</guid>"
                   "<pubDate>Fri, 30 Oct 2026 05:00:00 +0000</pubDate></item></channel></rss>")
            with open(os.path.join(d, "yahoo-RELIANCE.xml"), "w") as fh:
                fh.write(rss)
            shutil.copy(CHART, os.path.join(d, "chart-RELIANCE.json"))
            code, out = run("trader-news/news.py", "--tickers", "RELIANCE", "--offline", d, "--now",
                            "2026-10-30T06:30:00Z", "--dry-run", "--json")
            doc = json.loads(out)
            tags = {i["title"]: i["tags"] for i in doc["items"]}
            self.assertIn("macro", tags["RBI holds repo rate; Reliance gains"])
            self.assertIn("regulatory", tags["SEBI order on block deal"])
            self.assertEqual(doc["moves"][0]["prev_close"], 1167.4)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        news = load("trader-news", "news")
        self.assertIn("region=IN", news.YAHOO)


if __name__ == "__main__":
    unittest.main()
