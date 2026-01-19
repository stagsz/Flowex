"""Pytest configuration and fixtures."""

import os

# Set TESTING environment variable before any imports to skip production secrets validation
os.environ["TESTING"] = "true"

# Disable dev auth bypass to ensure authentication tests work correctly
os.environ["DEV_AUTH_BYPASS"] = "false"
