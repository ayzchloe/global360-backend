import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/blog", tags=["blog"])


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


@router.get("/", response_model=list[schemas.BlogArticleOut])
def list_blog_articles(
    tag: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Public — backs the Global360 Blog & News page.
    """
    query = db.query(models.BlogArticle).filter(models.BlogArticle.is_published == True)
    if tag:
        query = query.filter(models.BlogArticle.tags.contains(tag))
    return query.order_by(models.BlogArticle.published_at.desc()).all()


@router.get("/{slug_or_id}", response_model=schemas.BlogArticleOut)
def get_article(slug_or_id: str, db: Session = Depends(get_db)):
    """
    Public article detail view by slug or numeric ID.
    """
    if slug_or_id.isdigit():
        article = db.query(models.BlogArticle).filter(models.BlogArticle.id == int(slug_or_id)).first()
    else:
        article = db.query(models.BlogArticle).filter(models.BlogArticle.slug == slug_or_id).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("/", response_model=schemas.BlogArticleOut, status_code=201)
def create_article(
    art_in: schemas.BlogArticleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    slug = art_in.slug or _slugify(art_in.title)
    
    # Check duplicate slug
    existing = db.query(models.BlogArticle).filter(models.BlogArticle.slug == slug).first()
    if existing:
        slug = f"{slug}-{auth.secrets.token_hex(3)}"

    new_article = models.BlogArticle(
        title=art_in.title,
        slug=slug,
        summary=art_in.summary,
        content=art_in.content,
        cover_image=art_in.cover_image,
        author_name=art_in.author_name or current_user.name,
        tags=art_in.tags,
        read_time=art_in.read_time or "5 min read",
        is_published=art_in.is_published,
    )
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    return new_article


@router.delete("/{article_id}", status_code=200)
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    article = db.query(models.BlogArticle).filter(models.BlogArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"message": "Article deleted successfully"}
