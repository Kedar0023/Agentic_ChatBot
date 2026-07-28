from sqlalchemy.orm import Session

from app.models.chats import Thread
from app.models.user import User


class UserStore:
    """Repository encapsulating all User database operations."""

    # staticmethod allows to use this fn without instantiating the class
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User | None:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def user_exists(db: Session, username: str) -> bool:
        return UserStore.get_user_by_username(db, username) is not None

    @staticmethod
    def create_user(db: Session, username: str, hashed_password: str) -> User:
        user = User(
            username=username,
            password=hashed_password,
        )

        db.add(user)
        return user

    @staticmethod
    def get_all_thread_titles(db: Session, user_id: int) -> list[dict[str, str]]:
        rows = (
            db.query(Thread.id, Thread.title)
            .filter(
                Thread.user_id == user_id,
                Thread.title.isnot(None),
            )
            .order_by(Thread.updated_at.desc())
            .all()
        )

        return [
            {
                "id": str(thread_id),
                "title": title,
            }
            for thread_id, title in rows
            if title
        ]
