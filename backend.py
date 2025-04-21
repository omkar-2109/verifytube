import os
import json
from datetime import datetime

from flask import jsonify, request
from google.auth.transport import requests as grequests
from google.oauth2 import id_token
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from googleapiclient.discovery import build

# In-memory history
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
        if not captions["items"]:
            return None
        caption_id = captions["items"][0]["id"]
        print(f"[INFO] Caption found (ID: {caption_id}), but API key alone cannot fetch text.")
        return None
    except Exception as e:
        print(f"[ERROR] YouTube API caption fetch failed: {e}")
        return None


def get_transcript(video_id):
    transcript = fetch_transcript(video_id)
    if not transcript:
        transcript = fetch_caption_with_api(video_id)
    return transcript


def generate_fact_check(transcript):
    if not transcript:
        return None
    # Placeholder Gemini logic
    return f"Fact-check summary: [Simulated] This transcript contains {len(transcript.split())} words."
