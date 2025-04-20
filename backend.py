import re
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from yt_dlp import YoutubeDL

def get_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript(video_id):
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
                print("No subtitles found in info dict.")
                return None

            # Download subtitles manually using requested URL
            for sub in subtitles:
                if sub.get('ext') == 'vtt':
                    import requests
                    response = requests.get(sub['url'])
                    if response.ok:
                        return response.text

        return None
    except Exception as e:
        print("Error fetching transcript using yt-dlp with cookies:", e)
        return None

def generate_fact_check(transcript):
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
        system_instruction=[types.Part.from_text(text="You are a precise fact-checker. Extract only news claims.")],
    )

    for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
        if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
            continue
        print(chunk.text, end="")
