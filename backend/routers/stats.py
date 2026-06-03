import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from database import get_db
from routers.transactions import verify_api_key

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/monthly")
async def monthly_stats(
    year: str = None,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    if year:
        rows = await db.execute_fetchall("""
            SELECT strftime('%Y-%m', trans_date) as month,
                   SUM(amount) as total,
                   COUNT(*) as count
            FROM transactions
            WHERE strftime('%Y', trans_date) = ? AND user_id = ?
            GROUP BY month
            ORDER BY month ASC
        """, [year, auth["user_id"]])
    else:
        rows = await db.execute_fetchall("""
            SELECT strftime('%Y-%m', trans_date) as month,
                   SUM(amount) as total,
                   COUNT(*) as count
            FROM transactions
            WHERE user_id = ?
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """, [auth["user_id"]])
    return {"success": True, "data": [dict(r) for r in rows]}


@router.get("/category")
async def category_stats(
    month: str = None,
    year: str = None,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    if month:
        rows = await db.execute_fetchall("""
            SELECT t.category,
                   SUM(t.amount) as total,
                   c.icon,
                   c.color
            FROM transactions t
            LEFT JOIN categories c ON t.category = c.name AND c.user_id = ?
            WHERE strftime('%Y-%m', t.trans_date) = ? AND t.user_id = ?
            GROUP BY t.category
            ORDER BY total DESC
        """, [auth["user_id"], month, auth["user_id"]])
    elif year:
        rows = await db.execute_fetchall("""
            SELECT t.category,
                   SUM(t.amount) as total,
                   c.icon,
                   c.color
            FROM transactions t
            LEFT JOIN categories c ON t.category = c.name AND c.user_id = ?
            WHERE strftime('%Y', t.trans_date) = ? AND t.user_id = ?
            GROUP BY t.category
            ORDER BY total DESC
        """, [auth["user_id"], year, auth["user_id"]])
    else:
        rows = await db.execute_fetchall("""
            SELECT t.category,
                   SUM(t.amount) as total,
                   c.icon,
                   c.color
            FROM transactions t
            LEFT JOIN categories c ON t.category = c.name AND c.user_id = ?
            WHERE strftime('%Y-%m', t.trans_date) = strftime('%Y-%m', 'now') AND t.user_id = ?
            GROUP BY t.category
            ORDER BY total DESC
        """, [auth["user_id"], auth["user_id"]])

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
    auth=Depends(verify_api_key),
):
    rows = await db.execute_fetchall("""
        SELECT strftime('%Y-%m', trans_date) as month,
               SUM(amount) as total,
               COUNT(*) as count
        FROM transactions
        WHERE trans_date >= date('now', '-6 months') AND user_id = ?
        GROUP BY month
        ORDER BY month ASC
    """, [auth["user_id"]])
    return {"success": True, "data": [dict(r) for r in rows]}


@router.get("/export/csv")
async def export_csv(
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    rows = await db.execute_fetchall("""
        SELECT trans_date, category, item_name, amount, currency, notes
        FROM transactions
        WHERE user_id = ?
        ORDER BY trans_date DESC
    """, [auth["user_id"]])

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


@router.get("/daily")
async def daily_stats(
    month: str = None,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    """每日支出数据，用于热力图。month 格式 YYYY-MM"""
    if not month:
        month_query = "strftime('%Y-%m', 'now')"
        params = []
    else:
        month_query = "?"
        params = [month]

    rows = await db.execute_fetchall(
        f"""SELECT date(trans_date) as day, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE strftime('%Y-%m', trans_date) = {month_query} AND user_id = ?
            GROUP BY day
            ORDER BY day""",
        params + [auth["user_id"]],
    )
    return {"success": True, "data": [dict(r) for r in rows]}


@router.get("/ranking")
async def ranking_stats(
    period: str = "month",
    limit: int = 5,
    year: str = None,
    month: str = None,
    db=Depends(get_db),
    auth=Depends(verify_api_key),
):
    """支出排行：按分类和按商家"""
    if month:
        date_filter = "strftime('%Y-%m', trans_date) = ?"
        date_param = [month]
    elif year:
        date_filter = "strftime('%Y', trans_date) = ?"
        date_param = [year]
    elif period == "week":
        date_filter = "trans_date >= date('now', '-7 days')"
        date_param = []
    elif period == "year":
        date_filter = "trans_date >= date('now', '-1 year')"
        date_param = []
    else:
        date_filter = "strftime('%Y-%m', trans_date) = strftime('%Y-%m', 'now')"
        date_param = []

    # 按分类排行
    cat_rows = await db.execute_fetchall(
        f"""SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM transactions WHERE {date_filter} AND user_id = ?
            GROUP BY category ORDER BY total DESC LIMIT ?""",
        date_param + [auth["user_id"], limit],
    )

    # 按商家排行
    item_rows = await db.execute_fetchall(
        f"""SELECT item_name, SUM(amount) as total, COUNT(*) as count
            FROM transactions WHERE {date_filter} AND user_id = ?
            GROUP BY item_name ORDER BY total DESC LIMIT ?""",
        date_param + [auth["user_id"], limit],
    )

    return {
        "success": True,
        "data": {
            "by_category": [dict(r) for r in cat_rows],
            "by_item": [dict(r) for r in item_rows],
        },
    }
