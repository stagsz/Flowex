import json
import os
from enum import Enum
from functools import lru_cache
from typing import Any, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageProvider(str, Enum):
    """Supported storage providers."""

    AWS = "aws"
    SUPABASE = "supabase"
    LOCAL = "local"  # For testing


def get_secrets_from_aws(secret_name: str, region: str = "eu-west-1") -> dict[str, Any]:
    """Fetch secrets from AWS Secrets Manager.

    Args:
        secret_name: The name/ARN of the secret in Secrets Manager.
        region: AWS region where the secret is stored.

    Returns:
        Dictionary of secret key-value pairs.
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            result: dict[str, Any] = json.loads(response["SecretString"])
            return result
        return {}
    except ImportError:
        # boto3 not installed (likely dev environment)
        return {}
    except ClientError:
        # Secret not found or access denied
        return {}


@lru_cache
def load_aws_secrets() -> dict[str, Any]:
    """Load secrets from AWS Secrets Manager if configured.

    Uses caching to avoid repeated API calls.
    """
    secret_name = os.environ.get("AWS_SECRETS_NAME")
    region = os.environ.get("AWS_REGION", "eu-west-1")

    if secret_name:
        return get_secrets_from_aws(secret_name, region)
    return {}


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Flowex"
    DEBUG: bool = False
    DEV_AUTH_BYPASS: bool = False  # Skip authentication in dev mode

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
    SUPABASE_JWT_SECRET: str = ""  # JWT secret from Supabase dashboard (Settings > API)

    # Authentication Provider: "supabase" or "auth0"
    AUTH_PROVIDER: str = "supabase"

    # Auth0 Configuration (legacy - use AUTH_PROVIDER=auth0 to enable)
    AUTH0_DOMAIN: str = ""
    AUTH0_CLIENT_ID: str = ""
    AUTH0_CLIENT_SECRET: str = ""

    # JWT Configuration
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"  # HS256 for Supabase, RS256 for Auth0
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

    # Sentry Monitoring
    SENTRY_DSN: str = ""  # Sentry DSN for error tracking (leave empty to disable)
    SENTRY_ENVIRONMENT: str = "development"  # development, staging, production
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 10% of transactions for performance monitoring
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.1  # 10% of transactions for profiling

    # Logging Configuration
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_JSON_FORMAT: bool = False  # Use JSON format for logs (recommended for production)

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

    @model_validator(mode="before")
    @classmethod
    def load_secrets_from_aws(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Load secrets from AWS Secrets Manager before validation.

        This allows ECS tasks to inject secrets via the Secrets Manager
        integration, which sets them as environment variables.
        """
        # Try to load from AWS Secrets Manager
        aws_secrets = load_aws_secrets()
        if aws_secrets:
            # Merge AWS secrets with provided data (env vars take precedence)
            for key, value in aws_secrets.items():
                if key not in data or not data[key]:
                    data[key] = value
        return data

    def check_health(self) -> dict[str, Any]:
        """Check health of all dependencies.

        Returns:
            Dictionary with health status of each dependency.
        """
        checks: dict[str, dict[str, str]] = {}
        health: dict[str, Any] = {
            "status": "healthy",
            "checks": checks
        }

        # Check database connection
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.DATABASE_URL)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health["checks"]["database"] = {"status": "healthy"}
        except Exception as e:
            health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "degraded"

        # Check Redis connection
        try:
            import redis
            r = redis.from_url(self.REDIS_URL)  # type: ignore[no-untyped-call]
            r.ping()
            health["checks"]["redis"] = {"status": "healthy"}
        except Exception as e:
            health["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "degraded"

        # Check S3 access (if AWS provider)
        if self.is_aws:
            try:
                import boto3
                s3 = boto3.client("s3", region_name=self.AWS_REGION)
                s3.head_bucket(Bucket=self.AWS_S3_BUCKET)
                health["checks"]["s3"] = {"status": "healthy"}
            except Exception as e:
                health["checks"]["s3"] = {"status": "unhealthy", "error": str(e)}
                health["status"] = "degraded"

        return health

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
