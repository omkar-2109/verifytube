from flask import Flask, request, jsonify
from flask_cors import CORS
from backend import (
    verify_token,
    get_video_id,
    get_transcript,
    generate_fact_check,
    user_video_history,
)
from datetime import datetime

app = Flask(__name__)
CORS(app, origins="chrome-extension://pohnlnkideolhcmndnnddepnboapnhpm")

@app.route("/")
def index():
    return "✅ VerifyTube Backend is running!"

@app.route("/fact-check", methods=["POST"])
def fact_check():
    data = request.get_json()
    url = data.get("url")
    token = data.get("token")

    if not url or not token:
        return jsonify({"error": "Missing video URL or login token"}), 400

    user_email = verify_token(token)
    if not user_email:
        return jsonify({"error": "Invalid login token"}), 401

    video_id = get_video_id(url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    print(f"[INFO] User: {user_email} | Video ID: {video_id}")
    transcript = get_transcript(video_id)

    if not transcript:
        return jsonify({"error": "Transcript unavailable"}), 404

    # Save history
    user_history = user_video_history.setdefault(user_email, [])
    if not any(item["video_id"] == video_id for item in user_history):
        user_history.append({
            "video_id": video_id,
            "url": url,
            "title": "Fetched on " + datetime.utcnow().isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        })

    # Simulated fact-check
    summary = generate_fact_check(transcript)

    return jsonify({
        "video_id": video_id,
        "transcript": transcript,
        "fact_check": summary,
        "message": "Transcript fetched successfully"
    })


@app.route("/history", methods=["POST"])
def get_history():
    data = request.get_json()
    token = data.get("token")
    user_email = verify_token(token)

    if not user_email:
        return jsonify({"error": "Invalid login token"}), 401

    history = user_video_history.get(user_email, [])
    return jsonify({"email": user_email, "history": history})
