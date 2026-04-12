from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from app.models.brand import Brand, SocialAccount
from app.schemas.brand import BrandCreate, BrandUpdate

def create_brand(db: Session, workspace_id: int, payload: BrandCreate) -> Brand:
    if db.query(Brand).filter(Brand.workspace_id == workspace_id).first():
        raise HTTPException(status_code=409, detail="Brand already exists for this workspace")
    brand = Brand(
        workspace_id=workspace_id,
        name=payload.name,
        company_type=payload.company_type,
        description=payload.description,
        target_audience=payload.target_audience,
        goals=payload.goals,
        tone_of_voice=payload.tone_of_voice,
        posting_frequency=payload.posting_frequency,
    )
    db.add(brand)
    db.flush()
    for network in payload.networks:
        db.add(SocialAccount(brand_id=brand.id, network=network))
    db.commit()
    db.refresh(brand)
    # Force eager load while session is open
    _ = brand.social_accounts
    return brand

def get_brand(db: Session, workspace_id: int) -> Brand:
    brand = (
        db.query(Brand)
        .options(joinedload(Brand.social_accounts))
        .filter(Brand.workspace_id == workspace_id)
        .first()
    )
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand

def update_brand(db: Session, workspace_id: int, payload: BrandUpdate) -> Brand:
    brand = get_brand(db, workspace_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(brand, field, value)
    db.commit()
    db.refresh(brand)
    _ = brand.social_accounts
    return brand
