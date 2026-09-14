from collections import defaultdict, deque
from datetime import date
from time import monotonic

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .dependencies import get_current_owner
from .models import GalleryItem, Owner, QueueEntry, QueueStatus, Service
from .notifications import send_near_turn_notifications
from .schemas import GalleryCreate, GalleryResponse, LoginRequest, QueueJoinRequest, QueueResponse, QueueStatusResponse, ServiceCreate, ServiceResponse, TokenResponse
from .security import create_access_token, create_queue_status_token, decode_queue_status_token, verify_password

settings = get_settings()
app = FastAPI(
    title="Shiva's Salon API",
    version="1.0.0",
    description="Queue and salon management API",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

LOGIN_WINDOW_SECONDS = 60
LOGIN_MAX_ATTEMPTS = 5
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def queue_response(entry: QueueEntry) -> QueueResponse:
    return QueueResponse(
        id=entry.id,
        token_number=entry.token_number,
        customer_name=entry.customer_name,
        phone=entry.phone,
        service_id=entry.service_id,
        service_name=entry.service.name,
        status=entry.status,
        joined_at=entry.joined_at,
        status_token=create_queue_status_token(entry.id),
    )


def notify_near_turn(db: Session) -> None:
    send_near_turn_notifications(db, settings)


def check_login_rate_limit(client_key: str) -> None:
    now = monotonic()
    attempts = _login_attempts[client_key]
    while attempts and now - attempts[0] >= LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again in a minute.")
    attempts.append(now)


def clear_login_rate_limit(client_key: str) -> None:
    _login_attempts.pop(client_key, None)


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_key = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_key)
    owner = db.scalar(select(Owner).where(Owner.username == payload.username, Owner.is_active.is_(True)))
    if not owner or not verify_password(payload.password, owner.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    clear_login_rate_limit(client_key)
    return TokenResponse(access_token=create_access_token(owner.username))


@app.get("/api/services", response_model=list[ServiceResponse])
def services(db: Session = Depends(get_db)):
    return list(db.scalars(select(Service).where(Service.is_active.is_(True)).order_by(Service.id)))


@app.post("/api/queue/join", response_model=QueueResponse)
def join_queue(payload: QueueJoinRequest, db: Session = Depends(get_db)):
    service = db.get(Service, payload.service_id)
    if not service or not service.is_active:
        raise HTTPException(status_code=404, detail="Service not available")
    name, phone = payload.customer_name.strip(), payload.phone.strip()
    if not name or not phone:
        raise HTTPException(status_code=422, detail="Name and phone are required")
    db.execute(text("SELECT pg_advisory_xact_lock(90210)"))
    last_token = db.scalar(select(func.max(QueueEntry.token_number)).where(func.date(QueueEntry.joined_at) == date.today())) or 0
    entry = QueueEntry(token_number=last_token + 1, customer_name=name, phone=phone, service_id=service.id, status=QueueStatus.WAITING)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    notify_near_turn(db)
    return queue_response(entry)


@app.get("/api/queue/status/{status_token}", response_model=QueueStatusResponse)
def queue_status(status_token: str, db: Session = Depends(get_db)):
    entry_id = decode_queue_status_token(status_token)
    if not entry_id:
        raise HTTPException(status_code=404, detail="Queue status link is invalid or expired")
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return QueueStatusResponse(id=entry.id, token_number=entry.token_number, service_name=entry.service.name, status=entry.status, joined_at=entry.joined_at)


@app.get("/api/gallery", response_model=list[GalleryResponse])
def gallery(db: Session = Depends(get_db)):
    return list(db.scalars(select(GalleryItem).where(GalleryItem.is_active.is_(True)).order_by(GalleryItem.id.desc())))


@app.get("/api/admin/queue", response_model=list[QueueResponse])
def admin_queue(_: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    entries = db.scalars(select(QueueEntry).where(QueueEntry.status.in_([QueueStatus.WAITING, QueueStatus.SERVING])).order_by(QueueEntry.token_number)).all()
    return [queue_response(entry) for entry in entries]


@app.post("/api/admin/queue/next", response_model=QueueResponse)
def call_next(_: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    if db.scalar(select(QueueEntry).where(QueueEntry.status == QueueStatus.SERVING)):
        raise HTTPException(status_code=409, detail="A customer is already being served")
    entry = db.scalar(select(QueueEntry).where(QueueEntry.status == QueueStatus.WAITING).order_by(QueueEntry.token_number))
    if not entry:
        raise HTTPException(status_code=404, detail="No waiting customers")
    entry.status = QueueStatus.SERVING
    db.commit(); db.refresh(entry)
    notify_near_turn(db)
    return queue_response(entry)


@app.post("/api/admin/queue/{entry_id}/complete", response_model=QueueResponse)
def complete_queue(entry_id: int, _: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry.status != QueueStatus.SERVING:
        raise HTTPException(status_code=409, detail="Only a serving customer can be completed")
    entry.status = QueueStatus.COMPLETED
    db.commit(); db.refresh(entry)
    notify_near_turn(db)
    return queue_response(entry)


@app.post("/api/admin/queue/{entry_id}/cancel", response_model=QueueResponse)
def cancel_queue(entry_id: int, _: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry.status in (QueueStatus.COMPLETED, QueueStatus.CANCELLED):
        raise HTTPException(status_code=409, detail="Queue entry is already closed")
    entry.status = QueueStatus.CANCELLED
    db.commit(); db.refresh(entry)
    notify_near_turn(db)
    return queue_response(entry)


@app.post("/api/admin/services", response_model=ServiceResponse, status_code=201)
def create_service(payload: ServiceCreate, _: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    if db.scalar(select(Service).where(func.lower(Service.name) == payload.name.strip().lower())):
        raise HTTPException(status_code=409, detail="Service already exists")
    service = Service(name=payload.name.strip(), duration_minutes=payload.duration_minutes, description=payload.description)
    db.add(service); db.commit(); db.refresh(service)
    return service


@app.patch("/api/admin/services/{service_id}", response_model=ServiceResponse)
def update_service(service_id: int, payload: ServiceCreate, _: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    service.name, service.duration_minutes, service.description = payload.name.strip(), payload.duration_minutes, payload.description
    db.commit(); db.refresh(service)
    return service


@app.delete("/api/admin/services/{service_id}", status_code=204)
def deactivate_service(service_id: int, _: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    service.is_active = False
    db.commit()


@app.post("/api/admin/gallery", response_model=GalleryResponse, status_code=201)
def create_gallery(payload: GalleryCreate, _: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    item = GalleryItem(title=payload.title.strip(), image_url=payload.image_url.strip(), description=payload.description)
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.delete("/api/admin/gallery/{item_id}", status_code=204)
def deactivate_gallery(item_id: int, _: Owner = Depends(get_current_owner), db: Session = Depends(get_db)):
    item = db.get(GalleryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Gallery item not found")
    item.is_active = False
    db.commit()
