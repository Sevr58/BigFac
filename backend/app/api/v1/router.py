from fastapi import APIRouter
from app.api.v1 import auth, workspaces, brands, strategy, assets, drafts

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(brands.router, tags=["brands"])
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
router.include_router(assets.router)
router.include_router(drafts.router)
