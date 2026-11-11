"""user-service (port 8001) - accounts, login (JWT) and profiles.
Owns its own database: data/users.db
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
import time

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
DB_PATH = os.getenv("DB_PATH", "data/users.db")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

app = FastAPI(title="User Service", description="Registration, login and profiles")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with db() as c:
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        bio TEXT DEFAULT '',
        created REAL NOT NULL)"""
    )


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, _ = stored.split("$")
    return hmac.compare_digest(hash_password(password, salt), stored)


def make_token(user) -> str:
    payload = {"sub": str(user["id"]), "username": user["username"], "exp": int(time.time()) + 86400}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        return jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")


def public(row) -> dict:
    return {"id": row["id"], "username": row["username"], "email": row["email"], "bio": row["bio"]}


class Register(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: str
    password: str = Field(min_length=6)


class Login(BaseModel):
    username: str
    password: str


class ProfileUpdate(BaseModel):
    email: str | None = None
    bio: str | None = Field(default=None, max_length=300)


@app.get("/health")
def health():
    return {"service": "user-service", "status": "ok"}


@app.post("/auth/register", status_code=201)
def register(body: Register):
    username = body.username.lower()
    try:
        with db() as c:
            cur = c.execute(
                "INSERT INTO users (username, email, password_hash, created) VALUES (?,?,?,?)",
                (username, body.email, hash_password(body.password), time.time()),
            )
            row = c.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username already taken")
    return {"user": public(row), "token": make_token(row)}


@app.post("/auth/login")
def login(body: Login):
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE username=?", (body.username.lower(),)).fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    return {"user": public(row), "token": make_token(row)}


@app.get("/users")
def list_users():
    with db() as c:
        return [public(r) for r in c.execute("SELECT * FROM users ORDER BY id")]


@app.get("/users/me")
def me(user=Depends(current_user)):
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (int(user["sub"]),)).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return public(row)


@app.put("/users/me")
def update_me(body: ProfileUpdate, user=Depends(current_user)):
    with db() as c:
        if body.email is not None:
            c.execute("UPDATE users SET email=? WHERE id=?", (body.email, int(user["sub"])))
        if body.bio is not None:
            c.execute("UPDATE users SET bio=? WHERE id=?", (body.bio, int(user["sub"])))
        row = c.execute("SELECT * FROM users WHERE id=?", (int(user["sub"]),)).fetchone()
    return public(row)


@app.get("/users/{user_id}")
def get_user(user_id: int):
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return public(row)
