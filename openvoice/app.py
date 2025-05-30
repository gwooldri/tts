from flask import Flask, request, jsonify, send_file
from flask_cors import CORS  # Add this import
from werkzeug.utils import secure_filename
from voice_service import voice_cloner
import os
import logging

app = Flask(__name__)
# Configure CORS to accept requests from your frontend domain
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "https://your-frontend-domain.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

voice_cloner = VoiceCloner()  # Initialize the voice cloner

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return jsonify({'status': 'API is running'})

@app.route('/api/voice/clone', methods=['POST'])
def clone_voice_api():
    try:
        logger.debug(f"Received request: {request.files}, {request.form}")
        
        text = request.form.get('text')
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        if 'audio' not in request.files:
            return jsonify({'error': 'Audio file is required'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Process the audio
        reference_path = voice_cloner.save_uploaded_audio(audio_file)
        output_path = voice_cloner.clone_voice(text, reference_path)
        
        # Cleanup
        voice_cloner.cleanup_file(reference_path)
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name='cloned_voice.wav',
            mimetype='audio/wav'
        )
        
    except Exception as e:
        logger.error(f"Error in clone_voice_api: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/test', methods=['GET'])
def test_voice_service():
    return jsonify({
        'message': 'Voice cloning service is running!',
        'openvoice_ready': voice_cloner.openvoice_ready,
        'device': voice_cloner.device
    })

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway uses port 8080
    app.run(host="0.0.0.0", port=port)