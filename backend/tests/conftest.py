"""Pytest configuration and fixtures."""

import os

# Set TESTING environment variable before any imports to skip production secrets validation
os.environ["TESTING"] = "true"
