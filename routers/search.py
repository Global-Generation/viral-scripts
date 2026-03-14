import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Search, Video
from services.tavily_service import search_tiktok

router = APIRouter(prefix="/api/search", tags=["search"])
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str
    category: str = ""


@router.post("")
def do_search(data: SearchRequest, db: Session = Depends(get_db)):
    query = data.query.strip()
    if not query:
        return {"error": "Query is empty"}

    results = search_tiktok(query, max_results=15)

    search = Search(
        query=query,
        category=data.category,
        result_count=len(results),
    )
    db.add(search)
    db.flush()

    for r in results:
        video = Video(
            search_id=search.id,
            tiktok_url=r["url"],
            title=r.get("title", ""),
            description=r.get("content", ""),
            score=r.get("score", 0.0),
        )
        db.add(video)

    db.commit()
    return {"search_id": search.id, "count": len(results)}


@router.get("/status/{video_id}")
def video_status(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).get(video_id)
    if not video:
        return {"status": "not_found"}
    result = {"status": video.status, "error": video.error_message}
    if video.script:
        result["script_id"] = video.script.id
    return result
