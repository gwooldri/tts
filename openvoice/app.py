from flask import Flask
app = Flask(__name__)
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from voice_service import voice_cloner
import os

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Basic health check route
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'Voice cloning service is running!',
        'endpoints': [
            '/api/voice/test',
            '/api/voice/clone'
        ]
    })

@app.route('/api/voice/clone', methods=['POST'])
def clone_voice_api():
    try:
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
        print(f"Voice cloning error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/test', methods=['GET'])
def test_voice_service():
    return jsonify({
        'message': 'Voice cloning service is running!',
        'openvoice_ready': voice_cloner.openvoice_ready,
        'device': voice_cloner.device
    })

if __name__ == '__main__':
    # Railway sets the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
