from flask import Flask, request, jsonify, send_static_file
import os
import soundfile as sf
import librosa
import torch
from openvoice import seextractor
from openvoice.api import ToneColorConverter
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['STATIC_FOLDER'] = 'static'
app.config['TEMP_AUDIO_FOLDER'] = 'temp_audio'

# Ensure temp_audio and static folders exist
os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_AUDIO_FOLDER'], exist_ok=True)

# Paths to OpenVoice model checkpoints (adjust as per your setup)
base_speaker_model = "checkpoints/base_speaker.pth"
tone_color_converter_model = "checkpoints/converter.pth"

# Initialize OpenVoice models
device = "cuda" if torch.cuda.is_available() else "cpu"
tone_color_converter = ToneColorConverter(tone_color_converter_model, device=device)

@app.route('/')
def index():
    return send_static_file('code.html')

@app.route('/api/voice/test', methods=['POST'])
def voice_test():
    try:
        # Get text input from the form
        text = request.form.get('text', 'Hello, this is a test voice synthesis.')
        
        # Check if an audio file was uploaded
        if 'audio' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No audio file provided'
            }), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No audio file selected'
            }), 400

        # Save the uploaded audio file temporarily
        reference_audio_path = os.path.join(app.config['TEMP_AUDIO_FOLDER'], 'uploaded_reference.wav')
        audio_file.save(reference_audio_path)

        # Extract tone color from the uploaded reference audio
        se, _ = seextractor.extract(reference_audio_path, device=device)

        # Generate audio using OpenVoice
        output_file = os.path.join(app.config['STATIC_FOLDER'], 'output.wav')
        audio, sr = tone_color_converter.convert(
            text=text,
            source_se=se,
            target_se=se,  # Using same speaker for simplicity
            output_path=output_file
        )

        # Save the generated audio
        sf.write(output_file, audio, sr)

        # Clean up the temporary reference audio file (optional)
        os.remove(reference_audio_path)

        # Return response
        return jsonify({
            'status': 'success',
            'message': 'Audio generated successfully',
            'audio_url': f'/{output_file}'
        })

    except Exception as e:
        logging.error(f"Error in voice_test: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
