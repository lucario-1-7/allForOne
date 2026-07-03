"""All API routes: auth, profile/interests, follow search, and the feed."""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import feed as feed_service
from .adapters import anilist, tvmaze
from .adapters.football_data import FREE_COMPETITIONS
from .db import Follow, Interest, User, get_session
from .security import create_token, hash_password, verify_password, verify_token

router = APIRouter(prefix="/api")

VALID_DOMAINS = {"tech", "sports", "games", "screen"}


# --- auth -------------------------------------------------------------------

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_session)) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    user_id = verify_token(token) if token else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user


@router.post("/auth/register")
def register(creds: Credentials, db: Session = Depends(get_session)):
    email = creds.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(creds.password))
    db.add(user)
    db.commit()
    return {"token": create_token(user.id), "email": user.email, "onboarded": False}


@router.post("/auth/login")
def login(creds: Credentials, db: Session = Depends(get_session)):
    user = db.scalar(select(User).where(User.email == creds.email.lower()))
    if user is None or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    return {"token": create_token(user.id), "email": user.email, "onboarded": len(user.interests) > 0}


# --- profile / interests ----------------------------------------------------

class InterestsPayload(BaseModel):
    domains: dict[str, dict] = Field(default_factory=dict)  # domain -> config


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {
        "email": user.email,
        "domains": {i.domain: i.config for i in user.interests},
        "follows": [{"id": f.id, "kind": f.kind, "external_id": f.external_id, "title": f.title}
                    for f in user.follows],
        "leagues": FREE_COMPETITIONS,
    }


@router.put("/me/interests")
def set_interests(payload: InterestsPayload, user: User = Depends(current_user),
                  db: Session = Depends(get_session)):
    unknown = set(payload.domains) - VALID_DOMAINS
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown domains: {', '.join(sorted(unknown))}")
    for existing in list(user.interests):
        db.delete(existing)
    for domain, config in payload.domains.items():
        db.add(Interest(user_id=user.id, domain=domain, config=config or {}))
    db.commit()
    return {"ok": True}


# --- follows ----------------------------------------------------------------

class FollowPayload(BaseModel):
    kind: str = Field(pattern="^(tv|anime)$")
    external_id: str
    title: str


@router.get("/search")
async def search(kind: str, q: str, user: User = Depends(current_user)):
    q = q.strip()
    if len(q) < 2:
        return {"results": []}
    if kind == "tv":
        return {"results": await tvmaze.search_shows(q)}
    if kind == "anime":
        return {"results": await anilist.search_anime(q)}
    raise HTTPException(status_code=422, detail="kind must be tv or anime")


@router.post("/me/follows")
def add_follow(payload: FollowPayload, user: User = Depends(current_user),
               db: Session = Depends(get_session)):
    exists = any(f.kind == payload.kind and f.external_id == payload.external_id for f in user.follows)
    if not exists:
        db.add(Follow(user_id=user.id, kind=payload.kind,
                      external_id=payload.external_id, title=payload.title))
        db.commit()
    return {"ok": True}


@router.delete("/me/follows/{follow_id}")
def remove_follow(follow_id: int, user: User = Depends(current_user),
                  db: Session = Depends(get_session)):
    follow = db.get(Follow, follow_id)
    if follow is None or follow.user_id != user.id:
        raise HTTPException(status_code=404, detail="Follow not found")
    db.delete(follow)
    db.commit()
    return {"ok": True}


# --- feed -------------------------------------------------------------------

@router.get("/feed")
async def get_feed(user: User = Depends(current_user)):
    return await feed_service.build_feed(user.interests, user.follows)
