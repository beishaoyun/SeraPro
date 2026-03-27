"""
凭证加密模块 - 自研加密实现

安全设计:
- AES-256-GCM 对称加密 (认证加密)
- 密钥派生使用 PBKDF2-HMAC-SHA256
- 每个凭证独立的 nonce
- 密钥存储在 KMS 或环境变量
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class CredentialEncryptor:
    """凭证加密器"""

    def __init__(self, master_key: bytes):
        """
        初始化加密器

        Args:
            master_key: 主密钥 (32 字节)
        """
        if len(master_key) != 32:
            raise ValueError("Master key must be 32 bytes")
        self.master_key = master_key

    def encrypt(self, plaintext: str) -> bytes:
        """
        加密凭证

        Args:
            plaintext: 明文凭据

        Returns:
            密文 (salt + nonce + ciphertext)
        """
        # 生成随机 nonce (12 字节 for AES-GCM)
        nonce = os.urandom(12)

        # 生成随机 salt (16 字节)
        salt = os.urandom(16)

        # 从 master_key 派生会话密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(self.master_key)

        # 加密
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

        # 返回：salt + nonce + ciphertext
        return salt + nonce + ciphertext

    def decrypt(self, ciphertext: bytes) -> str:
        """
        解密凭证

        Args:
            ciphertext: 密文 (salt + nonce + ciphertext)

        Returns:
            明文凭证
        """
        if len(ciphertext) < 16 + 12:
            raise ValueError("Ciphertext too short")

        # 提取 salt, nonce, ciphertext
        salt = ciphertext[:16]
        nonce = ciphertext[16:28]
        actual_ciphertext = ciphertext[28:]

        # 派生会话密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(self.master_key)

        # 解密
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, actual_ciphertext, None)

        return plaintext.decode()

    def encrypt_base64(self, plaintext: str) -> str:
        """加密并返回 Base64 字符串"""
        ciphertext = self.encrypt(plaintext)
        return base64.b64encode(ciphertext).decode('utf-8')

    def decrypt_base64(self, ciphertext_b64: str) -> str:
        """解密 Base64 字符串"""
        ciphertext = base64.b64decode(ciphertext_b64)
        return self.decrypt(ciphertext)
