import os
from enum import Enum
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings


class StorageProvider(str, Enum):
    """Supported storage providers."""

    AWS = "aws"
    SUPABASE = "supabase"
    LOCAL = "local"  # For testing


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Flowex"
    DEBUG: bool = False

    # Storage Provider Selection
    # Set to "supabase" for development, "aws" for production
    STORAGE_PROVIDER: StorageProvider = StorageProvider.SUPABASE

    # Database
    # For Supabase: postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    # For local: postgresql://postgres:postgres@localhost:5432/flowex
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/flowex"

    # Supabase Configuration (for development)
    SUPABASE_URL: str = ""  # https://[project-ref].supabase.co
    SUPABASE_ANON_KEY: str = ""  # Public anon key
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # Service role key (for backend operations)
    SUPABASE_STORAGE_BUCKET: str = "drawings"  # Bucket name in Supabase Storage

    # Authentication
    AUTH0_DOMAIN: str = ""
    AUTH0_CLIENT_ID: str = ""
    AUTH0_CLIENT_SECRET: str = ""
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # AWS S3 (for production)
    AWS_S3_BUCKET: str = "flowex-uploads-eu"
    AWS_REGION: str = "eu-west-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Microsoft OAuth (OneDrive/SharePoint)
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"  # "common" for multi-tenant
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/api/v1/cloud/callback/microsoft"

    # Google OAuth (Google Drive)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/cloud/callback/google"

    # Token Encryption Key (Fernet - must be 32 url-safe base64-encoded bytes)
    TOKEN_ENCRYPTION_KEY: str = ""  # Generate with: Fernet.generate_key().decode()

    @property
    def is_supabase(self) -> bool:
        """Check if using Supabase as storage provider."""
        return self.STORAGE_PROVIDER == StorageProvider.SUPABASE

    @property
    def is_aws(self) -> bool:
        """Check if using AWS as storage provider."""
        return self.STORAGE_PROVIDER == StorageProvider.AWS

    @property
    def microsoft_auth_url(self) -> str:
        """Microsoft OAuth2 authorization endpoint."""
        return f"https://login.microsoftonline.com/{self.MICROSOFT_TENANT_ID}/oauth2/v2.0/authorize"

    @property
    def microsoft_token_url(self) -> str:
        """Microsoft OAuth2 token endpoint."""
        return f"https://login.microsoftonline.com/{self.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"

    @property
    def google_auth_url(self) -> str:
        """Google OAuth2 authorization endpoint."""
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def google_token_url(self) -> str:
        """Google OAuth2 token endpoint."""
        return "https://oauth2.googleapis.com/token"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        """Validate that production secrets are properly configured when not in DEBUG mode.

        Skipped during testing (when TESTING=true environment variable is set).
        """
        # Skip validation during testing
        if os.environ.get("TESTING", "").lower() == "true":
            return self

        if not self.DEBUG:
            # Check JWT secret is not the default development value
            if self.JWT_SECRET_KEY == "dev-secret-key-change-in-production":
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from default value in production. "
                    "Set DEBUG=true for development or provide a secure secret key."
                )

            # Check token encryption key is set for cloud integrations
            if (self.MICROSOFT_CLIENT_ID or self.GOOGLE_CLIENT_ID) and not self.TOKEN_ENCRYPTION_KEY:
                raise ValueError(
                    "TOKEN_ENCRYPTION_KEY must be set when cloud integrations are configured. "
                    "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )

        return self

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
