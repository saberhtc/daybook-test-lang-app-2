from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from db import get_db
from models import DeckCreate, DeckResponse, WordCreate, WordResponse, WordUpdate

router = APIRouter(prefix="/api/decks", tags=["words"])


async def _get_deck_or_404(deck_id: int, user_id: int, db):
    async with db.execute(
        "SELECT * FROM decks WHERE id = ? AND user_id = ?", (deck_id, user_id)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deck not found")
    return row


@router.post("")
async def create_deck(
    body: DeckCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    async with db.execute(
        "INSERT INTO decks (user_id, name, source_lang, target_lang) VALUES (?, ?, ?, ?)",
        (current_user["id"], body.name, body.source_lang, body.target_lang),
    ) as cur:
        deck_id = cur.lastrowid
    await db.commit()
    async with db.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)) as cur:
        row = await cur.fetchone()
    return {
        "data": DeckResponse(
            id=row["id"],
            name=row["name"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
            word_count=0,
            created_at=row["created_at"],
        ).model_dump(),
        "error": None,
    }


@router.get("")
async def list_decks(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    async with db.execute(
        """
        SELECT d.*, COUNT(w.id) AS word_count
        FROM decks d
        LEFT JOIN words w ON w.deck_id = d.id
        WHERE d.user_id = ?
        GROUP BY d.id
        ORDER BY d.created_at DESC
        """,
        (current_user["id"],),
    ) as cur:
        rows = await cur.fetchall()
    data = [
        DeckResponse(
            id=r["id"],
            name=r["name"],
            source_lang=r["source_lang"],
            target_lang=r["target_lang"],
            word_count=r["word_count"],
            created_at=r["created_at"],
        ).model_dump()
        for r in rows
    ]
    return {"data": data, "error": None}


@router.get("/{deck_id}")
async def get_deck(
    deck_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    async with db.execute(
        """
        SELECT d.*, COUNT(w.id) AS word_count
        FROM decks d
        LEFT JOIN words w ON w.deck_id = d.id
        WHERE d.id = ? AND d.user_id = ?
        GROUP BY d.id
        """,
        (deck_id, current_user["id"]),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deck not found")
    return {
        "data": DeckResponse(
            id=row["id"],
            name=row["name"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
            word_count=row["word_count"],
            created_at=row["created_at"],
        ).model_dump(),
        "error": None,
    }


@router.delete("/{deck_id}")
async def delete_deck(
    deck_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_deck_or_404(deck_id, current_user["id"], db)
    await db.execute("DELETE FROM words WHERE deck_id = ?", (deck_id,))
    await db.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
    await db.commit()
    return {"data": {"deleted": True}, "error": None}


@router.post("/{deck_id}/words")
async def add_word(
    deck_id: int,
    body: WordCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_deck_or_404(deck_id, current_user["id"], db)
    async with db.execute(
        "SELECT id FROM words WHERE deck_id = ? AND term = ?", (deck_id, body.term)
    ) as cur:
        existing = await cur.fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Term already exists in this deck")
    async with db.execute(
        "INSERT INTO words (deck_id, term, translation) VALUES (?, ?, ?)",
        (deck_id, body.term, body.translation),
    ) as cur:
        word_id = cur.lastrowid
    await db.commit()
    async with db.execute("SELECT * FROM words WHERE id = ?", (word_id,)) as cur:
        row = await cur.fetchone()
    return {"data": _word_dict(row), "error": None}


@router.get("/{deck_id}/words")
async def list_words(
    deck_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_deck_or_404(deck_id, current_user["id"], db)
    async with db.execute(
        "SELECT * FROM words WHERE deck_id = ? ORDER BY created_at ASC", (deck_id,)
    ) as cur:
        rows = await cur.fetchall()
    return {"data": [_word_dict(r) for r in rows], "error": None}


@router.put("/{deck_id}/words/{word_id}")
async def update_word(
    deck_id: int,
    word_id: int,
    body: WordUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_deck_or_404(deck_id, current_user["id"], db)
    async with db.execute(
        "SELECT * FROM words WHERE id = ? AND deck_id = ?", (word_id, deck_id)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Word not found")

    new_term = body.term if body.term is not None else row["term"]
    new_translation = body.translation if body.translation is not None else row["translation"]

    if body.term is not None and body.term != row["term"]:
        async with db.execute(
            "SELECT id FROM words WHERE deck_id = ? AND term = ? AND id != ?",
            (deck_id, body.term, word_id),
        ) as cur:
            conflict = await cur.fetchone()
        if conflict:
            raise HTTPException(status_code=409, detail="Term already exists in this deck")

    await db.execute(
        "UPDATE words SET term = ?, translation = ? WHERE id = ?",
        (new_term, new_translation, word_id),
    )
    await db.commit()
    async with db.execute("SELECT * FROM words WHERE id = ?", (word_id,)) as cur:
        updated = await cur.fetchone()
    return {"data": _word_dict(updated), "error": None}


@router.delete("/{deck_id}/words/{word_id}")
async def delete_word(
    deck_id: int,
    word_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    await _get_deck_or_404(deck_id, current_user["id"], db)
    async with db.execute(
        "SELECT id FROM words WHERE id = ? AND deck_id = ?", (word_id, deck_id)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Word not found")
    await db.execute("DELETE FROM words WHERE id = ?", (word_id,))
    await db.commit()
    return {"data": {"deleted": True}, "error": None}


def _word_dict(row) -> dict:
    return WordResponse(
        id=row["id"],
        term=row["term"],
        translation=row["translation"],
        times_correct=row["times_correct"],
        times_wrong=row["times_wrong"],
        mastered=bool(row["mastered"]),
        created_at=row["created_at"],
    ).model_dump()
