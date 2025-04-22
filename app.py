import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from backend import (
    get_video_id,
    get_transcript,
    get_transcript_youtube_api,
    generate_fact_check
)

app = Flask(__name__)

# Allow your extension or localhost to call
origins = os.environ.get("CORS_ORIGINS",
                         "chrome-extension://pohnlnkideolhcmndnnddepnboapnhpm")
CORS(app, origins=origins)

@app.route("/", methods=["GET"])
def index():
    return "✅ VerifyTube Backend is running!", 200

@app.route("/fact-check", methods=["POST"])
def fact_check():
    data = request.get_json() or {}
    video_url = data.get("url", "").strip()
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    vid = get_video_id(video_url)
    if not vid:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    # Try transcripts
    transcript = get_transcript(vid)
    if not transcript:
        transcript = get_transcript_youtube_api(vid)
    if not transcript:
        return jsonify({"error": "Could not retrieve transcript"}), 500

    # Run fact-check
    try:
        result = generate_fact_check(transcript)
        # result is already a dict with keys "claims" and "verdicts"
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Internal error: {e}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
