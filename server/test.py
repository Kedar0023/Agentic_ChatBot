"""
Unit test suite for all API endpoints in TheChatBot backend.
Covers Authentication, Session Management, Chat Threads, Streaming Chat, and Document endpoints.
"""

import io
import sys
import unittest
import uuid
from unittest.mock import MagicMock, patch

# Dynamic module aliasing to resolve legacy import paths in codebase without modifying existing files
import app.types as types

sys.modules["app.types"] = types
sys.modules["app.types"] = types
sys.modules["app.types"] = types

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.sqltypes import Uuid

# Patch Uuid.bind_processor for SQLite string to UUID parameter compatibility
orig_bind_processor = Uuid.bind_processor


def patched_bind_processor(self, dialect):
    proc = orig_bind_processor(self, dialect)

    def process(value):
        if isinstance(value, str):
            try:
                value = uuid.UUID(value)
            except ValueError:
                pass
        if proc:
            return proc(value)
        return value

    return process


Uuid.bind_processor = patched_bind_processor

from app.database.db import Base, get_async_db_session, get_db
from app.index import app
from app.models.chats import MessageRole, MessageStatus, Thread
from app.models.document import Document, DocumentStatus
from app.models.user import User

# SQLite in-memory setup for unit tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class MockAsyncSessionContext:
    def __init__(self, sync_session):
        self.sync_session = sync_session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def merge(self, obj):
        return self.sync_session.merge(obj)

    async def commit(self):
        self.sync_session.commit()

    async def rollback(self):
        self.sync_session.rollback()


def override_get_async_db_session():
    def _maker():
        return MockAsyncSessionContext(TestingSessionLocal())

    return _maker


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_async_db_session] = override_get_async_db_session


class BaseAPITestCase(unittest.TestCase):
    """Base class providing database reset and client initialization."""

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    def register_and_login(self, username="testuser", password="password123"):
        """Helper to create a user and get access token and refresh cookie."""
        self.client.post("/v2/auth/register", json={"username": username, "password": password})
        res = self.client.post("/v2/auth/login", json={"username": username, "password": password})
        data = res.json()
        token = data.get("access_token")
        cookie = res.cookies.get("refresh_token")
        return token, cookie, data.get("userId")


class AuthAPITestCase(BaseAPITestCase):
    """Tests for /v2/auth endpoints."""

    def test_register_success(self):
        response = self.client.post(
            "/v2/auth/register",
            json={"username": "newuser", "password": "securepassword"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("userId", response.json())
        self.assertEqual(response.json()["message"], "User registered successfully")

    def test_register_duplicate_username(self):
        self.client.post("/v2/auth/register", json={"username": "existinguser", "password": "password123"})
        response = self.client.post(
            "/v2/auth/register",
            json={"username": "existinguser", "password": "password123"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Username already exists", response.json()["detail"])

    def test_login_success(self):
        self.client.post("/v2/auth/register", json={"username": "loginuser", "password": "loginpassword"})
        response = self.client.post(
            "/v2/auth/login",
            json={"username": "loginuser", "password": "loginpassword"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["username"], "loginuser")
        self.assertIn("refresh_token", response.cookies)

    def test_login_invalid_credentials(self):
        self.client.post("/v2/auth/register", json={"username": "validuser", "password": "correctpassword"})
        response = self.client.post(
            "/v2/auth/login",
            json={"username": "validuser", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_success(self):
        _, cookie, _ = self.register_and_login("logoutuser", "password123")
        self.client.cookies.set("refresh_token", cookie)
        response = self.client.post("/v2/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "User logged out successfully")

    def test_logout_missing_cookie(self):
        response = self.client.post("/v2/auth/logout")
        self.assertEqual(response.status_code, 401)


class SessionAPITestCase(BaseAPITestCase):
    """Tests for /v2/session endpoints."""

    def test_refresh_token_success(self):
        _, cookie, _ = self.register_and_login("refreshuser", "password123")
        self.client.cookies.set("refresh_token", cookie)
        response = self.client.post("/v2/session/refresh")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", response.cookies)

    def test_refresh_token_missing_cookie(self):
        response = self.client.post("/v2/session/refresh")
        self.assertEqual(response.status_code, 401)

    def test_get_me_success(self):
        token, _, user_id = self.register_and_login("profileuser", "password123")
        response = self.client.get(
            "/v2/session/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "profileuser")
        self.assertEqual(data["userId"], str(user_id))

    def test_get_me_unauthorized(self):
        response = self.client.get("/v2/session/me")
        self.assertEqual(response.status_code, 401)


class ThreadAPITestCase(BaseAPITestCase):
    """Tests for /v2/thread endpoints."""

    def test_create_thread_success(self):
        token, _, _ = self.register_and_login("threaduser", "password123")
        response = self.client.post(
            "/v2/thread/create",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("thread_id", response.json())

    def test_create_thread_unauthorized(self):
        response = self.client.post("/v2/thread/create")
        self.assertEqual(response.status_code, 401)

    def test_list_threads_success(self):
        token, _, _ = self.register_and_login("listuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        # Give thread a title so it appears in UserStore.get_all_thread_titles
        self.client.patch(
            f"/v2/thread/{thread_id}/title",
            json={"title": "Test Thread Title"},
            headers={"Authorization": f"Bearer {token}"},
        )

        response = self.client.get(
            "/v2/thread/list_threads",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], "Test Thread Title")

    def test_get_thread_messages_success(self):
        token, _, _ = self.register_and_login("msguser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        response = self.client.get(
            f"/v2/thread/{thread_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("messages", response.json())

    def test_get_thread_messages_forbidden(self):
        token1, _, _ = self.register_and_login("user1", "password123")
        token2, _, _ = self.register_and_login("user2", "password123")

        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token1}"})
        thread_id = res.json()["thread_id"]

        response = self.client.get(
            f"/v2/thread/{thread_id}/messages",
            headers={"Authorization": f"Bearer {token2}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_get_thread_models_success(self):
        token, _, _ = self.register_and_login("modeluser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        response = self.client.get(
            f"/v2/thread/{thread_id}/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("current_model", data)
        self.assertIn("models", data)

    def test_update_thread_model_success(self):
        token, _, _ = self.register_and_login("updatemodeluser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        response = self.client.patch(
            f"/v2/thread/{thread_id}/model",
            json={"model": "qwen2.5:1.5b"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "qwen2.5:1.5b")

    def test_update_thread_model_invalid(self):
        token, _, _ = self.register_and_login("invalidmodeluser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        response = self.client.patch(
            f"/v2/thread/{thread_id}/model",
            json={"model": "non-existent-model"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_update_thread_title_success(self):
        token, _, _ = self.register_and_login("titleuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        response = self.client.patch(
            f"/v2/thread/{thread_id}/title",
            json={"title": "New Thread Title"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "New Thread Title")

    def test_delete_thread_success(self):
        token, _, _ = self.register_and_login("deluser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        response = self.client.delete(
            f"/v2/thread/{thread_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Thread deleted successfully")


class ChatAPITestCase(BaseAPITestCase):
    """Tests for /v2/chat streaming endpoints."""

    @patch("app.routes.chat.ChatEngine.stream")
    def test_anonymous_chat_success(self, mock_stream):
        async def mock_generator(*args, **kwargs):
            yield {"type": "ai", "content": "Hello World"}

        mock_stream.side_effect = mock_generator

        response = self.client.post(
            "/v2/chat/anonymous",
            json={"prompt": "Hello", "history": []},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])

    def test_anonymous_chat_limit_exceeded(self):
        history = [{"role": "human", "content": f"msg {i}"} for i in range(20)]
        response = self.client.post(
            "/v2/chat/anonymous",
            json={"prompt": "Hello", "history": history},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Free credits limit reached", response.json()["detail"])

    @patch("app.routes.chat.ChatEngine.stream")
    def test_authenticated_chat_success(self, mock_stream):
        async def mock_generator(*args, **kwargs):
            yield {"type": "ai", "content": "AI response chunk"}

        mock_stream.side_effect = mock_generator

        token, _, _ = self.register_and_login("chatuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        response = self.client.post(
            f"/v2/chat/{thread_id}",
            json={"prompt": "Hi AI"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])

    def test_authenticated_chat_forbidden(self):
        token1, _, _ = self.register_and_login("chatuser1", "password123")
        token2, _, _ = self.register_and_login("chatuser2", "password123")

        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token1}"})
        thread_id = res.json()["thread_id"]

        response = self.client.post(
            f"/v2/chat/{thread_id}",
            json={"prompt": "Hi AI"},
            headers={"Authorization": f"Bearer {token2}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_stop_chat_success(self):
        token, _, _ = self.register_and_login("stopuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        response = self.client.post(
            f"/v2/chat/{thread_id}/stop",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Chat generation stopped successfully.")
        self.assertEqual(response.json()["thread_id"], thread_id)

    def test_stop_chat_forbidden(self):
        token1, _, _ = self.register_and_login("stopuser1", "password123")
        token2, _, _ = self.register_and_login("stopuser2", "password123")

        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token1}"})
        thread_id = res.json()["thread_id"]

        response = self.client.post(
            f"/v2/chat/{thread_id}/stop",
            headers={"Authorization": f"Bearer {token2}"},
        )
        self.assertEqual(response.status_code, 403)


class DocumentAPITestCase(BaseAPITestCase):

    """Tests for /v2/thread/{thread_id}/upload, download, and ingest endpoints."""

    @patch("app.routes.docs.upload_file")
    def test_upload_document_success(self, mock_upload):
        mock_upload.return_value = None

        token, _, _ = self.register_and_login("docuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        file_content = b"%PDF-1.4 dummy pdf content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

        response = self.client.post(
            f"/v2/thread/{thread_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "Document uploaded successfully.")

    def test_upload_document_unsupported_type(self):
        token, _, _ = self.register_and_login("docuser2", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        files = {"file": ("script.exe", io.BytesIO(b"binary data"), "application/x-msdownload")}
        response = self.client.post(
            f"/v2/thread/{thread_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_document_empty_file(self):
        token, _, _ = self.register_and_login("docuser3", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        response = self.client.post(
            f"/v2/thread/{thread_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)

    @patch("app.routes.docs.get_downloadable_file")
    @patch("app.routes.docs.upload_file")
    def test_get_document_success(self, mock_upload, mock_download):
        mock_upload.return_value = None
        mock_download.return_value = {
            "Body": io.BytesIO(b"%PDF-1.4 mock content"),
            "ContentType": "application/pdf",
            "ContentLength": 21,
        }

        token, _, _ = self.register_and_login("downdocuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        # Upload first
        files = {"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")}
        self.client.post(
            f"/v2/thread/{thread_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Retrieve doc_id from DB
        db = TestingSessionLocal()
        doc = db.query(Document).first()
        doc_id = str(doc.id)
        db.close()

        response = self.client.get(
            f"/v2/thread/{thread_id}/docs/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_get_document_not_found(self):
        token, _, _ = self.register_and_login("notfounduser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        fake_doc_id = "00000000-0000-0000-0000-000000000000"
        response = self.client.get(
            f"/v2/thread/{thread_id}/docs/{fake_doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 404)

    @patch("app.routes.docs.get_vector_store")
    @patch("app.routes.docs.RAGWorkflow")
    @patch("app.routes.docs.get_downloadable_file")
    @patch("app.routes.docs.upload_file")
    def test_ingest_document_success(self, mock_upload, mock_download, mock_rag, mock_vector_store):
        mock_upload.return_value = None
        mock_download.return_value = {
            "Body": io.BytesIO(b"%PDF-1.4 mock pdf content"),
            "ContentType": "application/pdf",
        }

        # Mock RAG pipeline
        mock_chunk = MagicMock()
        mock_chunk.page_content = "Chunk 1 content"
        mock_chunk.metadata = {"page": 1}
        mock_rag.load_pdf_from_bytes.return_value = ["Page 1"]
        mock_rag.split_into_chunks.return_value = [mock_chunk]
        mock_rag.embed_chunks.return_value = [[0.1, 0.2, 0.3]]

        mock_vs = MagicMock()
        mock_vector_store.return_value = mock_vs

        token, _, _ = self.register_and_login("ingestuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        files = {"file": ("sample.pdf", io.BytesIO(b"%PDF-1.4 data"), "application/pdf")}
        self.client.post(
            f"/v2/thread/{thread_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        db = TestingSessionLocal()
        doc = db.query(Document).first()
        doc_id = str(doc.id)
        db.close()

        response = self.client.post(
            f"/v2/thread/{thread_id}/docs/{doc_id}/ingest",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Document processed successfully.")
        self.assertEqual(data["document"]["status"], DocumentStatus.COMPLETED.value)

    @patch("app.routes.docs.upload_file")
    def test_ingest_document_non_pdf(self, mock_upload):
        mock_upload.return_value = None
        token, _, _ = self.register_and_login("ingesttxtuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        files = {"file": ("sample.txt", io.BytesIO(b"plain text data"), "text/plain")}
        self.client.post(
            f"/v2/thread/{thread_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        db = TestingSessionLocal()
        doc = db.query(Document).first()
        doc_id = str(doc.id)
        db.close()

        response = self.client.post(
            f"/v2/thread/{thread_id}/docs/{doc_id}/ingest",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only PDF documents can be processed", response.json()["detail"])

    @patch("app.routes.docs.upload_file")
    def test_get_all_documents_success(self, mock_upload):
        mock_upload.return_value = None
        token, _, _ = self.register_and_login("getalldocsuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        files = {"file": ("sample.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")}
        self.client.post(
            f"/v2/thread/{thread_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        response = self.client.get(
            f"/v2/thread/{thread_id}/docs",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("documents", data)
        self.assertEqual(len(data["documents"]), 1)
        self.assertEqual(data["documents"][0]["filename"], "sample.pdf")

    def test_get_all_documents_forbidden(self):
        token1, _, _ = self.register_and_login("docowner1", "password123")
        token2, _, _ = self.register_and_login("docowner2", "password123")

        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token1}"})
        thread_id = res.json()["thread_id"]

        response = self.client.get(
            f"/v2/thread/{thread_id}/docs",
            headers={"Authorization": f"Bearer {token2}"},
        )
        self.assertEqual(response.status_code, 403)

    @patch("app.routes.docs.delete_file")
    @patch("app.routes.docs.get_vector_store")
    @patch("app.routes.docs.upload_file")
    def test_delete_document_success(self, mock_upload, mock_vector_store, mock_delete_file):
        mock_upload.return_value = None
        mock_delete_file.return_value = None
        mock_vs = MagicMock()
        mock_vector_store.return_value = mock_vs

        token, _, _ = self.register_and_login("deldocuser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        files = {"file": ("file_to_del.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")}
        self.client.post(
            f"/v2/thread/{thread_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        db = TestingSessionLocal()
        doc = db.query(Document).first()
        doc_id = str(doc.id)
        db.close()

        response = self.client.delete(
            f"/v2/thread/{thread_id}/docs/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Document deleted successfully.")

        db = TestingSessionLocal()
        deleted_doc = db.query(Document).filter(Document.id == doc_id).first()
        self.assertIsNone(deleted_doc)
        db.close()

    def test_delete_document_not_found(self):
        token, _, _ = self.register_and_login("delnotfounduser", "password123")
        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token}"})
        thread_id = res.json()["thread_id"]

        fake_doc_id = "00000000-0000-0000-0000-000000000000"
        response = self.client.delete(
            f"/v2/thread/{thread_id}/docs/{fake_doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_document_forbidden(self):
        token1, _, _ = self.register_and_login("delforbid1", "password123")
        token2, _, _ = self.register_and_login("delforbid2", "password123")

        res = self.client.post("/v2/thread/create", headers={"Authorization": f"Bearer {token1}"})
        thread_id = res.json()["thread_id"]

        fake_doc_id = "00000000-0000-0000-0000-000000000000"
        response = self.client.delete(
            f"/v2/thread/{thread_id}/docs/{fake_doc_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()

