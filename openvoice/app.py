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

# Paths to OpenVoice model checkpoints (adjust as per your setup)
base_speaker_model = "checkpoints/base_speaker.pth"
tone_color_converter_model = "checkpoints/converter.pth"

# Initialize OpenVoice models
device = "cuda" if torch.cuda.is_available() else "cpu"
tone_color_converter = ToneColorConverter(tone_color_converter_model, device=device)

# Reference speaker audio
reference_speaker_audio = "temp_audio/reference_speaker.wav"

@app.route('/')
def index():
    return send_static_file('code.html')

@app.route('/api/voice/test', methods=['GET'])
def voice_test():
    try:
        # Get query parameters
        text = request.args.get('text', 'Hello, this is a test voice synthesis.')
        output_file = os.path.join(app.config['STATIC_FOLDER'], 'output.wav')

        # Extract tone color from reference speaker
        se, _ = seextractor.extract(reference_speaker_audio, device=device)

        # Generate audio using OpenVoice
        audio, sr = tone_color_converter.convert(
            text=text,
            source_se=se,
            target_se=se,
            output_path=output_file
        )

        # Save the generated audio
        sf.write(output_file, audio, sr)

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
