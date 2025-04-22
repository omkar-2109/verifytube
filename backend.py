import os
import re
import json
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# GCP / Vertex AI config via env‑vars
GENAI_PROJECT  = os.environ.get("GCP_PROJECT",  "skillful-cider-451510-j7")
GENAI_LOCATION = os.environ.get("GCP_LOCATION", "us‑central1")

def get_video_id(url: str) -> str | None:
    m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    return m[1] if m else None

def get_transcript(video_id: str) -> str | None:
    """
    Try to fetch any available transcript (auto or manual) via youtube‑transcript‑api.
    """
    try:
        subs = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(item["text"] for item in subs)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        print(f"[WARN] No transcript for {video_id}: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Transcript fetch error for {video_id}: {e}")
        return None

def generate_fact_check(transcript: str) -> dict:
    """
    Send transcript into Gemini for fact‑checking, return JSON dict.
    """
    client = genai.Client(
        vertexai=True,
        project=GENAI_PROJECT,
        location=GENAI_LOCATION,
    )

    prompt = f"""
You are a fact‑checking AI.  Extract ONLY news‑related claims from the transcript below,
verify each claim, and output EXACTLY a JSON object:

{{
  "claims": ["…"],
  "verdicts": ["true"|"false"|"misleading"|…]
}}

Transcript:
\"\"\"{transcript}\"\"\"
"""
    # build the request
    contents = [genai.types.Content(role="user", parts=[genai.types.Part.from_text(prompt)])]
    tools    = [genai.types.Tool(google_search=genai.types.GoogleSearch())]
    config   = genai.types.GenerateContentConfig(
        temperature=0,
        top_p=1,
        seed=0,
        max_output_tokens=4096,
        response_modalities=["TEXT"],
        tools=tools,
        system_instruction=[genai.types.Part.from_text("You are a precise fact‑checker.")]
    )

    # stream & accumulate
    out = ""
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-pro-exp-03-25",
        contents=contents,
        config=config
    ):
        out += chunk.text

    # parse JSON
    try:
        return json.loads(out.strip())
    except Exception as e:
        raise ValueError(f"AI output is not valid JSON: {e}\n---\n{out}")
