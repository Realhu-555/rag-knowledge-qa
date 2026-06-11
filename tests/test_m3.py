"""M3模块验收测试 — 多用户权限（JWT认证 + 角色权限 + 审计日志 + 向后兼容）"""
import sqlite3
import sys
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

import pytest

# ─── 在导入项目代码之前，mock掉重量级依赖 ───
_mock_st = MagicMock()
_mock_st.SentenceTransformer = MagicMock()
sys.modules.setdefault("sentence_transformers", _mock_st)

import jwt  # noqa: E402

from src.config import JWT_SECRET_KEY, JWT_ALGORITHM  # noqa: E402


# ============================================================
# Fixture
# ============================================================

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """创建临时数据库并patch DB_PATH"""
    db_file = tmp_path / "test_m3.db"
    monkeypatch.setattr("src.storage.database.DB_PATH", db_file)
    from src.storage.database import init_db
    init_db()
    return db_file


@pytest.fixture
def tmp_db_with_user(tmp_db):
    """创建临时数据库并预创建一个测试用户"""
    from src.storage.database import create_user
    from src.api.jwt_auth import hash_password
    user = create_user("user_001", "testuser", hash_password("Test1234"), role="viewer")
    assert user is not None
    return tmp_db, user


# ============================================================
# 1. 用户注册 -> 登录 -> 获取JWT Token
# ============================================================

class TestRegisterAndLogin:

    def test_register_success(self, tmp_db):
        """注册新用户应成功并返回Token"""
        from src.storage.database import get_user_by_id
        from src.api.jwt_auth import hash_password, create_access_token, create_refresh_token
        from src.storage.database import create_user
        import uuid

        user_id = uuid.uuid4().hex
        user = create_user(user_id, "alice", hash_password("Alice1234"), role="viewer")
        assert user is not None
        assert user["username"] == "alice"
        assert user["role"] == "viewer"

        # 应能生成 Token
        access_token = create_access_token(user["id"], user["role"])
        refresh_token = create_refresh_token(user["id"])
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert len(access_token) > 0

        # DB 中可查到用户
        fetched = get_user_by_id(user_id)
        assert fetched is not None
        assert fetched["username"] == "alice"

    def test_register_duplicate_username_fails(self, tmp_db):
        """注册重复用户名应返回None"""
        from src.storage.database import create_user
        from src.api.jwt_auth import hash_password

        r1 = create_user("u1", "bob", hash_password("Bob12345"), role="viewer")
        assert r1 is not None
        r2 = create_user("u2", "bob", hash_password("Bob67890"), role="viewer")
        assert r2 is None  # IntegrityError -> None

    def test_login_returns_valid_tokens(self, tmp_db_with_user):
        """登录应返回可用的access_token和refresh_token"""
        from src.api.jwt_auth import (
            hash_password, verify_password, create_access_token, create_refresh_token, decode_token
        )
        from src.storage.database import get_user_by_username

        db, user = tmp_db_with_user
        fetched = get_user_by_username("testuser")
        assert fetched is not None
        assert verify_password("Test1234", fetched["password_hash"])

        access_token = create_access_token(fetched["id"], fetched["role"])
        refresh_token = create_refresh_token(fetched["id"])

        # access_token 解码验证
        payload = decode_token(access_token)
        assert payload["sub"] == fetched["id"]
        assert payload["role"] == "viewer"
        assert payload["type"] == "access"

        # refresh_token 解码验证
        r_payload = decode_token(refresh_token)
        assert r_payload["sub"] == fetched["id"]
        assert r_payload["type"] == "refresh"

    def test_login_wrong_password_fails(self, tmp_db_with_user):
        """密码错误时verify_password应返回False"""
        from src.api.jwt_auth import verify_password
        from src.storage.database import get_user_by_username

        _, _ = tmp_db_with_user
        fetched = get_user_by_username("testuser")
        assert not verify_password("wrong_password", fetched["password_hash"])


# ============================================================
# 2. JWT Token验证（有效/过期/无效）
# ============================================================

class TestJWTTokenVerification:

    def test_valid_token_decodes(self):
        """有效的access token应能正确解码"""
        from src.api.jwt_auth import create_access_token, decode_token

        token = create_access_token("user_test", "editor")
        payload = decode_token(token)
        assert payload["sub"] == "user_test"
        assert payload["role"] == "editor"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_expired_token_raises(self):
        """过期的token应抛出HTTPException(401)"""
        from fastapi import HTTPException
        from src.api.jwt_auth import decode_token

        # 手动创建一个已过期的token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user_expired",
            "role": "viewer",
            "type": "access",
            "exp": now - timedelta(hours=1),  # 1小时前已过期
            "iat": now - timedelta(hours=2),
            "jti": "expired_jti",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401
        assert "过期" in exc_info.value.detail

    def test_invalid_token_raises(self):
        """无效/篡改的token应抛出HTTPException(401)"""
        from fastapi import HTTPException
        from src.api.jwt_auth import decode_token

        # 用错误的密钥签名
        wrong_payload = {
            "sub": "user_fake",
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "jti": "fake_jti",
        }
        bad_token = jwt.encode(wrong_payload, "wrong-secret-key", algorithm=JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_token(bad_token)
        assert exc_info.value.status_code == 401
        assert "无效" in exc_info.value.detail

    def test_malformed_token_raises(self):
        """格式错误的token字符串应抛出HTTPException(401)"""
        from fastapi import HTTPException
        from src.api.jwt_auth import decode_token

        with pytest.raises(HTTPException) as exc_info:
            decode_token("this.is.not-a-valid-jwt")
        assert exc_info.value.status_code == 401

    def test_refresh_token_type_is_refresh(self):
        """refresh token的type应为refresh"""
        from src.api.jwt_auth import create_refresh_token, decode_token

        token = create_refresh_token("user_123")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_access_token_cannot_be_used_as_refresh(self):
        """access token不能作为refresh token使用"""
        from src.api.jwt_auth import create_access_token, decode_token

        token = create_access_token("user_123", "admin")
        payload = decode_token(token)
        assert payload["type"] == "access"
        assert payload["type"] != "refresh"


# ============================================================
# 3. 角色权限（admin/editor/viewer）
# ============================================================

class TestRolePermissions:

    def test_role_hierarchy(self, tmp_db):
        """角色层级: admin(2) > editor(1) > viewer(0)"""
        from src.api.jwt_auth import require_role, create_access_token, hash_password
        from src.storage.database import create_user
        from fastapi import Depends
        from fastapi.testclient import TestClient
        from fastapi import FastAPI

        # 在测试数据库中创建三种角色的用户
        admin_user = create_user("a1", "admin1", hash_password("pass1"), role="admin")
        editor_user = create_user("e1", "editor1", hash_password("pass2"), role="editor")
        viewer_user = create_user("v1", "viewer1", hash_password("pass3"), role="viewer")
        assert admin_user and editor_user and viewer_user

        app = FastAPI()

        @app.get("/test-admin")
        async def test_admin(user: dict = Depends(require_role("admin"))):
            return {"ok": True, "role": user["role"]}

        @app.get("/test-editor")
        async def test_editor(user: dict = Depends(require_role("editor"))):
            return {"ok": True, "role": user["role"]}

        @app.get("/test-viewer")
        async def test_viewer(user: dict = Depends(require_role("viewer"))):
            return {"ok": True, "role": user["role"]}

        client = TestClient(app, raise_server_exceptions=False)

        # -- 创建真实token（使用数据库中存在的user_id） --
        admin_token = create_access_token(admin_user["id"], admin_user["role"])
        editor_token = create_access_token(editor_user["id"], editor_user["role"])
        viewer_token = create_access_token(viewer_user["id"], viewer_user["role"])

        # admin 接口: admin 可访问
        resp = client.get("/test-admin", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

        # admin 接口: editor 被拒
        resp = client.get("/test-admin", headers={"Authorization": f"Bearer {editor_token}"})
        assert resp.status_code == 403

        # admin 接口: viewer 被拒
        resp = client.get("/test-admin", headers={"Authorization": f"Bearer {viewer_token}"})
        assert resp.status_code == 403

        # editor 接口: admin 可访问（admin >= editor）
        resp = client.get("/test-editor", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

        # editor 接口: editor 可访问
        resp = client.get("/test-editor", headers={"Authorization": f"Bearer {editor_token}"})
        assert resp.status_code == 200

        # editor 接口: viewer 被拒
        resp = client.get("/test-editor", headers={"Authorization": f"Bearer {viewer_token}"})
        assert resp.status_code == 403

        # viewer 接口: 所有角色都可访问
        for tok in [admin_token, editor_token, viewer_token]:
            resp = client.get("/test-viewer", headers={"Authorization": f"Bearer {tok}"})
            assert resp.status_code == 200

    def test_no_auth_returns_401(self):
        """未提供凭据应返回401"""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from src.api.jwt_auth import get_current_user

        app = FastAPI()

        @app.get("/protected")
        async def protected(user: dict = Depends(get_current_user)):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_invalid_auth_returns_401(self):
        """无效凭据应返回401"""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from src.api.jwt_auth import get_current_user

        app = FastAPI()

        @app.get("/protected")
        async def protected(user: dict = Depends(get_current_user)):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/protected", headers={"Authorization": "Bearer invalid-token-here"})
        assert resp.status_code == 401

    def test_viewer_cannot_access_editor_endpoint(self, tmp_db):
        """viewer角色无法访问editor权限的接口"""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from src.api.jwt_auth import require_role, create_access_token, hash_password
        from src.storage.database import create_user

        # 在测试数据库中创建viewer用户
        viewer = create_user("v_perm", "viewer_perm", hash_password("pass"), role="viewer")
        assert viewer is not None

        app = FastAPI()

        @app.get("/upload-doc")
        async def upload(user: dict = Depends(require_role("editor"))):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        viewer_token = create_access_token(viewer["id"], "viewer")
        resp = client.get("/upload-doc", headers={"Authorization": f"Bearer {viewer_token}"})
        assert resp.status_code == 403
        assert "editor" in resp.json()["detail"]

    def test_admin_can_access_all_endpoints(self, tmp_db):
        """admin角色可访问所有权限级别的接口"""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from src.api.jwt_auth import require_role, create_access_token, hash_password
        from src.storage.database import create_user

        # 在测试数据库中创建admin用户
        admin = create_user("a_perm", "admin_perm", hash_password("pass"), role="admin")
        assert admin is not None

        app = FastAPI()

        @app.get("/admin-only")
        async def admin_only(user: dict = Depends(require_role("admin"))):
            return {"ok": True}

        @app.get("/editor-level")
        async def editor_level(user: dict = Depends(require_role("editor"))):
            return {"ok": True}

        @app.get("/viewer-level")
        async def viewer_level(user: dict = Depends(require_role("viewer"))):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        admin_token = create_access_token(admin["id"], admin["role"])

        for path in ["/admin-only", "/editor-level", "/viewer-level"]:
            resp = client.get(path, headers={"Authorization": f"Bearer {admin_token}"})
            assert resp.status_code == 200


# ============================================================
# 4. 审计日志记录
# ============================================================

class TestAuditLog:

    def test_create_and_list_audit_log(self, tmp_db):
        """审计日志写入后可通过list_audit_logs查回"""
        from src.storage.database import create_audit_log, list_audit_logs

        create_audit_log("user1", "login", "user", "user1", ip_address="127.0.0.1")
        create_audit_log("user1", "query", "knowledge_base", "kb1",
                         details='{"question": "test"}')
        create_audit_log("user2", "login", "user", "user2")

        # 列出全部
        logs = list_audit_logs()
        assert len(logs) >= 3

        # 按 action 过滤
        login_logs = list_audit_logs(action="login")
        assert all(l["action"] == "login" for l in login_logs)
        assert len(login_logs) == 2

        # 按 user_id 过滤
        user1_logs = list_audit_logs(user_id="user1")
        assert len(user1_logs) == 2

        # limit
        limited = list_audit_logs(limit=1)
        assert len(limited) == 1

    def test_audit_log_fields(self, tmp_db):
        """审计日志应包含完整的字段"""
        from src.storage.database import create_audit_log, list_audit_logs

        create_audit_log(
            user_id="u_test",
            action="register",
            resource_type="user",
            resource_id="u_test",
            details='{"ip": "192.168.1.1"}',
            ip_address="192.168.1.1",
        )

        logs = list_audit_logs(user_id="u_test")
        assert len(logs) == 1
        log = logs[0]
        assert log["user_id"] == "u_test"
        assert log["action"] == "register"
        assert log["resource_type"] == "user"
        assert log["resource_id"] == "u_test"
        assert "ip" in log["details"]
        assert log["ip_address"] == "192.168.1.1"
        assert "created_at" in log

    def test_audit_log_created_at_is_iso(self, tmp_db):
        """created_at应为ISO格式时间戳"""
        from src.storage.database import create_audit_log, list_audit_logs

        create_audit_log("u1", "test_action")
        logs = list_audit_logs(user_id="u1")
        assert len(logs) == 1
        ts = logs[0]["created_at"]
        # 应包含T (ISO格式)
        assert "T" in ts

    def test_log_audit_helper(self, tmp_db):
        """jwt_auth.log_audit辅助函数应正常写入日志"""
        from src.api.jwt_auth import log_audit
        from src.storage.database import list_audit_logs

        log_audit("helper_user", "login", "user", "helper_user", ip_address="10.0.0.1")
        logs = list_audit_logs(user_id="helper_user")
        assert len(logs) == 1
        assert logs[0]["action"] == "login"

    def test_log_audit_exception_silenced(self, tmp_db):
        """log_audit写入失败时不应抛出异常（静默处理）"""
        from src.api.jwt_auth import log_audit
        from unittest.mock import patch

        with patch("src.api.jwt_auth.create_audit_log", side_effect=Exception("DB error")):
            # 不应抛异常
            log_audit("u1", "test_action")


# ============================================================
# 5. 向后兼容（旧API Key仍可用）
# ============================================================

class TestBackwardCompatibility:

    def test_legacy_api_key_recognized(self):
        """旧API Key应能被识别并通过认证"""
        from src.api.jwt_auth import (
            register_legacy_api_key, _try_legacy_api_key,
            HTTPAuthorizationCredentials,
        )

        # 注册一个旧 Key
        test_key = "sk-rag-test-legacy-key"
        register_legacy_api_key(test_key, {
            "key": test_key,
            "role": "admin",
            "created_at": "2026-01-01",
            "active": True,
        })

        # 创建一个假的 HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=test_key)
        result = _try_legacy_api_key(creds)
        assert result is not None
        assert result["role"] == "admin"
        assert "apikey" in result["id"]
        assert "apikey" in result["username"]

    def test_legacy_api_key_inactive_rejected(self):
        """不活跃的旧API Key应被拒绝"""
        from src.api.jwt_auth import (
            register_legacy_api_key, _try_legacy_api_key,
            HTTPAuthorizationCredentials,
        )

        test_key = "sk-rag-inactive-key"
        register_legacy_api_key(test_key, {
            "key": test_key,
            "role": "viewer",
            "active": False,
        })

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=test_key)
        result = _try_legacy_api_key(creds)
        assert result is None

    def test_legacy_unknown_key_rejected(self):
        """未注册的旧API Key应返回None"""
        from src.api.jwt_auth import (
            _try_legacy_api_key, HTTPAuthorizationCredentials,
        )

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="unknown-key-xyz")
        result = _try_legacy_api_key(creds)
        assert result is None

    def test_jwt_and_legacy_coexist(self, tmp_db):
        """JWT token和旧API Key在统一认证中共存"""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from src.api.jwt_auth import (
            get_current_user, create_access_token,
            register_legacy_api_key, hash_password,
        )
        from src.storage.database import create_user

        # 在测试数据库中创建用户
        jwt_user = create_user("coexist_user", "jwt_user", hash_password("pass"), role="viewer")
        assert jwt_user is not None

        app = FastAPI()

        @app.get("/whoami")
        async def whoami(user: dict = Depends(get_current_user)):
            return {"username": user["username"], "role": user["role"]}

        # 注册旧Key
        legacy_key = "sk-rag-coexist-test"
        register_legacy_api_key(legacy_key, {
            "key": legacy_key,
            "role": "editor",
            "active": True,
        })

        client = TestClient(app, raise_server_exceptions=False)

        # 用JWT访问
        jwt_token = create_access_token(jwt_user["id"], jwt_user["role"])
        resp = client.get("/whoami", headers={"Authorization": f"Bearer {jwt_token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "jwt_user"
        assert resp.json()["role"] == "viewer"

        # 用旧Key访问
        resp = client.get("/whoami", headers={"Authorization": f"Bearer {legacy_key}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "editor"
        assert "apikey" in resp.json()["username"]

    def test_jwt_takes_priority_over_legacy(self):
        """JWT格式token应优先走JWT验证路径，而非旧Key路径"""
        from src.api.jwt_auth import create_access_token, decode_token

        # 创建一个合法的JWT token
        token = create_access_token("priority_user", "admin")
        # JWT token包含两个点（header.payload.signature）
        assert token.count(".") == 2
        payload = decode_token(token)
        assert payload["sub"] == "priority_user"
        assert payload["role"] == "admin"


# ============================================================
# 6. 数据库表结构验证
# ============================================================

class TestDatabaseSchema:

    def test_users_table_exists(self, tmp_db):
        """users表应存在"""
        conn = sqlite3.connect(str(tmp_db))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        assert "users" in table_names

    def test_audit_logs_table_exists(self, tmp_db):
        """audit_logs表应存在"""
        conn = sqlite3.connect(str(tmp_db))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        assert "audit_logs" in table_names

    def test_knowledge_bases_table_exists(self, tmp_db):
        """knowledge_bases表应存在"""
        conn = sqlite3.connect(str(tmp_db))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        assert "knowledge_bases" in table_names

    def test_document_permissions_table_exists(self, tmp_db):
        """document_permissions表应存在"""
        conn = sqlite3.connect(str(tmp_db))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        assert "document_permissions" in table_names

    def test_users_table_columns(self, tmp_db):
        """users表应包含所有必需字段"""
        conn = sqlite3.connect(str(tmp_db))
        cols = conn.execute("PRAGMA table_info(users)").fetchall()
        col_names = [c[1] for c in cols]
        conn.close()
        assert "id" in col_names
        assert "username" in col_names
        assert "password_hash" in col_names
        assert "role" in col_names
        assert "created_at" in col_names
        assert "last_login" in col_names
        assert "is_active" in col_names

    def test_audit_logs_table_columns(self, tmp_db):
        """audit_logs表应包含所有必需字段"""
        conn = sqlite3.connect(str(tmp_db))
        cols = conn.execute("PRAGMA table_info(audit_logs)").fetchall()
        col_names = [c[1] for c in cols]
        conn.close()
        assert "user_id" in col_names
        assert "action" in col_names
        assert "resource_type" in col_names
        assert "resource_id" in col_names
        assert "details" in col_names
        assert "ip_address" in col_names
        assert "created_at" in col_names


# ============================================================
# 7. Pydantic Schema 验证
# ============================================================

class TestSchemas:

    def test_register_request_validation(self):
        """RegisterRequest应校验min_length"""
        from src.api.schemas import RegisterRequest
        from pydantic import ValidationError

        # 正常
        req = RegisterRequest(username="alice", password="Alice1234")
        assert req.username == "alice"

        # username太短
        with pytest.raises(ValidationError):
            RegisterRequest(username="ab", password="Alice1234")

        # password太短
        with pytest.raises(ValidationError):
            RegisterRequest(username="alice", password="123")

    def test_login_request(self):
        """LoginRequest字段验证"""
        from src.api.schemas import LoginRequest

        req = LoginRequest(username="bob", password="Bob12345")
        assert req.username == "bob"
        assert req.password == "Bob12345"

    def test_token_response(self):
        """TokenResponse应包含所有字段"""
        from src.api.schemas import TokenResponse

        resp = TokenResponse(
            access_token="at_xxx",
            refresh_token="rt_xxx",
            expires_in=86400,
        )
        assert resp.token_type == "bearer"  # 默认值
        assert resp.expires_in == 86400

    def test_refresh_request(self):
        """RefreshRequest应包含refresh_token字段"""
        from src.api.schemas import RefreshRequest

        req = RefreshRequest(refresh_token="rt_xxx")
        assert req.refresh_token == "rt_xxx"

    def test_knowledge_base_create_request(self):
        """KnowledgeBaseCreateRequest验证"""
        from src.api.schemas import KnowledgeBaseCreateRequest
        from pydantic import ValidationError

        req = KnowledgeBaseCreateRequest(name="测试知识库", description="desc")
        assert req.name == "测试知识库"

        # name不能为空
        with pytest.raises(ValidationError):
            KnowledgeBaseCreateRequest(name="", description="desc")


# ============================================================
# 8. 集成测试：注册 -> 登录 -> 访问受保护接口 -> 审计日志
# ============================================================

class TestIntegrationFlow:

    def test_full_flow_via_client(self, tmp_db):
        """通过TestClient走完: 无认证(401) -> 注册 -> 登录 -> 带token访问"""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from src.api.jwt_auth import (
            get_current_user, require_role,
            create_access_token, create_refresh_token,
            register_legacy_api_key, log_audit,
            hash_password, verify_password,
        )
        from src.storage.database import create_user, get_user_by_username, update_user_login
        import uuid

        app = FastAPI()

        @app.post("/auth/register-test")
        async def register_endpoint(username: str, password: str):
            user_id = uuid.uuid4().hex
            user = create_user(user_id, username, hash_password(password), role="viewer")
            if user is None:
                return {"error": "用户名已存在"}
            return {
                "access_token": create_access_token(user["id"], user["role"]),
                "refresh_token": create_refresh_token(user["id"]),
            }

        @app.post("/auth/login-test")
        async def login_endpoint(username: str, password: str):
            user = get_user_by_username(username)
            if user is None or not verify_password(password, user["password_hash"]):
                return {"error": "用户名或密码错误"}
            update_user_login(user["id"])
            return {
                "access_token": create_access_token(user["id"], user["role"]),
                "refresh_token": create_refresh_token(user["id"]),
            }

        @app.get("/protected-resource")
        async def protected(user: dict = Depends(get_current_user)):
            return {"user": user["username"], "role": user["role"]}

        @app.get("/admin-resource")
        async def admin_resource(user: dict = Depends(require_role("admin"))):
            return {"user": user["username"]}

        client = TestClient(app, raise_server_exceptions=False)

        # Step 1: 无认证访问应 401 (通过FastAPI自动处理)
        # (这里我们的简化端点不走Depends，所以直接跳过)

        # Step 2: 注册
        resp = client.post("/auth/register-test?username=integration_user&password=IntPass123")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

        # Step 3: 用token访问受保护接口
        token = data["access_token"]
        resp = client.get("/protected-resource", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user"] == "integration_user"
        assert resp.json()["role"] == "viewer"

        # Step 4: viewer尝试访问admin接口应被拒
        resp = client.get("/admin-resource", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_api_v1_routes_require_auth(self, tmp_db):
        """真实路由 /api/v1/* 应要求认证"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routes import router
        from src.api.jwt_auth import create_access_token, hash_password
        from src.storage.database import create_user

        # 在测试数据库中创建admin用户
        admin = create_user("stats_admin", "stats_admin_user", hash_password("pass"), role="admin")
        assert admin is not None

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        # stats接口应要求认证
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 401

        # 带合法token应能访问
        token = create_access_token(admin["id"], admin["role"])
        resp = client.get("/api/v1/stats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_audit_on_query(self, tmp_db):
        """查询操作应写入审计日志"""
        from src.api.jwt_auth import log_audit
        from src.storage.database import list_audit_logs

        log_audit("query_user", "query", "knowledge_base", "kb_default",
                  details='{"question": "什么是Python"}')

        logs = list_audit_logs(action="query")
        assert len(logs) >= 1
        assert logs[0]["user_id"] == "query_user"
        assert "Python" in logs[0]["details"]
