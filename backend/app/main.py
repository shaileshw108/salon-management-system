from fastapi import FastAPI, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from fastapi import Depends

from .config import get_settings
from .database import Base, engine, get_db
from .models import GalleryItem, QueueEntry, QueueStatus, Service
from .schemas import GalleryCreate, GalleryResponse, QueueJoinRequest, QueueResponse, ServiceCreate, ServiceResponse

settings = get_settings()
app = FastAPI(title="Shiva's Salon API", version="0.1.0")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}

@app.get("/api/services", response_model=list[ServiceResponse])
def services(db: Session = Depends(get_db)):
    return list(db.scalars(select(Service).where(Service.is_active.is_(True)).order_by(Service.id)))

@app.post("/api/queue/join", response_model=QueueResponse)
def join_queue(payload: QueueJoinRequest, db: Session = Depends(get_db)):
    service = db.get(Service, payload.service_id)
    if not service or not service.is_active:
        raise HTTPException(404, "Service not available")
    db.execute(text("SELECT pg_advisory_xact_lock(90210)"))
    last_token = db.scalar(select(func.max(QueueEntry.token_number))) or 0
    entry = QueueEntry(token_number=last_token + 1, customer_name=payload.customer_name.strip(), phone=payload.phone.strip(), service_id=service.id, status=QueueStatus.WAITING)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return QueueResponse(id=entry.id, token_number=entry.token_number, customer_name=entry.customer_name, phone=entry.phone, service_id=entry.service_id, service_name=service.name, status=entry.status, joined_at=entry.joined_at)

@app.get("/api/queue/{entry_id}", response_model=QueueResponse)
def queue_status(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Queue entry not found")
    return QueueResponse(id=entry.id, token_number=entry.token_number, customer_name=entry.customer_name, phone=entry.phone, service_id=entry.service_id, service_name=entry.service.name, status=entry.status, joined_at=entry.joined_at)

@app.get("/api/gallery", response_model=list[GalleryResponse])
def gallery(db: Session = Depends(get_db)):
    return list(db.scalars(select(GalleryItem).where(GalleryItem.is_active.is_(True)).order_by(GalleryItem.id.desc())))

@app.post("/api/gallery", response_model=GalleryResponse)
def create_gallery(payload: GalleryCreate, db: Session = Depends(get_db)):
    item = GalleryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
