from flask import Flask, request, jsonify, send_file, send_static_file
from werkzeug.utils import secure_filename
from voice_service import voice_cloner
import os
import logging

# Set up logging to a file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.config['STATIC_FOLDER'] = 'static'
app.config['TEMP_AUDIO_FOLDER'] = 'temp_audio'

# Ensure static and temp_audio folders exist
os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_AUDIO_FOLDER'], exist_ok=True)

# Verify voice_cloner initialization
try:
    if not voice_cloner.openvoice_ready:
        raise RuntimeError("OpenVoice is not ready")
    logging.info(f"Voice cloning service initialized. Device: {voice_cloner.device}")
except Exception as e:
    logging.error(f"Failed to initialize voice_cloner: {str(e)}")
    raise RuntimeError(f"Voice cloning service initialization failed: {str(e)}")

@app.route('/')
def index():
    try:
        return send_static_file('code.html')
    except Exception as e:
        logging.error(f"Error serving code.html: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to serve the frontend page'
        }), 500

@app.route('/api/voice/clone', methods=['POST'])
def clone_voice_api():
    try:
        text = request.form.get('text')
        if not text:
            logging.warning("Text is required but not provided")
            return jsonify({'error': 'Text is required'}), 400
        
        if 'audio' not in request.files:
            logging.warning("Audio file is required but not provided")
            return jsonify({'error': 'Audio file is required'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            logging.warning("No audio file selected")
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Process the audio
        reference_path = voice_cloner.save_uploaded_audio(audio_file)
        logging.debug(f"Uploaded audio saved to: {reference_path}")
        
        output_path = voice_cloner.clone_voice(text, reference_path)
        logging.debug(f"Cloned audio saved to: {output_path}")
        
        # Cleanup
        voice_cloner.cleanup_file(reference_path)
        logging.debug("Temporary reference audio file cleaned up")
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name='cloned_voice.wav',
            mimetype='audio/wav'
        )
        
    except Exception as e:
        logging.error(f"Voice cloning error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/test', methods=['GET'])
def test_voice_service():
    try:
        return jsonify({
            'message': 'Voice cloning service is running!',
            'openvoice_ready': voice_cloner.openvoice_ready,
            'device': voice_cloner.device
        })
    except Exception as e:
        logging.error(f"Error in test_voice_service: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to access voice service: {str(e)}'
        }), 500

# Global error handler to ensure JSON responses
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({
        'status': 'error',
        'message': f'Server error: {str(e)}'
    }), 500

if __name__ == '__main__':
    app.run(debug=False)  # Disable debug mode in production
