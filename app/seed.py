"""Seeds position_metadata for the demo. This is administrative backfill, not
the entry-gate save path — it does not go through missing_checklist_fields
(that only applies to new positions saved through the API/UI, per
docs/ARCHITECTURE.md §6). Legacy assets are grandfathered in with minimal
metadata, matching the "legacy book" transition described in
docs/investment-rules-v1.md §9."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import PositionMetadata


def _days_ago(n: int) -> date:
    return date.today() - timedelta(days=n)


SATELLITES = [
    dict(
        asset="SOL",
        cost_basis=40.0,
        entry_date=_days_ago(200),
        thesis="L1 with real throughput and a live app ecosystem; fee revenue funds validator rewards.",
        catalyst_name="Firedancer mainnet rollout",
        catalyst_date=_days_ago(-120),
        invalidation="Firedancer misses two consecutive quarterly targets",
        unlock_schedule_pct=3.0,
        liquidity_note="Exitable same-day on Coinbase/Gate without moving price",
        value_accrual="Transaction fees burned; validator staking yield funded by real usage",
        fresh_cash_test=True,
        ladder_3x_price=120.0,
        ladder_5x_price=200.0,
        ladder_10x_price=400.0,
        hard_stop_price=26.0,
        time_stop_date=_days_ago(-165),
        narrative_cluster="solana",
        classification="satellite",
    ),
    dict(
        asset="RENDER",
        cost_basis=0.40,  # true purchase price — see docs/rules-engine-build-spec.md §3
        venue_reported_cost_basis=6.29,  # Swyftx transfer-date price, not the real basis
        entry_date=_days_ago(400),
        thesis="GPU rendering marketplace; token used to pay node operators for compute.",
        catalyst_name="Render Network v2 compute marketplace",
        catalyst_date=_days_ago(60),
        invalidation="Node operator count declines for two consecutive quarters",
        unlock_schedule_pct=8.0,
        liquidity_note="Exitable same-day on Swyftx without moving price",
        value_accrual="Compute payments settle in RENDER; burn-and-mint on usage",
        fresh_cash_test=False,
        ladder_3x_price=1.20,
        ladder_5x_price=2.00,
        ladder_10x_price=4.00,
        hard_stop_price=0.26,
        time_stop_date=_days_ago(-30),
        narrative_cluster="ai",
        classification="satellite",
    ),
    dict(
        asset="FET",
        cost_basis=0.55,
        entry_date=_days_ago(250),
        thesis="Agent framework positioning for on-chain AI agent transactions.",
        catalyst_name="ASI:Chain mainnet",
        catalyst_date=_days_ago(-90),
        invalidation="ASI:Chain mainnet slips past 2027 with no interim usage growth",
        unlock_schedule_pct=6.0,
        liquidity_note="Exitable same-day on Crypto.com without moving price",
        value_accrual="Agent transaction fees paid in FET",
        fresh_cash_test=False,
        ladder_3x_price=1.65,
        ladder_5x_price=2.75,
        ladder_10x_price=5.50,
        hard_stop_price=0.36,
        time_stop_date=_days_ago(-115),
        narrative_cluster="ai",
        classification="satellite",
    ),
    dict(
        asset="JTO",
        cost_basis=1.60,
        entry_date=_days_ago(180),
        thesis="Solana's dominant liquid-staking/MEV protocol; captures MEV revenue.",
        catalyst_name="JitoSOL restaking integration",
        catalyst_date=_days_ago(-45),
        invalidation="JitoSOL market share drops below 20% of Solana liquid staking",
        unlock_schedule_pct=4.0,
        liquidity_note="Exitable same-day on Gate without moving price",
        value_accrual="MEV and staking revenue shared with JTO stakers",
        fresh_cash_test=True,
        ladder_3x_price=4.80,
        ladder_5x_price=8.00,
        ladder_10x_price=16.00,
        hard_stop_price=1.04,
        time_stop_date=_days_ago(-185),
        narrative_cluster="solana",
        classification="satellite",
    ),
    dict(
        asset="PUMP",
        cost_basis=0.0031,
        entry_date=_days_ago(90),
        thesis="Dominant Solana memecoin launchpad; fee switch funds buybacks.",
        catalyst_name="Fee-switch buyback activation",
        catalyst_date=_days_ago(-30),
        invalidation="Launch volume share drops below 40% for a full quarter",
        unlock_schedule_pct=15.0,
        liquidity_note="Exitable same-day on Crypto.com without moving price",
        value_accrual="Platform fees fund token buybacks",
        fresh_cash_test=True,
        ladder_3x_price=0.0093,
        ladder_5x_price=0.0155,
        ladder_10x_price=0.031,
        hard_stop_price=0.002,
        time_stop_date=_days_ago(-275),
        narrative_cluster="solana",
        classification="satellite",
    ),
]

# Legacy: grandfathered in under the old ("interesting tech") approach —
# minimal metadata, wind-down only, per investment-rules-v1.md §9.
LEGACY = [
    ("AERO", 1.10, "DEX on Base; superseded by narrower satellite bets."),
    ("EDU", 0.55, "Education-chain thesis never found usage."),
    ("CSPR", 0.045, "L1 with no meaningful adoption."),
    ("NAKA", 0.09, "Speculative L1 position from the pre-rules era."),
    ("GFI", 0.06, "RWA lending token, thin liquidity."),
    ("SYS", 0.09, "Near-worthless — candidate for worthless-asset tax provisions."),
    ("BRD", 0.02, "Near-worthless — candidate for worthless-asset tax provisions."),
    ("MBOX", 0.11, "Near-worthless — candidate for worthless-asset tax provisions."),
    ("VIDT", 0.006, "Near-worthless — candidate for worthless-asset tax provisions."),
]


def seed(db: Session) -> None:
    if db.query(PositionMetadata).count() > 0:
        return

    for data in SATELLITES:
        db.add(PositionMetadata(**data))

    for asset, cost_basis, thesis in LEGACY:
        db.add(
            PositionMetadata(
                asset=asset,
                cost_basis=cost_basis,
                entry_date=_days_ago(700),
                thesis=thesis,
                catalyst_name="n/a — legacy, wind-down only",
                catalyst_date=_days_ago(700),
                invalidation="n/a — legacy, wind-down only",
                unlock_schedule_pct=0.0,
                liquidity_note="Dust-tier; likely dust-convert-only at exchange minimums",
                value_accrual="n/a — grandfathered from the pre-rules approach",
                fresh_cash_test=False,
                ladder_3x_price=cost_basis * 3,
                ladder_5x_price=cost_basis * 5,
                ladder_10x_price=cost_basis * 10,
                hard_stop_price=cost_basis * 0.65,
                time_stop_date=_days_ago(335),
                narrative_cluster="legacy",
                classification="legacy",
            )
        )

    db.commit()
