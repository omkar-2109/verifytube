import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from backend import get_video_id, get_transcript, generate_fact_check

app = Flask(__name__)
CORS(app, origins=os.environ.get(
    "CORS_ORIGINS",
    "chrome-extension://pohnlnkideolhcmndnnddepnboapnhpm"
))

@app.route("/", methods=["GET"])
def index():
    return "✅ VerifyTube Backend is running!", 200

@app.route("/fact-check", methods=["POST"])
def fact_check():
    data = request.get_json() or {}
    url  = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    vid = get_video_id(url)
    if not vid:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    transcript = get_transcript(vid)
    if not transcript:
        return jsonify({"error": "Could not retrieve transcript"}), 500

    try:
        payload = generate_fact_check(transcript)
        # payload is {"claims":[…],"verdicts":[…]}
        return jsonify(payload), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Internal error: {e}"}), 500

if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "false") == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
