from fastapi import APIRouter

from app.api.routes import auth, conversations, health, models, pdf_extraction, preferences, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(models.router, prefix="/models", tags=["AI Models"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["AI Preferences"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(pdf_extraction.router, prefix="/pdf", tags=["PDF Processing"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
