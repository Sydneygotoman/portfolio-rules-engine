# Investment Rules — v1.0

**Written:** 1 September 2026
**Portfolio at writing:** ~$13,686 AUD across 5 venues, ~123 positions
**Contributions:** $500/month
**Review:** quarterly. Rules can only be changed at review, never mid-trade.

---

## 0. Why this exists

The previous approach — "buy projects with interesting tech and real-world utility" — produced 123 positions, a 69% drawdown, and no exits. It failed for three specific reasons:

1. The filter admitted everything. Every crypto project claims interesting tech and real-world utility.
2. It measured the wrong thing. Several picks were correct about the technology (ONDO, RENDER, GRT, FIL) and the tokens fell anyway, because nothing connected network usage to token price.
3. There were no exits. Nothing was ever sold — not at 34x, not at -90%.

Every rule below exists to fix one of those three.

---

## 1. Hard prohibitions — never, no exceptions

- **No leverage. No margin. No perpetuals. No futures. No options.**
- No borrowing to invest. No credit.
- No trading outside the scheduled weekly window (except a hard stop firing).
- No buying a position that fails the entry checklist, for any reason.
- No position opened without a written thesis and invalidation.

These are not preferences. They are the boundary. The Coinbase app advertises BTC/ETH/SOL perps at 2–50x one tap from the balance screen. At 50x, a 2% adverse move is a full liquidation. The urge to use it will be strongest when furthest behind — which is exactly when it is most lethal.

---

## 2. Portfolio structure

| Rule | Target |
|---|---|
| Maximum positions | **10** |
| Minimum position size | **5% of portfolio** (~$684 today) |
| Maximum position size | **20%** — trim back on breach |
| Cash floor | **20%** |
| Core (BTC + ETH) | **50% minimum** |
| Maximum per narrative/cluster | **25%** |

**Current gap:** core is $1,084 (7.9%). Target is ~$6,843. Gap ≈ $5,759.

**Narrative clusters count as one position for correlation purposes.** SOL + PUMP + JTO is a Solana bet. RENDER + FET + AKT + IO is an AI bet. Diversification that doesn't reduce correlation isn't diversification.

**Position sizing uses total portfolio across all venues**, never a single exchange balance. Duplicate holdings across venues (AERO, EDU, NAKA, GFI, CSPR) count as one position.

---

## 3. Entry rules

### 3.1 Primary filter

**Alts:** must be **outperforming BTC over the trailing 90 days.** No exceptions. If it isn't beating the benchmark, holding it means taking alt risk for below-BTC returns.

**BTC and ETH:** scheduled accumulation regardless of price. Dip-buying is permitted here only, because these are the only holdings with a demonstrated floor.

### 3.2 Checklist — all six, written down, before buying

1. **Value accrual.** Name the specific mechanism connecting network usage to token price — fee burn, revenue-funded buyback, revenue-funded staking. If none exists, it is a narrative trade. Label it as such and size it at minimum.
2. **Named catalyst with a date window.** "ASI:Chain mainnet, Q1 2027" — not "AI is big."
3. **Written invalidation.** What specifically would prove this wrong.
4. **Unlock schedule.** What % of supply vests in the next 12 months. High emissions into thin liquidity is how tokens bleed regardless of fundamentals.
5. **Liquidity.** Can the full position be exited in one day without moving price.
6. **Fresh cash test.** Would I buy this today, at this price, owning none?

### 3.3 Minimum target

**Must have a credible path to 100%+.** Below that, Swyftx's ~1.6% round-trip cost and the tax friction make the trade not worth taking.

### 3.4 What does NOT qualify as a reason to buy

- Interesting technology
- Real-world utility, absent a value-accrual mechanism
- Low unit price, or "I can get 10 million of these"
- Someone else's conviction
- It's down a lot
- It feels like a good opportunity

---

## 4. Exit rules — set at entry, executed without deliberation

### 4.1 Profit ladder

| Trigger | Action |
|---|---|
| **3x** | Sell 33% — **cost basis fully off the table** |
| **5x** | Sell 25% |
| **10x** | Sell 25% |
| Remainder | Runs indefinitely |
| **Above 20% weight** | Trim to 20%, regardless of multiple |

You will sell into rallies that keep going. Every time. That is the price of the system, and it is far cheaper than the alternative already experienced.

### 4.2 Stops — four kinds

| Type | Trigger | Action |
|---|---|---|
| **Hard stop** | −35% from entry | Exit |
| **Time stop** | 12 months, no catalyst progress | Exit regardless of price |
| **Relative stop** | Underperforming BTC by 30% over 90 days | Mandatory review, default is exit |
| **Thesis invalidation** | The written invalidation occurs | Exit immediately, price irrelevant |

Three of the four fire without predicting anything.

### 4.3 Tax note

12-month holds qualify for the 50% CGT discount. Where an exit can be timed past the anniversary, do so. **But never hold a broken position to chase the discount** — a 50% discount on a gain given back entirely is worth nothing.

---

## 5. Deploying the $500/month

**Months 1–11 (Sept 2026 – Jul 2027):** 100% into BTC/ETH, roughly 70/30. Fixed day each month. No timing. This closes the core gap by ~August 2027 without selling anything.

**From month 12:** $300 core, $200 accumulating toward satellites. At a $684 minimum, that is one new satellite roughly every three months — three or four a year, each fully researched.

**Rules:**
- Cash floor tops to 20% before anything else.
- Never deploy a full contribution in one buy — split across 3–4.
- Never add to a position already above target weight.
- **New money never touches the legacy book.** Run them as two separate portfolios.

---

## 6. Venues

| Venue | Role |
|---|---|
| **Swyftx** | AUD rails, long-term core. Free deposits, AUSTRAC-registered. High fees irrelevant on multi-year holds. |
| **Coinbase** | BTC custody. |
| **KuCoin / Gate** | Wind down and close. ~$645 combined, mostly unsellable dust, non-AUSTRAC counterparty risk for 5% of the portfolio. |
| **Crypto.com** | Wind down. |

Every transfer between venues is a cost-basis event. Minimise them.

---

## 7. Routine

**Weekly — 30 min, same day each week**
1. Check every position against ladder levels, stops, time stops. Act on triggers. No discretion.
2. Update journal.
3. Note watchlist candidates.
4. Close the app.

**Monthly — 1 hr**
- Execute the $500 contribution.
- Check allocation vs targets. Rebalance breaches.
- Review watchlist against the 90-day relative strength filter.

**Quarterly — 2 hr**
- Review whether the rules are working. Amend if needed. Version the change.
- Tax position review.

**No trades outside these windows** except a hard stop firing. This single constraint removes the emotional trade.

---

## 8. Journal — one row per position, updated weekly

| Field |
|---|
| Ticker / venue / size / % of portfolio |
| Entry date, entry price, cost basis |
| Written thesis (2 sentences) |
| Named catalyst + date window |
| Written invalidation |
| Ladder levels (3x / 5x / 10x prices) |
| Hard stop price |
| Time stop date |
| 90-day performance vs BTC |
| Status |

Without this you cannot tell whether the rules are working, which means you can never improve them.

---

## 9. Legacy book transition

**Sequence matters. Do not skip step 1.**

1. **Set up consolidated tracking** (Koinly or CryptoTaxCalculator — AU CGT native). Connect all five venues. **Blocks everything else** — Swyftx shows wrong cost basis on transferred-in coins, KuCoin and Gate show none at all.
2. **Export Binance transaction history immediately.** Exchange records get purged. Without it, actual cost basis on transferred coins (e.g. RENDER bought at 40c, displayed as a $1,968 loss when it's likely a gain) is unprovable.
3. **Dust-convert** everything below exchange minimum order size. Not a decision — those positions cannot be sold.
4. **Stage disposals Oct 2026 – Mar 2027.** Not June. Every Australian harvests losses in June; thin small-cap books plus concentrated selling means poor fills.
5. **Pair loss realisation with gain realisation** in the same financial year so losses shelter gains.
6. Close KuCoin, Gate, Crypto.com.

**Get an accountant involved before any disposals.** Wash-sale anti-avoidance provisions apply if anything sold is rebought. Worthless-asset provisions may apply to the four zero-value holdings (SYS, BRD, MBOX, VIDT, ~$1,306 cost basis).

---

## 10. Amendment

Rules change only at quarterly review, never mid-position, never while a trade is open, never in response to a single loss.

Every amendment gets a version number, a date, and a one-line reason.

---

*This is a personal rule set, not financial advice. All decisions and their consequences are the author's own.*
