from flask import Flask, jsonify, request, render_template
import database
import config
import downloader
import analyzer
import explorer
import translator
import scheduler
import keyword_extractor
import trending

app = Flask(__name__)

database.init_db()
scheduler.start()

# ── Pages ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ── Papers ─────────────────────────────────────────────────────────────────────

@app.route("/api/papers")
def list_papers():
    source   = request.args.get("source")
    starred  = request.args.get("starred")
    unread   = request.args.get("unread") == "1"
    date     = request.args.get("date")
    page     = int(request.args.get("page", 1))
    limit    = int(request.args.get("limit", 20))
    offset   = (page - 1) * limit

    papers = database.get_papers(
        source=source,
        starred=(True if starred == "1" else (False if starred == "0" else None)),
        unread=unread,
        date=date,
        limit=limit,
        offset=offset
    )
    return jsonify({"papers": papers, "page": page})

@app.route("/api/papers/<int:pid>")
def get_paper(pid):
    paper = database.get_paper(pid)
    if not paper:
        return jsonify({"error": "not found"}), 404
    analysis = database.get_analysis(pid)
    return jsonify({"paper": paper, "analysis": analysis})

@app.route("/api/papers/<int:pid>/star", methods=["POST"])
def star_paper(pid):
    paper = database.get_paper(pid)
    if not paper:
        return jsonify({"error": "not found"}), 404
    new_val = 0 if paper["is_starred"] else 1
    database.update_paper(pid, is_starred=new_val)
    return jsonify({"is_starred": new_val})

@app.route("/api/papers/<int:pid>/read", methods=["POST"])
def mark_read(pid):
    database.update_paper(pid, is_read=1)
    return jsonify({"ok": True})

@app.route("/api/papers/<int:pid>/download", methods=["POST"])
def download(pid):
    result = downloader.download_pdf(pid)
    return jsonify(result)

@app.route("/api/papers/<int:pid>/translate", methods=["POST"])
def translate(pid):
    force = request.json.get("force", False) if request.is_json else False
    result = translator.translate_paper(pid, force=force)
    return jsonify(result)

@app.route("/api/papers/<int:pid>/analyze", methods=["POST"])
def analyze(pid):
    force = request.json.get("force", False) if request.is_json else False
    result = analyzer.analyze_paper(pid, force=force)
    return jsonify(result)

# ── Advanced Exploration ───────────────────────────────────────────────────────

@app.route("/api/papers/<int:pid>/explore/start", methods=["POST"])
def explore_start(pid):
    result = explorer.start_exploration(pid)
    return jsonify(result)

@app.route("/api/sessions/<int:sid>/chat", methods=["POST"])
def session_chat(sid):
    data = request.get_json()
    if not data or not data.get("message", "").strip():
        return jsonify({"ok": False, "msg": "消息不能为空"}), 400
    result = explorer.chat(sid, data["message"].strip())
    return jsonify(result)

@app.route("/api/sessions/<int:sid>/end", methods=["POST"])
def session_end(sid):
    result = explorer.end_exploration(sid)
    return jsonify(result)

@app.route("/api/sessions/<int:sid>")
def get_session(sid):
    data = explorer.get_exploration(sid)
    if not data:
        return jsonify({"error": "not found"}), 404
    return jsonify(data)

@app.route("/api/papers/<int:pid>/sessions")
def paper_sessions(pid):
    sessions = database.get_paper_sessions(pid)
    return jsonify({"sessions": sessions})

# ── Keyword Extraction ────────────────────────────────────────────────────────

@app.route("/api/papers/<int:pid>/keywords", methods=["POST"])
def extract_keywords(pid):
    force = request.json.get("force", False) if request.is_json else False
    result = keyword_extractor.extract_paper_keywords(pid, force=force)
    return jsonify(result)

# ── Trending ───────────────────────────────────────────────────────────────────

@app.route("/api/trending")
def get_trending():
    return jsonify({"keywords": trending.get_trending_list()})

@app.route("/api/trending/search", methods=["POST"])
def trending_search():
    data = request.get_json()
    keyword = (data or {}).get("keyword", "").strip()
    if not keyword:
        return jsonify({"ok": False, "msg": "keyword 不能为空"}), 400
    return jsonify(trending.ai_search_papers(keyword))

@app.route("/api/trending/detail", methods=["POST"])
def trending_detail():
    data = request.get_json()
    keyword = (data or {}).get("keyword", "").strip()
    if not keyword:
        return jsonify({"ok": False, "msg": "keyword 不能为空"}), 400
    return jsonify(trending.ai_keyword_detail(keyword))

# ── Stats ──────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def stats():
    return jsonify(database.get_stats())

# ── Manual fetch ───────────────────────────────────────────────────────────────

@app.route("/api/fetch", methods=["POST"])
def manual_fetch():
    results = scheduler.run_fetch()
    return jsonify({"ok": True, "results": results})

# ── Config ─────────────────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def get_config():
    cfg = config.load_config()
    cfg.pop("anthropic_api_key", None)
    cfg.pop("anthropic_api_key_advanced", None)
    return jsonify(cfg)

@app.route("/api/config", methods=["POST"])
def save_config():
    new_cfg = request.get_json()
    if not new_cfg:
        return jsonify({"error": "invalid json"}), 400
    cfg = config.load_config()
    cfg.update(new_cfg)
    config.save_config(cfg)
    if "schedule_hour" in new_cfg:
        scheduler.start(hour=new_cfg["schedule_hour"])
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=False, port=5001)
