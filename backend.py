import re
import os
import requests
from googleapiclient.discovery import build
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

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
        api_key = os.environ.get("YOUTUBE_API_KEY")
        print("[INFO] YOUTUBE_API_KEY present:", bool(api_key))
        if not api_key:
            return None

        youtube = build("youtube", "v3", developerKey=api_key)
        print("[INFO] YouTube API client initialized.")

        captions = youtube.captions().list(part="snippet", videoId=video_id).execute()
        print("[INFO] Captions fetched:", captions)

        if not captions.get("items"):
            print("[INFO] No caption items found.")
            return None

        caption_id = captions["items"][0]["id"]
        print("[INFO] Caption ID:", caption_id)

        caption_response = youtube.captions().download(id=caption_id).execute()
        return caption_response.decode("utf-8")

    except Exception as e:
        print("[ERROR] YouTube API Exception:", str(e))
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
