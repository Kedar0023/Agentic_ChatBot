from datetime import datetime

from sqlalchemy.orm import Session

from app.models.user import RefreshToken


class RefreshTokenRepo:
    """Repository encapsulating all RefreshToken database operations."""

    @staticmethod
    def create(db: Session, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        rf = RefreshToken(user_id=user_id, token=token_hash, expires_at=expires_at)
        db.add(rf)
        return rf

    @staticmethod
    def get_by_user_and_hash(db: Session, user_id: int, token_hash: str) -> RefreshToken | None:
        return (
            db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.token == token_hash)
            .first()
        )

    @staticmethod
    def get_active_token_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == token_hash,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
            .first()
        )

    @staticmethod
    def revoke(db: Session, rf_token: RefreshToken) -> None:
        rf_token.is_revoked = True
