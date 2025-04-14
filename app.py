
import os
from flask import Flask, request, jsonify
from backend import get_video_id, get_transcript, get_transcript_yt_dlp, generate_fact_check

app = Flask(__name__)
application = app  # for gunicorn

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    url = data.get('text')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    video_id = get_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    transcript = get_transcript(video_id)
    if not transcript:
        transcript = get_transcript_yt_dlp(url)

    if not transcript:
        return jsonify({'error': 'Transcript could not be fetched'}), 500
    
    return jsonify({'transcript': transcript})  # Replace with Gemini response if needed

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
