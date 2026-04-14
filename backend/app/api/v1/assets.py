from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import SourceAsset, AssetStatus, AssetType
from app.services.storage import storage

router = APIRouter(prefix="/assets", tags=["assets"])


class InitiateUploadRequest(BaseModel):
    brand_id: int
    name: str
    asset_type: AssetType
    file_size: Optional[int] = None
    tags: list[str] = []


class InitiateUploadResponse(BaseModel):
    asset_id: int
    upload_url: str
    storage_key: str


class AssetOut(BaseModel):
    id: int
    brand_id: int
    name: str
    asset_type: str
    status: str
    storage_key: str
    file_size: Optional[int]
    duration_seconds: Optional[int]
    transcription: Optional[str]
    tags: list

    class Config:
        from_attributes = True


@router.post("/initiate", response_model=InitiateUploadResponse)
def initiate_upload(
    body: InitiateUploadRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    import uuid
    storage_key = f"brands/{body.brand_id}/assets/{uuid.uuid4()}/{body.name}"
    asset = SourceAsset(
        brand_id=body.brand_id,
        name=body.name,
        asset_type=body.asset_type,
        status=AssetStatus.uploaded,
        storage_key=storage_key,
        file_size=body.file_size,
        tags=body.tags,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    upload_url = storage.presigned_upload_url(storage_key)
    return InitiateUploadResponse(
        asset_id=asset.id,
        upload_url=upload_url,
        storage_key=storage_key,
    )


@router.post("/{asset_id}/confirm")
def confirm_upload(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = db.get(SourceAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.status = AssetStatus.processing
    db.commit()

    from app.tasks.asset_tasks import process_asset
    process_asset.delay(asset_id)

    return {"status": "processing", "asset_id": asset_id}


@router.get("/", response_model=list[AssetOut])
def list_assets(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(SourceAsset).filter(SourceAsset.brand_id == brand_id).all()


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = db.get(SourceAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        storage.delete(asset.storage_key)
    except Exception:
        pass
    db.delete(asset)
    db.commit()
