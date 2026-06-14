"""
Vercel Serverless Function entry point.

Vercel automatically routes requests through this file when
deployed with the Python runtime. It re-exports the FastAPI
app from backend.main so all endpoints work as-is.
"""
from backend.main import app

# Vercel expects a variable named `app` for ASGI frameworks.
