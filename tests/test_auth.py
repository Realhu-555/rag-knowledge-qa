"""API鉴权模块测试"""
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.api.auth import (
    generate_api_key,
    create_api_key,
    verify_api_key,
    require_role,
    API_KEYS,
)


class TestApiKeyGeneration:
    """API Key生成测试"""

    def test_generate_api_key_format(self):
        """生成格式正确的Key"""
        key = generate_api_key()
        assert key.startswith("sk-rag-")
        assert len(key) > 10

    def test_generate_api_key_custom_prefix(self):
        """自定义前缀"""
        key = generate_api_key(prefix="sk-test")
        assert key.startswith("sk-test-")

    def test_generate_unique_keys(self):
        """每次生成不同的Key"""
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100


class TestCreateApiKey:
    """创建API Key测试"""

    def test_create_key_default_role(self):
        """默认角色是reader"""
        API_KEYS.clear()
        key_info = create_api_key()

        assert key_info["role"] == "reader"
        assert key_info["active"] is True
        assert "created_at" in key_info

    def test_create_key_custom_role(self):
        """自定义角色"""
        API_KEYS.clear()
        key_info = create_api_key(role="admin")

        assert key_info["role"] == "admin"

    def test_create_key_stored(self):
        """Key被存储"""
        API_KEYS.clear()
        key_info = create_api_key()
        key = key_info["key"]

        assert key in API_KEYS


class TestVerifyApiKey:
    """验证API Key测试"""

    def test_verify_valid_key(self):
        """验证有效Key"""
        API_KEYS.clear()
        key_info = create_api_key()
        key = key_info["key"]

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=key)
        result = verify_api_key(credentials)

        assert result["key"] == key

    def test_verify_invalid_key(self):
        """验证无效Key"""
        API_KEYS.clear()
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-key")

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(credentials)
        assert exc_info.value.status_code == 401

    def test_verify_disabled_key(self):
        """验证禁用的Key"""
        API_KEYS.clear()
        key_info = create_api_key()
        key = key_info["key"]
        API_KEYS[key]["active"] = False

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=key)
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(credentials)
        assert exc_info.value.status_code == 401


class TestRequireRole:
    """角色检查测试"""

    def test_sufficient_role(self):
        """角色足够"""
        API_KEYS.clear()
        key_info = create_api_key(role="admin")

        role_checker = require_role("writer")
        result = role_checker(key_info=key_info)
        assert result["role"] == "admin"

    def test_insufficient_role(self):
        """角色不足"""
        API_KEYS.clear()
        key_info = create_api_key(role="reader")

        role_checker = require_role("admin")

        with pytest.raises(HTTPException) as exc_info:
            role_checker(key_info=key_info)
        assert exc_info.value.status_code == 403
