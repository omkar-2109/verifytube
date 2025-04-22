import os
import re
import json
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from googleapiclient.discovery import build
import google.generativeai as genai

# Load YouTube Data API key from env
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Configure Vertex AI
GENAI_PROJECT  = os.environ.get("GCP_PROJECT", "skillful-cider-451510-j7")
GENAI_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

def get_video_id(url: str) -> str | None:
    """Extract the 11‐char YouTube video ID from a URL."""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    m = re.search(pattern, url)
    return m.group(1) if m else None

def get_transcript(video_id: str) -> str | None:
    """Try official YouTube Transcript API (auto or manual subs)."""
    try:
        subs = YouTubeTranscriptApi.get_transcript(video_id, languages=["en-US"])
        return " ".join(entry["text"] for entry in subs)
    except TranscriptsDisabled:
        return None
    except Exception:
        # fallback to Hindi or any
        try:
            subs = YouTubeTranscriptApi.get_transcript(video_id, languages=["hi"])
            return " ".join(entry["text"] for entry in subs)
        except Exception:
            return None

def get_transcript_youtube_api(video_id: str) -> str | None:
    """Use YouTube Data v3 to list & download captions (requires OAuth)."""
    if not YOUTUBE_API_KEY:
        return None

    yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    resp = yt.captions().list(part="snippet", videoId=video_id).execute()
    items = resp.get("items", [])
    if not items:
        return None

    caption_id = items[0]["id"]
    # This call requires OAuth; with API key only it will error out
    try:
        dl = yt.captions().download(id=caption_id).execute()
        return dl.decode("utf-8")
    except Exception:
        return None

def generate_fact_check(transcript: str) -> dict:
    """
    Call Gemini to extract and verify claims.
    Returns a Python dict: {"claims": [...], "verdicts": [...]}
    """
    client = genai.Client(
        vertexai=True,
        project=GENAI_PROJECT,
        location=GENAI_LOCATION,
    )

    prompt = f"""
You are a fact‑checking AI. From the transcript below, extract ONLY news-related claims,
verify each claim’s accuracy, and output EXACTLY a JSON object:

{{
  "claims": ["..."],
  "verdicts": ["true"|"false"|"misleading"|…]
}}

Transcript:
\"\"\"{transcript}\"\"\"
"""

    contents = [
        genai.types.Content(
            role="user",
            parts=[genai.types.Part.from_text(prompt)]
        )
    ]
    tools = [genai.types.Tool(google_search=genai.types.GoogleSearch())]
    cfg = genai.types.GenerateContentConfig(
        temperature=0,
        top_p=1,
        max_output_tokens=4096,
        response_modalities=["TEXT"],
        tools=tools,
        system_instruction=[genai.types.Part.from_text("You are a precise fact-checker.")]
    )

    # Stream the response into one string
    text_out = ""
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-pro-exp-03-25",
        contents=contents,
        config=cfg
    ):
        text_out += chunk.text

    # Attempt to parse into JSON
    try:
        return json.loads(text_out.strip())
    except json.JSONDecodeError as e:
        # If the model’s output was slightly malformed, you could
        # try some cleanup here. For now, bubble up an error.
        raise ValueError(f"Invalid JSON from AI: {e}\n\nOutput was:\n{text_out}")

