from fastapi import APIRouter

from app.api.routes import auth, conversations, health, models, preferences

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(models.router, prefix="/models", tags=["AI Models"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["AI Preferences"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
