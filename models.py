from typing import Optional

from pydantic import BaseModel


class UserRegister(BaseModel):
    email: str
    password: str
    name: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: int
    email: str
    display_name: str
    created_at: str


class DeckCreate(BaseModel):
    name: str
    source_lang: str
    target_lang: str


class DeckResponse(BaseModel):
    id: int
    name: str
    source_lang: str
    target_lang: str
    word_count: int
    created_at: str


class WordCreate(BaseModel):
    term: str
    translation: str


class WordUpdate(BaseModel):
    term: Optional[str] = None
    translation: Optional[str] = None


class WordResponse(BaseModel):
    id: int
    term: str
    translation: str
    times_correct: int
    times_wrong: int
    mastered: bool
    created_at: str
