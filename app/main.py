from datetime import datetime, timezone

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from . import cache, db
from .sessions import MAX_SECONDS, SessionError, classify, duration, rank, split_across_days

app = FastAPI(title="study-leaderboard")


@app.get("/health")
def health():
    out = {"status": "ok", "postgres": False, "redis": False}
    try:
        db.query("SELECT 1")
        out["postgres"] = True
    except Exception as e:
        out["pg_error"] = str(e)
    try:
        cache.client().ping()
        out["redis"] = True
    except Exception as e:
        out["redis_error"] = str(e)
    return out if out["postgres"] and out["redis"] else JSONResponse(out, status_code=503)


@app.post("/sessions/start", status_code=201)
def start(payload: dict = Body(...)):
    student = str(payload.get("student", "")).strip()
    subject = str(payload.get("subject", "")).strip() or "General"
    if not student:
        raise HTTPException(400, "student is required")
    if cache.get_json(f"live:{student}"):
        raise HTTPException(409, "that student already has a timer running")
    now = datetime.now(timezone.utc)
    cache.set_json(f"live:{student}", {"subject": subject, "started": now.isoformat()},
                   ttl=MAX_SECONDS + 600)
    return {"student": student, "subject": subject, "started": now.isoformat()}


@app.post("/sessions/stop")
def stop(payload: dict = Body(...)):
    student = str(payload.get("student", "")).strip()
    live = cache.get_json(f"live:{student}")
    if not live:
        raise HTTPException(404, "no timer running for that student")
    started = datetime.fromisoformat(live["started"])
    now = datetime.now(timezone.utc)
    try:
        secs = duration(started, now)
    except SessionError as e:
        raise HTTPException(400, str(e))
    verdict, credited = classify(secs)
    cache.drop(f"live:{student}")
    if verdict == "discard":
        return {"student": student, "verdict": verdict, "seconds": secs, "credited": 0}

    for day, part in split_across_days(started, now):
        if part <= 0:
            continue
        share = int(part * credited / secs) if secs else part
        db.query("INSERT INTO sessions (student, subject, day, seconds) VALUES (%s,%s,%s,%s)",
                 (student, live["subject"], day, share), fetch=False)
    cache.client().zincrby("board:all", credited, student)
    cache.drop_prefix("board:week")
    return {"student": student, "verdict": verdict, "seconds": secs, "credited": credited}


@app.get("/leaderboard")
def leaderboard(period: str = "week"):
    where = "day >= CURRENT_DATE - 7" if period == "week" else "TRUE"
    rows = db.query(f"SELECT student, sum(seconds) AS secs FROM sessions"
                    f" WHERE {where} GROUP BY student")
    return {"period": period,
            "leaderboard": rank({r["student"]: int(r["secs"]) for r in rows})}


@app.get("/students/{name}")
def student(name: str):
    rows = db.query("SELECT subject, sum(seconds) AS secs FROM sessions"
                    " WHERE student=%s GROUP BY subject ORDER BY secs DESC", (name,))
    if not rows:
        raise HTTPException(404, "no sessions for that student")
    return {"student": name, "by_subject": rows,
            "total_seconds": sum(int(r["secs"]) for r in rows),
            "running": bool(cache.get_json(f"live:{name}"))}
