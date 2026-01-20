"""Token encryption for cloud storage credentials."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class TokenEncryption:
    """Encrypt and decrypt tokens using Fernet symmetric encryption."""

    _fernet: Fernet | None = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create Fernet instance."""
        if cls._fernet is None:
            if not settings.TOKEN_ENCRYPTION_KEY:
                raise ValueError(
                    "TOKEN_ENCRYPTION_KEY must be set. "
                    "Generate one with: python -c "
                    "'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
            cls._fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """Encrypt a token string."""
        fernet = cls._get_fernet()
        encrypted = fernet.encrypt(plaintext.encode())
        return encrypted.decode()

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        """Decrypt an encrypted token string."""
        fernet = cls._get_fernet()
        try:
            decrypted = fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            raise ValueError("Invalid or corrupted token")

    @classmethod
    def generate_key(cls) -> str:
        """Generate a new encryption key."""
        return Fernet.generate_key().decode()
