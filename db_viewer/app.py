from flask import Flask, jsonify, render_template, request
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import SessionLocal, init_db
from models import Paper
from sqlalchemy import or_, desc

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/papers")
def api_papers():
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page
    query_str = request.args.get("query", "").strip()

    db = SessionLocal()
    try:
        q = db.query(Paper)
        if query_str:
            term = f"%{query_str}%"
            q = q.filter(
                or_(Paper.title.like(term), Paper.authors.like(term), Paper.abstract_snippet.like(term))
            )
        total_count = q.count()
        papers = q.order_by(desc(Paper.published_date)).offset(offset).limit(per_page).all()
        return jsonify({
            "papers": [{
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "abstract_snippet": p.abstract_snippet,
                "published_date": p.published_date.isoformat() if p.published_date else None,
                "source_api": p.source_api,
                "source_url": p.source_url,
                "citation_count": p.citation_count,
                "primary_topic": p.primary_topic,
            } for p in papers],
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page,
        })
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
