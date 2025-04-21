import re
import google.generativeai as genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from yt_dlp import YoutubeDL
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
import requests
import os


# 🔐 Your YouTube Data API Key
YOUTUBE_API_KEY = os.getenv("GOOGLE_API_KEY")

def get_video_id(url):
    """Extracts video ID from a YouTube URL."""
    parsed_url = urlparse(url)
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]
    elif parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")
    return None

def get_transcript(video_id):
    """Attempts to fetch the transcript using youtube_transcript_api."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en-US'])
        return " ".join([entry['text'] for entry in transcript_list])
    except TranscriptsDisabled:
        print("Transcripts are disabled for this video.")
        return None
    except Exception as e:
        print(f"Error fetching transcript in 'en-US': {e}")

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi'])
        return " ".join([entry['text'] for entry in transcript_list])
    except Exception as e:
        print(f"Error fetching transcript in 'hi': {e}")

    return None

def get_transcript_youtube_api(video_id):
    """Fetches captions metadata using YouTube Data API v3."""
    try:
        youtube = build("youtube", "v3")
        response = youtube.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()

        if not response.get("items"):
            print("No captions found via YouTube API.")
            return None

        for item in response["items"]:
            snippet = item["snippet"]
            if snippet.get("language") == "en" and snippet.get("trackKind") != "ASR":
                return f"Captions available in '{snippet['language']}' — manually uploaded."

        print("Only auto-captions or non-English captions available.")
        return None

    except Exception as e:
        print("Error using YouTube Data API for captions:", e)
        return None

def get_transcript_yt_dlp(video_url):
    """Fallback using yt-dlp + cookies to fetch auto-generated captions."""
    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt',  # Ensure this matches your Docker location
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            subtitles = info.get('automatic_captions', {}).get('en')
            if not subtitles:
                print("No automatic captions found via yt-dlp.")
                return None

            for sub in subtitles:
                if sub.get('ext') == 'vtt':
                    print("Downloading subtitle file from:", sub['url'])
                    response = requests.get(sub['url'])
                    if response.ok:
                        return response.text

        return None
    except Exception as e:
        print("Error fetching transcript using yt-dlp with cookies:", e)
        return None

def generate_fact_check(transcript):
    """Uses Gemini Pro to generate a fact-checking report."""
    client = genai.Client(vertexai=True, project="skillful-cider-451510-j7", location="us-central1")

    text1 = types.Part.from_text(text=f"""
    You are a fact-checking AI. Your task is to extract ONLY news-related claims from the given YouTube transcript.
    For each claim, verify its accuracy and provide credible sources with links.

    **YouTube Transcript:** {transcript}
    """)

    model = "gemini-2.5-pro-exp-03-25"
    contents = [types.Content(role="user", parts=[text1])]
    tools = [types.Tool(google_search=types.GoogleSearch())]

    config = types.GenerateContentConfig(
        temperature=0,
        top_p=1,
        seed=0,
        max_output_tokens=65535,
        response_modalities=["TEXT"],
        tools=tools,
        system_instruction=[types.Part.from_text(text="You are a precise fact-checker. Extract only news claims.")]
    )

    result_text = ""
    for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
            result_text += chunk.text

    return result_text.strip() if result_text else "No fact-check results."
