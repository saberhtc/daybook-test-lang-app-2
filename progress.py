from datetime import date, timedelta

from fastapi import APIRouter, Depends

from auth import get_current_user
from db import get_db
from models import DailyActivity, ProgressStats

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    user_id = current_user["id"]

    async with db.execute(
        "SELECT COUNT(*) FROM words w JOIN decks d ON d.id = w.deck_id WHERE d.user_id = ?",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
    total_words = row[0]

    async with db.execute(
        "SELECT COUNT(*) FROM words w JOIN decks d ON d.id = w.deck_id WHERE d.user_id = ? AND w.mastered = 1",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
    mastered_words = row[0]

    async with db.execute(
        "SELECT COUNT(*), SUM(correct) FROM quiz_attempts WHERE user_id = ?",
        (user_id,),
    ) as cur:
        row = await cur.fetchone()
    total_quizzes = row[0] or 0
    total_correct = row[1] or 0
    overall_accuracy_pct = round((total_correct / total_quizzes) * 100, 1) if total_quizzes > 0 else 0.0

    async with db.execute(
        "SELECT date FROM daily_streaks WHERE user_id = ? ORDER BY date DESC",
        (user_id,),
    ) as cur:
        streak_rows = await cur.fetchall()

    active_dates = {r[0] for r in streak_rows}

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    current_streak = 0
    if today in active_dates:
        check = date.today()
    elif yesterday in active_dates:
        check = date.today() - timedelta(days=1)
    else:
        check = None

    if check:
        while check.isoformat() in active_dates:
            current_streak += 1
            check -= timedelta(days=1)

    if not active_dates:
        longest_streak = 0
    else:
        sorted_dates = sorted(active_dates)
        longest_streak = 1
        current_run = 1
        for i in range(1, len(sorted_dates)):
            prev = date.fromisoformat(sorted_dates[i - 1])
            curr = date.fromisoformat(sorted_dates[i])
            if (curr - prev).days == 1:
                current_run += 1
                if current_run > longest_streak:
                    longest_streak = current_run
            else:
                current_run = 1

    return {
        "data": ProgressStats(
            total_words=total_words,
            mastered_words=mastered_words,
            total_quizzes=total_quizzes,
            overall_accuracy_pct=overall_accuracy_pct,
            current_streak_days=current_streak,
            longest_streak_days=longest_streak,
        ).model_dump(),
        "error": None,
    }


@router.get("/history")
async def get_history(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    user_id = current_user["id"]
    today = date.today()
    since = (today - timedelta(days=29)).isoformat()

    async with db.execute(
        "SELECT date, quizzes_completed, correct_count, total_count FROM daily_streaks WHERE user_id = ? AND date >= ?",
        (user_id, since),
    ) as cur:
        rows = await cur.fetchall()

    activity_map = {r["date"]: r for r in rows}

    result = []
    for i in range(29, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        if d in activity_map:
            r = activity_map[d]
            total = r["total_count"]
            correct = r["correct_count"]
            accuracy = round((correct / total) * 100, 1) if total > 0 else 0.0
            result.append(
                DailyActivity(
                    date=d,
                    quizzes_completed=r["quizzes_completed"],
                    correct_count=correct,
                    total_count=total,
                    accuracy_pct=accuracy,
                ).model_dump()
            )
        else:
            result.append(
                DailyActivity(
                    date=d,
                    quizzes_completed=0,
                    correct_count=0,
                    total_count=0,
                    accuracy_pct=0.0,
                ).model_dump()
            )

    return {"data": result, "error": None}
