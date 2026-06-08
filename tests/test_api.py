def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stats(client):
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total_papers" in data
    assert isinstance(data["total_papers"], int)
    assert data["total_papers"] >= 0


def test_feed(client):
    r = client.get("/feed")
    assert r.status_code == 200
    data = r.json()
    assert "rows" in data


def test_search(client):
    r = client.get("/search?q=learning")
    assert r.status_code == 200
    assert "papers" in r.json()


def test_single_user_preferences(client):
    r = client.get("/users/me/preferences")
    assert r.status_code == 200
    assert "topic_slugs" in r.json()


def test_save_paper_no_auth(client):
    search = client.get("/search?q=learning")
    papers = search.json().get("papers", [])
    if not papers:
        return
    paper_id = papers[0]["id"]
    r = client.post(f"/users/me/reading-list/{paper_id}")
    assert r.status_code == 200
    assert r.json()["saved"] is True
