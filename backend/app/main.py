from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import AuditEvent, User
from .schemas import AuditResponse, LoginRequest, RoleUpdate, TokenResponse, UserResponse
from .security import create_token, current_user, hash_password, require_role, verify_password

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gatehouse IAM API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def audit(db: Session, actor: User | None, event_type: str, target: str, detail: str):
    db.add(AuditEvent(
        actor_user_id=actor.id if actor else None,
        event_type=event_type,
        target=target,
        detail=detail,
    ))
    db.commit()


def seed_demo_users():
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)):
            return
        demos = [
            ("user@example.com", "User123!", "user"),
            ("analyst@example.com", "Analyst123!", "analyst"),
            ("admin@example.com", "Admin123!", "admin"),
        ]
        for email, password, role in demos:
            db.add(User(email=email, password_hash=hash_password(password), role=role))
        db.commit()
    finally:
        db.close()


seed_demo_users()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "gatehouse-iam"}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        audit(db, None, "login_failed", payload.email, "Invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.active:
        raise HTTPException(status_code=403, detail="Account disabled")
    audit(db, user, "login_success", user.email, f"Authenticated as {user.role}")
    return TokenResponse(access_token=create_token(user))


@app.get("/api/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/security/overview")
def security_overview(user: User = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    users = db.scalars(select(User)).all()
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(20)).all()
    return {
        "viewer_role": user.role,
        "active_users": sum(1 for item in users if item.active),
        "admins": sum(1 for item in users if item.role == "admin"),
        "recent_security_events": len(events),
    }


@app.get("/api/admin/users", response_model=list[UserResponse])
def admin_users(_: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@app.patch("/api/admin/users/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: int,
    payload: RoleUpdate,
    actor: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if payload.role not in {"user", "analyst", "admin"}:
        raise HTTPException(status_code=400, detail="Unknown role")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    previous = target.role
    target.role = payload.role
    db.commit()
    db.refresh(target)
    audit(db, actor, "role_changed", target.email, f"Role changed from {previous} to {target.role}")
    return target


@app.get("/api/audit", response_model=list[AuditResponse])
def audit_log(_: User = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    return db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100)).all()
