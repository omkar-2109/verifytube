from flask import Flask, request, jsonify
from flask_cors import CORS
from backend import (
    get_video_id,
    get_transcript_youtube_api,
    generate_fact_check
)

app = Flask(__name__)
CORS(app, origins="chrome-extension://pohnlnkideolhcmndnnddepnboapnhpm")

@app.route("/")
def index():
    return "✅ VerifyTube Backend is running!"

@app.route("/fact-check", methods=["POST"])
def fact_check():
    try:
        data = request.get_json()
        video_url = data.get("url")
        print("[INFO] Received URL:", video_url)

        if not video_url:
            return jsonify({"error": "No URL provided"}), 400

        video_id = get_video_id(video_url)
        print("[INFO] Extracted video ID:", video_id)

        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        transcript = get_transcript(video_id)
        print("[INFO] Got transcript from youtube_transcript_api:", bool(transcript))

        if not transcript:
            transcript = get_transcript_youtube_api(video_id)
            print("[INFO] Got transcript from YouTube API:", bool(transcript))

        if not transcript:
            return jsonify({"error": "Could not retrieve transcript"}), 500

        result = generate_fact_check(transcript)
        print("[INFO] Gemini result:", result[:100])  # just first 100 chars

        return jsonify({"result": result})

    except Exception as e:
        import traceback
        print("[ERROR] Exception occurred:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/debug")
def debug():
    return jsonify({
        "status": "ok",
        "youtube_api_key": bool(os.environ.get("YOUTUBE_API_KEY")),
        "genai_configured": hasattr(genai, "Client")
    })


# Optional: remove this block if using gunicorn
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
