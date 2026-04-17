import random

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from db import get_db
from models import QuizAnswer, QuizCard, QuizResult, QuizStart, QuizWordStat

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


async def _get_deck_or_404(deck_id: int, user_id: int, db):
    async with db.execute(
        "SELECT * FROM decks WHERE id = ? AND user_id = ?", (deck_id, user_id)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deck not found")
    return row


async def _get_word_for_user(word_id: int, user_id: int, db):
    async with db.execute(
        """
        SELECT w.* FROM words w
        JOIN decks d ON d.id = w.deck_id
        WHERE w.id = ? AND d.user_id = ?
        """,
        (word_id, user_id),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Word not found")
    return row


@router.post("/start")
async def start_quiz(
    body: QuizStart,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_deck_or_404(body.deck_id, current_user["id"], db)
    async with db.execute(
        """
        SELECT id, term FROM words
        WHERE deck_id = ?
        ORDER BY times_correct ASC
        LIMIT ?
        """,
        (body.deck_id, body.count),
    ) as cur:
        rows = await cur.fetchall()
    cards = [
        QuizCard(card_id=r["id"], prompt=r["term"], direction="term_to_translation").model_dump()
        for r in rows
    ]
    random.shuffle(cards)
    return {"data": cards, "error": None}


@router.post("/answer")
async def answer_quiz(
    body: QuizAnswer,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    word = await _get_word_for_user(body.word_id, current_user["id"], db)
    correct = body.answer.strip().lower() == word["translation"].strip().lower()

    if correct:
        new_times_correct = word["times_correct"] + 1
        mastered = 1 if new_times_correct >= 5 else word["mastered"]
        await db.execute(
            "UPDATE words SET times_correct = ?, mastered = ? WHERE id = ?",
            (new_times_correct, mastered, body.word_id),
        )
    else:
        await db.execute(
            "UPDATE words SET times_wrong = times_wrong + 1, mastered = 0 WHERE id = ?",
            (body.word_id,),
        )

    await db.execute(
        "INSERT INTO quiz_attempts (user_id, word_id, correct) VALUES (?, ?, ?)",
        (current_user["id"], body.word_id, 1 if correct else 0),
    )
    await db.commit()

    return {
        "data": QuizResult(
            correct=correct,
            expected=word["translation"],
            word_id=body.word_id,
        ).model_dump(),
        "error": None,
    }


@router.get("/results/{deck_id}")
async def quiz_results(
    deck_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_deck_or_404(deck_id, current_user["id"], db)
    async with db.execute(
        "SELECT id, term, translation, times_correct, times_wrong, mastered FROM words WHERE deck_id = ? ORDER BY term ASC",
        (deck_id,),
    ) as cur:
        rows = await cur.fetchall()
    data = [
        QuizWordStat(
            word_id=r["id"],
            term=r["term"],
            translation=r["translation"],
            times_correct=r["times_correct"],
            times_wrong=r["times_wrong"],
            mastered=bool(r["mastered"]),
        ).model_dump()
        for r in rows
    ]
    return {"data": data, "error": None}
