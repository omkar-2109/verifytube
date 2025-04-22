import os
import re
import json
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import google.generativeai as genai

# Vertex AI configuration
GENAI_PROJECT  = os.environ.get("GCP_PROJECT",  "skillful-cider-451510-j7")
GENAI_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

def get_video_id(url: str) -> str | None:
    """Extract the 11‑char YouTube video ID."""
    m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return m.group(1) if m else None

def get_transcript(video_id: str) -> str | None:
    """
    Uses youtube-transcript-api to fetch English auto‑sub or manual sub.
    Returns the joined text or None.
    """
    for lang in ["en", "en-US", "hi"]:
        try:
            subs = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
            return " ".join(entry["text"] for entry in subs)
        except TranscriptsDisabled:
            # auto‑sub disabled, try next
            return None
        except Exception:
            # no manual or auto for this lang, try next
            continue
    return None

def generate_fact_check(transcript: str) -> dict:
    """
    Calls Gemini to extract & verify claims.
    Returns a dict: {"claims": [...], "verdicts": [...]}
    """
    client = genai.Client(
        vertexai=True,
        project=GENAI_PROJECT,
        location=GENAI_LOCATION
    )

    prompt = f"""
You are a fact‑checking AI. From the transcript below, extract ONLY news‑related claims,
verify each claim’s accuracy, and output EXACTLY a JSON object:

{{
  "claims": ["…"],
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
        system_instruction=[genai.types.Part.from_text("You are a precise fact‑checker.")]
    )

    # collect the streamed text
    out = ""
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-pro-exp-03-25",
        contents=contents,
        config=cfg
    ):
        out += chunk.text

    # parse to JSON
    try:
        return json.loads(out.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from AI: {e}\nOutput was:\n{out}")
