from contextlib import asynccontextmanager
from datetime import date, datetime

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import seed as seed_module
from app.aggregation import build_snapshot
from app.db import SessionLocal, get_db, init_db
from app.exchange_adapters import get_adapters
from app.models import JournalEntry, PositionMetadata, SystemEvent
from app.rules_engine import breaches_only, evaluate_all, missing_checklist_fields
from app.rules_engine.entry_gate import check_alt_outperformance
from app.sync import build_price_history, sync_all

CONTRIBUTION_MONTHLY_AUD = 500
CORE_GAP_MONTHS_TARGET = 11  # spec §5: months 1-11 close the core gap


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_module.seed(db)
        sync_all(db, get_adapters())
    finally:
        db.close()
    yield


app = FastAPI(title="Portfolio Rules Engine", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def _context(db: Session):
    snapshot = build_snapshot(db)
    price_history = build_price_history(db)
    results = evaluate_all(snapshot, price_history, today=date.today())
    breaches = breaches_only(results)
    return snapshot, results, breaches


@app.get("/")
def index():
    return RedirectResponse("/overview")


@app.get("/overview")
def overview(request: Request, db: Session = Depends(get_db)):
    snapshot, results, breaches = _context(db)
    total = snapshot.total_value
    core_value = sum(p.value for p in snapshot.positions if p.asset in ("BTC", "ETH"))
    satellite_value = sum(p.value for p in snapshot.non_legacy() if p.asset not in ("BTC", "ETH"))
    legacy_value = sum(p.value for p in snapshot.legacy())
    allocation = {
        "core": core_value,
        "satellite": satellite_value,
        "cash": snapshot.cash_total,
        "legacy": legacy_value,
    }
    return templates.TemplateResponse(
        request,
        "overview.html",
        {
            "active": "overview",
            "total": total,
            "allocation": allocation,
            "breach_count": len([r for r in breaches if r.status == "breach"]),
            "warning_count": len([r for r in breaches if r.status == "warning"]),
            "top_breaches": breaches[:5],
        },
    )


@app.get("/breaches")
def breaches_page(request: Request, db: Session = Depends(get_db)):
    _, _, breaches = _context(db)
    return templates.TemplateResponse(request, "breaches.html", {"active": "breaches", "breaches": breaches})


@app.get("/positions")
def positions_page(request: Request, db: Session = Depends(get_db)):
    snapshot, results, _ = _context(db)
    total = snapshot.total_value
    by_asset = {}
    for r in results:
        if r.asset:
            by_asset.setdefault(r.asset, []).append(r)
    rows = []
    for p in snapshot.non_legacy():
        weight = p.value / total if total else 0
        rows.append({"position": p, "weight": weight, "rules": by_asset.get(p.asset, [])})
    return templates.TemplateResponse(request, "positions.html", {"active": "positions", "rows": rows})


@app.get("/positions/add")
def add_position_form(request: Request):
    return templates.TemplateResponse(
        request, "add_position.html", {"active": "add_position", "errors": [], "values": {}}
    )


@app.post("/positions/add")
def add_position_submit(
    request: Request,
    db: Session = Depends(get_db),
    asset: str = Form(...),
    cost_basis: float = Form(...),
    entry_date: date = Form(...),
    thesis: str = Form(""),
    value_accrual: str = Form(""),
    catalyst_name: str = Form(""),
    catalyst_date: date | None = Form(None),
    invalidation: str = Form(""),
    unlock_schedule_pct: str = Form(""),
    liquidity_note: str = Form(""),
    fresh_cash_test: str = Form(""),
    ladder_3x_price: float = Form(0),
    ladder_5x_price: float = Form(0),
    ladder_10x_price: float = Form(0),
    hard_stop_price: float = Form(0),
    time_stop_date: date | None = Form(None),
    narrative_cluster: str = Form(""),
    classification: str = Form("satellite"),
):
    checklist = {
        "value_accrual": value_accrual,
        "catalyst_name": catalyst_name,
        "catalyst_date": catalyst_date.isoformat() if catalyst_date else "",
        "invalidation": invalidation,
        "unlock_schedule_pct": unlock_schedule_pct,
        "liquidity_note": liquidity_note,
        "fresh_cash_test": fresh_cash_test,
    }
    missing = missing_checklist_fields(checklist)
    if missing:
        return templates.TemplateResponse(
            request,
            "add_position.html",
            {
                "active": "add_position",
                "errors": [f"Missing required field: {m}" for m in missing],
                "values": dict(asset=asset, cost_basis=cost_basis, thesis=thesis, **checklist),
            },
            status_code=422,
        )

    price_history = build_price_history(db)
    warning = check_alt_outperformance(asset, price_history)

    db.add(
        PositionMetadata(
            asset=asset.upper(),
            cost_basis=cost_basis,
            entry_date=entry_date,
            thesis=thesis,
            value_accrual=value_accrual,
            catalyst_name=catalyst_name,
            catalyst_date=catalyst_date or entry_date,
            invalidation=invalidation,
            unlock_schedule_pct=float(unlock_schedule_pct or 0),
            liquidity_note=liquidity_note,
            fresh_cash_test=fresh_cash_test.lower() in ("true", "on", "yes", "1"),
            ladder_3x_price=ladder_3x_price,
            ladder_5x_price=ladder_5x_price,
            ladder_10x_price=ladder_10x_price,
            hard_stop_price=hard_stop_price,
            time_stop_date=time_stop_date or entry_date,
            narrative_cluster=narrative_cluster,
            classification=classification,
        )
    )
    db.commit()
    return RedirectResponse(f"/positions?added={asset}" + (f"&warning={warning.reason}" if warning else ""), status_code=303)


@app.get("/contributions")
def contributions_page(request: Request, db: Session = Depends(get_db)):
    snapshot, _, _ = _context(db)
    total = snapshot.total_value
    core_value = sum(p.value for p in snapshot.positions if p.asset in ("BTC", "ETH"))
    gap = max(0.0, 0.5 * total - core_value)
    return templates.TemplateResponse(
        request,
        "contributions.html",
        {
            "active": "contributions",
            "monthly": CONTRIBUTION_MONTHLY_AUD,
            "core_gap": gap,
            "months_to_close_gap": (gap / (CONTRIBUTION_MONTHLY_AUD)) if gap > 0 else 0,
        },
    )


@app.get("/legacy")
def legacy_page(request: Request, db: Session = Depends(get_db)):
    snapshot, _, _ = _context(db)
    return templates.TemplateResponse(request, "legacy.html", {"active": "legacy", "positions": snapshot.legacy()})


@app.get("/journal")
def journal_page(request: Request, db: Session = Depends(get_db)):
    entries = db.execute(select(JournalEntry).order_by(JournalEntry.created_at.desc())).scalars().all()
    return templates.TemplateResponse(request, "journal.html", {"active": "journal", "entries": entries})


@app.post("/journal")
def journal_add(request: Request, db: Session = Depends(get_db), entry_text: str = Form(...), asset: str = Form("")):
    db.add(JournalEntry(entry_text=entry_text, asset=asset or None))
    db.commit()
    return RedirectResponse("/journal", status_code=303)


@app.get("/system")
def system_page(request: Request, db: Session = Depends(get_db)):
    events = db.execute(select(SystemEvent).order_by(SystemEvent.created_at.desc())).scalars().all()
    per_venue = {}
    for e in events:
        if e.venue not in per_venue:
            per_venue[e.venue] = e  # most recent first
    return templates.TemplateResponse(
        request, "system.html", {"active": "system", "per_venue": per_venue, "now": datetime.utcnow()}
    )


@app.post("/system/sync")
def trigger_sync(db: Session = Depends(get_db)):
    sync_all(db, get_adapters())
    return RedirectResponse("/system", status_code=303)


# --- JSON API (thin views over the same service layer) ---


@app.get("/api/overview")
def api_overview(db: Session = Depends(get_db)):
    snapshot, results, breaches = _context(db)
    return {
        "total_value": snapshot.total_value,
        "cash_total": snapshot.cash_total,
        "breach_count": len([r for r in breaches if r.status == "breach"]),
        "warning_count": len([r for r in breaches if r.status == "warning"]),
    }


@app.get("/api/breaches")
def api_breaches(db: Session = Depends(get_db)):
    _, _, breaches = _context(db)
    return [r.__dict__ for r in breaches]


@app.get("/api/positions")
def api_positions(db: Session = Depends(get_db)):
    snapshot, _, _ = _context(db)
    return [
        {"asset": p.asset, "quantity": p.quantity, "price": p.price, "value": p.value, "venues": p.venues}
        for p in snapshot.positions
    ]
