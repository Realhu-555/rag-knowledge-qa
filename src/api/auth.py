"""API Key鉴权"""
import secrets
from datetime import datetime

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 简单的内存存储（生产环境应该用数据库）
API_KEYS: dict[str, dict] = {}

security = HTTPBearer()


def generate_api_key(prefix: str = "sk-rag") -> str:
    """生成API Key"""
    random_part = secrets.token_hex(16)
    return f"{prefix}-{random_part}"


def create_api_key(role: str = "reader") -> dict:
    """创建API Key"""
    key = generate_api_key()
    API_KEYS[key] = {
        "key": key,
        "role": role,
        "created_at": datetime.now().isoformat(),
        "active": True
    }
    return API_KEYS[key]


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """验证API Key"""
    key = credentials.credentials

    if key not in API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="无效的API Key"
        )

    key_info = API_KEYS[key]
    if not key_info["active"]:
        raise HTTPException(
            status_code=401,
            detail="API Key已被禁用"
        )

    return key_info


def require_role(required_role: str):
    """角色检查装饰器"""
    def role_checker(key_info: dict = Security(verify_api_key)):
        role_hierarchy = {"reader": 0, "writer": 1, "admin": 2}
        user_level = role_hierarchy.get(key_info["role"], -1)
        required_level = role_hierarchy.get(required_role, 2)

        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"需要 {required_role} 权限"
            )
        return key_info
    return role_checker
