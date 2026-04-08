from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.taxonomy import Category, Role
from app.schemas.taxonomy import NamedEntityCreate, NamedEntityOut

router = APIRouter(tags=["taxonomy"])


@router.get("/api/categories", response_model=list[NamedEntityOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.id.asc())).all()


@router.post("/api/categories", response_model=NamedEntityOut)
def create_category(payload: NamedEntityCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    existed = db.scalar(select(Category).where(Category.name == name))
    if existed:
        raise HTTPException(status_code=409, detail="Category already exists")
    item = Category(name=name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/api/categories/{category_id}", response_model=NamedEntityOut)
def update_category(category_id: int, payload: NamedEntityCreate, db: Session = Depends(get_db)):
    item = db.get(Category, category_id)
    if not item:
        raise HTTPException(status_code=404, detail="Category not found")
    name = payload.name.strip()
    duplicate = db.scalar(select(Category).where(Category.name == name, Category.id != category_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Category name already exists")
    item.name = name
    db.commit()
    db.refresh(item)
    return item


@router.delete("/api/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    item = db.get(Category, category_id)
    if not item:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@router.get("/api/roles", response_model=list[NamedEntityOut])
def list_roles(db: Session = Depends(get_db)):
    return db.scalars(select(Role).order_by(Role.id.asc())).all()


@router.post("/api/roles", response_model=NamedEntityOut)
def create_role(payload: NamedEntityCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    existed = db.scalar(select(Role).where(Role.name == name))
    if existed:
        raise HTTPException(status_code=409, detail="Role already exists")
    item = Role(name=name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/api/roles/{role_id}", response_model=NamedEntityOut)
def update_role(role_id: int, payload: NamedEntityCreate, db: Session = Depends(get_db)):
    item = db.get(Role, role_id)
    if not item:
        raise HTTPException(status_code=404, detail="Role not found")
    name = payload.name.strip()
    duplicate = db.scalar(select(Role).where(Role.name == name, Role.id != role_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Role name already exists")
    item.name = name
    db.commit()
    db.refresh(item)
    return item


@router.delete("/api/roles/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    item = db.get(Role, role_id)
    if not item:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}

