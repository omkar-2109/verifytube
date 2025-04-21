import re
import os
import requests
from googleapiclient.discovery import build
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from yt_dlp import YoutubeDL

YOUTUBE_API_KEY = os.getenv("GOOGLE_API_KEY")

def get_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en-US'])
        return " ".join([entry['text'] for entry in transcript_list])
    except TranscriptsDisabled:
        return None
    except Exception:
        pass

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi'])
        return " ".join([entry['text'] for entry in transcript_list])
    except Exception:
        return None

def get_transcript_youtube_api(video_id):
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        captions = youtube.captions().list(part="id", videoId=video_id).execute()
        caption_items = captions.get("items", [])
        if not caption_items:
            return None
        caption_id = caption_items[0]["id"]
        caption = youtube.captions().download(id=caption_id).execute()
        return caption.get("body", "").strip()
    except Exception as e:
        print("YouTube API error:", e)
        return None

def get_transcript_yt_dlp(video_url):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'cookiefile': 'cookies.txt',
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            subtitles = info.get('automatic_captions', {}).get('en')
            if not subtitles:
                return None

            for sub in subtitles:
                if sub.get('ext') == 'vtt':
                    response = requests.get(sub['url'])
                    if response.ok:
                        return response.text.replace('\n', ' ').strip()
        return None
    except Exception as e:
        print("yt-dlp error:", e)
        return None

def generate_fact_check(transcript):
    client = genai.Client(
        vertexai=True,
        project="skillful-cider-451510-j7",
        location="us-central1"
    )

    prompt = f"""
You are a fact-checking AI. Extract news-related claims from the following transcript, verify their accuracy, and respond in JSON format:
{{
  "claims": ["claim 1", "claim 2", ...],
  "verdicts": ["true", "false", "misleading", ...]
}}

Transcript:
\"\"\"
{transcript}
\"\"\"
"""

    model = "gemini-2.5-pro-exp-03-25"
    contents = [genai.types.Content(role="user", parts=[genai.types.Part.from_text(prompt)])]
    tools = [genai.types.Tool(google_search=genai.types.GoogleSearch())]
    config = genai.types.GenerateContentConfig(
        temperature=0,
        top_p=1,
        seed=0,
        max_output_tokens=4096,
        response_modalities=["TEXT"],
        tools=tools,
        system_instruction=[genai.types.Part.from_text("You are a precise fact-checker.")]
    )

    response_text = ""
    for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
            response_text += chunk.text

    return response_text.strip()
