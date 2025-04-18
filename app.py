from flask import Flask, request, jsonify
from flask_cors import CORS
from backend import get_video_id, get_transcript, get_transcript_yt_dlp, generate_fact_check

app = Flask(__name__)
CORS(app, origins="chrome-extension://pohnlnkideolhcmndnnddepnboapnhpm")

@app.route("/")
def index():
    return "VerifyTube Backend is running!"

@app.route("/fact-check", methods=["POST"])
def fact_check():
    data = request.get_json()
    video_url = data.get("url")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    video_id = get_video_id(video_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    transcript = get_transcript(video_id)
    if not transcript:
        transcript = get_transcript_yt_dlp(video_url)

    if not transcript:
        return jsonify({"error": "Could not retrieve transcript"}), 500

    result = generate_fact_check(transcript)
    return jsonify({"result": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
