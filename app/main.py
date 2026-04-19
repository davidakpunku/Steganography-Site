from __future__ import annotations

import os
import sys
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .auth import get_user_by_username, hash_password, verify_password
from .db import Base, engine, get_db
from .models import Post, User
from .stego import StegoError, embed_payload_into_carrier, extract_payload_from_carrier

# Add this for better module resolution on Azure / deployment platforms
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

MEDIA_DIR = BASE_DIR / "media"
SECRETS_DIR = BASE_DIR / "secrets"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
SECRETS_DIR.mkdir(parents=True, exist_ok=True)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Steganography Site")


app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SECRET_KEY",
        "10_Y3AgNu9H8DGb-I8wPvxcER25P6GXSk0v_C3SoPD3dOJTgzcYFFDAEq9qvkH6j4lctZyN_TEIZ_YdBz0q2gw"
    ),
)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def current_user(request: Request) -> Optional[str]:
    return request.session.get("user")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.is_public == True).order_by(Post.id.desc()).all()  # noqa: E712
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "posts": posts,
            "user": current_user(request),
        },
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "user": current_user(request),
            "error": None,
        },
    )


@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()

    if len(username) < 3 or len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "user": current_user(request),
                "error": "Username must be at least 3 characters and password at least 6 characters.",
            },
        )

    if get_user_by_username(db, username):
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "user": current_user(request),
                "error": "That username already exists.",
            },
        )

    db.add(User(username=username, password_hash=hash_password(password)))
    db.commit()
    request.session["user"] = username
    return RedirectResponse(url="/upload", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "user": current_user(request),
            "error": None,
        },
    )


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user_by_username(db, username.strip())

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "user": current_user(request),
                "error": "Invalid username or password.",
            },
        )

    request.session["user"] = user.username
    return RedirectResponse(url="/upload", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "user": current_user(request),
            "error": None,
            "success": None,
        },
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload_post(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    start_bit: int = Form(...),
    interval_l: int = Form(...),
    mode: str = Form(...),
    carrier_file: UploadFile = File(...),
    message_text: str = Form(""),
    secret_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    username = current_user(request)
    if not username:
        return RedirectResponse(url="/login", status_code=303)

    try:
        carrier_bytes = await carrier_file.read()
        if not carrier_bytes:
            raise StegoError("Carrier file cannot be empty.")

        if secret_file and secret_file.filename:
            secret_bytes = await secret_file.read()
            secret_name = secret_file.filename
        elif message_text:
            secret_bytes = message_text.encode("utf-8")
            secret_name = "message.txt"
        else:
            raise StegoError("Provide either a text message or a secret file to hide.")

        stego_bytes = embed_payload_into_carrier(
            carrier=carrier_bytes,
            secret=secret_bytes,
            start_bit=start_bit,
            base_l=interval_l,
            mode=mode,
            secret_name=secret_name,
        )

        unique_name = secrets.token_hex(12) + ".png"
        output_path = MEDIA_DIR / unique_name
        output_path.write_bytes(stego_bytes)

        post = Post(
            title=title.strip() or "Untitled Post",
            description=description,
            carrier_original_name=carrier_file.filename or "carrier_image.png",
            stego_filename=unique_name,
            mime_type="image/png",
            start_bit=start_bit,
            interval_l=interval_l,
            mode=mode,
            created_by=username,
            is_public=True,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "user": username,
                "error": None,
                "success": "Post created successfully. Public file id: {}".format(post.id),
            },
        )

    except StegoError as exc:
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "user": username,
                "error": str(exc),
                "success": None,
            },
        )


@app.get("/post/{post_id}", response_class=HTMLResponse)
def view_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return templates.TemplateResponse(
        "post.html",
        {
            "request": request,
            "post": post,
            "user": current_user(request),
            "is_image": True,
        },
    )


@app.get("/download/post/{post_id}")
def download_post_file(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    path = MEDIA_DIR / post.stego_filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=path,
        filename=post.stego_filename,
        media_type="application/octet-stream",
    )


@app.get("/extract", response_class=HTMLResponse)
def extract_page(request: Request):
    if not current_user(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "extract.html",
        {
            "request": request,
            "user": current_user(request),
            "error": None,
            "result": None,
        },
    )


@app.post("/extract", response_class=HTMLResponse)
async def extract_message(
    request: Request,
    stego_file: UploadFile = File(...),
    start_bit: int = Form(...),
    interval_l: int = Form(...),
    mode: str = Form(...),
):
    username = current_user(request)
    if not username:
        return RedirectResponse(url="/login", status_code=303)

    try:
        carrier_bytes = await stego_file.read()
        name, secret = extract_payload_from_carrier(
            carrier=carrier_bytes,
            start_bit=start_bit,
            base_l=interval_l,
            mode=mode,
        )

        download_name = "extracted_{}".format(name)
        download_path = SECRETS_DIR / download_name
        download_path.write_bytes(secret)

        try:
            preview = secret.decode("utf-8")
        except UnicodeDecodeError:
            preview = "Binary file extracted ({} bytes). Download it below.".format(len(secret))

        return templates.TemplateResponse(
            "extract.html",
            {
                "request": request,
                "user": username,
                "error": None,
                "result": {
                    "name": download_name,
                    "preview": preview,
                },
            },
        )

    except StegoError as exc:
        return templates.TemplateResponse(
            "extract.html",
            {
                "request": request,
                "user": username,
                "error": str(exc),
                "result": None,
            },
        )


@app.get("/download/secret/{filename}")
def download_secret(filename: str):
    path = SECRETS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Secret file not found")
    return FileResponse(path, filename=filename)