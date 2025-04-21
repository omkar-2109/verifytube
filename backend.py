import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.auth.transport import requests as grequests
from google.oauth2 import id_token
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from googleapiclient.discovery import build
from datetime import datetime

app = Flask(__name__)
CORS(app)

# In-memory user data store
user_video_history = {}

# Constants
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")


def verify_token(token):
    try:
        idinfo = id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
        return idinfo["email"]
    except Exception as e:
        print(f"[ERROR] Token verification failed: {e}")
        return None


def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None


def fetch_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry["text"] for entry in transcript])
        print("[INFO] Transcript fetched using youtube_transcript_api.")
        return text
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        print(f"[WARNING] No transcript via youtube_transcript_api: {e}")
        return None


def fetch_caption_with_api(video_id):
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        captions = youtube.captions().list(part="snippet", videoId=video_id).execute()
        caption_id = captions["items"][0]["id"]

        print("[INFO] Caption ID found, but API key can't access caption body without OAuth.")
        return None  # Can't fetch body with just API key
    except Exception as e:
        print(f"[ERROR] YouTube API failed to get caption: {e}")
        return None


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

    transcript = fetch_transcript(video_id)
    if not transcript:
        transcript = fetch_caption_with_api(video_id)

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

    return jsonify({
        "video_id": video_id,
        "transcript": transcript,
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
