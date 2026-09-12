import os

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Owner, Service
from app.security import hash_password


DEFAULT_SERVICES = [
    ("Haircut", 30, "Classic haircut and finishing"),
    ("Beard", 15, "Beard trim and styling"),
    ("Massage", 45, "Relaxing full-service massage"),
    ("Facial", 40, "Cleansing and facial care"),
]


def main() -> None:
    username = os.getenv("OWNER_USERNAME")
    password = os.getenv("OWNER_PASSWORD")
    if not username or not password:
        raise SystemExit("Set OWNER_USERNAME and OWNER_PASSWORD before running the seed script.")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.scalar(select(Owner).where(Owner.username == username)):
            db.add(Owner(username=username, password_hash=hash_password(password)))
        for name, duration, description in DEFAULT_SERVICES:
            if not db.scalar(select(Service).where(Service.name == name)):
                db.add(Service(name=name, duration_minutes=duration, description=description))
        db.commit()
        print(f"Owner '{username}' and default services are ready.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
