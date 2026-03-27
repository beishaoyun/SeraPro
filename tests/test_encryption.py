"""
凭证加密模块测试
"""

import pytest
from src.core.credentials.encryption import CredentialEncryptor


class TestCredentialEncryptor:
    """凭证加密测试类"""

    def test_encrypt_decrypt(self):
        """测试加密解密"""
        key = b"0123456789abcdef0123456789abcdef"
        encryptor = CredentialEncryptor(key)

        plaintext = '{"username": "root", "password": "secret123"}'
        ciphertext = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_decrypt_base64(self):
        """测试 Base64 加密解密"""
        key = b"0123456789abcdef0123456789abcdef"
        encryptor = CredentialEncryptor(key)

        plaintext = '{"username": "root", "password": "secret123"}'
        ciphertext_b64 = encryptor.encrypt_base64(plaintext)
        decrypted = encryptor.decrypt_base64(ciphertext_b64)

        assert decrypted == plaintext
        # 验证是 Base64 格式
        import base64
        base64.b64decode(ciphertext_b64)  # 不应抛出异常

    def test_different_ciphertexts_for_same_plaintext(self):
        """测试相同明文生成不同密文"""
        key = b"0123456789abcdef0123456789abcdef"
        encryptor = CredentialEncryptor(key)

        plaintext = "test_password"
        ciphertext1 = encryptor.encrypt(plaintext)
        ciphertext2 = encryptor.encrypt(plaintext)

        # 每次加密应该产生不同的密文 (因为有随机 salt 和 nonce)
        assert ciphertext1 != ciphertext2

    def test_invalid_key_length(self):
        """测试无效密钥长度"""
        with pytest.raises(ValueError) as exc_info:
            CredentialEncryptor(b"short_key")
        assert "32 bytes" in str(exc_info.value)

    def test_decrypt_invalid_ciphertext(self):
        """测试解密密文"""
        key = b"0123456789abcdef0123456789abcdef"
        encryptor = CredentialEncryptor(key)

        with pytest.raises(Exception):
            encryptor.decrypt(b"invalid_ciphertext")

    def test_ssh_key_encryption(self):
        """测试 SSH 私钥加密"""
        key = b"0123456789abcdef0123456789abcdef"
        encryptor = CredentialEncryptor(key)

        ssh_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MvXj5ZzqOZrKpq
-----END RSA PRIVATE KEY-----"""

        encrypted = encryptor.encrypt_base64(ssh_key)
        decrypted = encryptor.decrypt_base64(encrypted)

        assert decrypted == ssh_key
