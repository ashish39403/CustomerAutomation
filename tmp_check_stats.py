from sqlalchemy import text

from app.db.session import SessionLocal

with SessionLocal() as db:
    print("by internal status:", db.execute(text("select status, count(*) from tickets group by status order by 2 desc")).all())
    print("total:", db.execute(text("select count(*) from tickets")).scalar())
    print(
        "today_total (created today UTC):",
        db.execute(
            text(
                "select count(*) from tickets "
                "where created_at >= date_trunc('day', now() at time zone 'utc')"
            )
        ).scalar(),
    )
    print("min/max created_at:", db.execute(text("select min(created_at), max(created_at) from tickets")).all())
