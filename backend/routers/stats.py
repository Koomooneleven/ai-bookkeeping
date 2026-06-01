import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from database import get_db
from routers.transactions import verify_api_key

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/monthly")
async def monthly_stats(
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    rows = await db.execute_fetchall("""
        SELECT strftime('%Y-%m', trans_date) as month,
               SUM(amount) as total,
               COUNT(*) as count
        FROM transactions
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """)
    return {"success": True, "data": [dict(r) for r in rows]}


@router.get("/category")
async def category_stats(
    month: str = None,
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    if month:
        rows = await db.execute_fetchall("""
            SELECT t.category,
                   SUM(t.amount) as total,
                   c.icon,
                   c.color
            FROM transactions t
            LEFT JOIN categories c ON t.category = c.name
            WHERE strftime('%Y-%m', t.trans_date) = ?
            GROUP BY t.category
            ORDER BY total DESC
        """, [month])
    else:
        rows = await db.execute_fetchall("""
            SELECT t.category,
                   SUM(t.amount) as total,
                   c.icon,
                   c.color
            FROM transactions t
            LEFT JOIN categories c ON t.category = c.name
            WHERE strftime('%Y-%m', t.trans_date) = strftime('%Y-%m', 'now')
            GROUP BY t.category
            ORDER BY total DESC
        """)

    grand_total = sum(r["total"] for r in rows) or 1
    data = [
        {
            "category": r["category"],
            "total": r["total"],
            "percentage": round(r["total"] / grand_total * 100, 1),
            "icon": r["icon"] or "📌",
            "color": r["color"] or "#CCCCCC",
        }
        for r in rows
    ]
    return {"success": True, "data": data}


@router.get("/trend")
async def trend_stats(
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    rows = await db.execute_fetchall("""
        SELECT strftime('%Y-%m', trans_date) as month,
               SUM(amount) as total,
               COUNT(*) as count
        FROM transactions
        WHERE trans_date >= date('now', '-6 months')
        GROUP BY month
        ORDER BY month ASC
    """)
    return {"success": True, "data": [dict(r) for r in rows]}


@router.get("/export/csv")
async def export_csv(
    db=Depends(get_db),
    _=Depends(verify_api_key),
):
    rows = await db.execute_fetchall("""
        SELECT trans_date, category, item_name, amount, currency, notes
        FROM transactions
        ORDER BY trans_date DESC
    """)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日期", "分类", "名称", "金额", "货币", "备注"])
    for r in rows:
        writer.writerow([r["trans_date"], r["category"], r["item_name"], r["amount"], r["currency"], r["notes"]])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=accounting_export.csv"},
    )
