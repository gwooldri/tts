#!/usr/bin/env python3
"""
Edge TTS API Server
A Flask-based REST API server for Microsoft Edge Text-to-Speech
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import edge_tts
import asyncio
import io
import os
import tempfile
import logging
from datetime import datetime

# Edge TTS API endpoint (used internally by edge-tts)
EDGE_TTS_API_ENDPOINT = "wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1"

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EdgeTTSServer:
    def __init__(self):
        self.voices = None
        
    async def get_voices(self):
        """Get available voices from Edge TTS"""
        if self.voices is None:
            voices = await edge_tts.list_voices()
            self.voices = [
                {
                    'name': voice['Name'],
                    'short_name': voice['ShortName'],
                    'gender': voice['Gender'],
                    'locale': voice['Locale'],
                    'language': voice['Locale'].split('-')[0],
                    'country': voice['Locale'].split('-')[1] if '-' in voice['Locale'] else '',
                    'display_name': voice['FriendlyName']
                }
                for voice in voices
            ]
        return self.voices
    
    async def synthesize_speech(self, text, voice="en-US-AriaNeural", rate="+0%", pitch="+0Hz", volume="+0%"):
        """Synthesize speech using Edge TTS"""
        try:
            # Create TTS communicator
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
            
            # Generate audio data
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            return audio_data
        except Exception as e:
            logger.error(f"TTS synthesis error: {str(e)}")
            raise

# Initialize the TTS server
tts_server = EdgeTTSServer()

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Edge TTS API Server',
        'timestamp': datetime.now().isoformat(),
        'edge_tts_endpoint': EDGE_TTS_API_ENDPOINT
    })

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get all available voices"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        voices = loop.run_until_complete(tts_server.get_voices())
        loop.close()
        
        # Optional filtering by language
        lang = request.args.get('lang')
        if lang:
            voices = [v for v in voices if v['language'].lower() == lang.lower()]
        
        return jsonify({
            'voices': voices,
            'count': len(voices)
        })
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """Convert text to speech"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        voice = data.get('voice', 'en-US-AriaNeural')
        rate = data.get('rate', '+0%')
        pitch = data.get('pitch', '+0Hz')
        volume = data.get('volume', '+0%')
        output_format = data.get('format', 'mp3').lower()
        
        # Validate parameters
        if len(text) > 10000:  # Reasonable limit
            return jsonify({'error': 'Text too long (max 10000 characters)'}), 400
        
        # Synthesize speech
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(
            tts_server.synthesize_speech(text, voice, rate, pitch, volume)
        )
        loop.close()
        
        if not audio_data:
            return jsonify({'error': 'Failed to generate audio'}), 500
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{output_format}') as tmp_file:
            tmp_file.write(audio_data)
            tmp_file_path = tmp_file.name
        
        # Return audio file
        def remove_file(response):
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass
            return response
        
        return send_file(
            tmp_file_path,
            mimetype=f'audio/{output_format}',
            as_attachment=True,
            download_name=f'tts_output.{output_format}'
        )
        
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/tts/stream', methods=['POST'])
def text_to_speech_base64():
    """Convert text to speech and return as base64"""
    try:
        import base64
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        voice = data.get('voice', 'en-US-AriaNeural')
        rate = data.get('rate', '+0%')
        pitch = data.get('pitch', '+0Hz')
        volume = data.get('volume', '+0%')
        
        # Synthesize speech
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(
            tts_server.synthesize_speech(text, voice, rate, pitch, volume)
        )
        loop.close()
        
        if not audio_data:
            return jsonify({'error': 'Failed to generate audio'}), 500
        
        # Encode as base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
            'audio': audio_base64,
            'format': 'mp3',
            'size': len(audio_data),
            'text': text,
            'voice': voice
        })
        
    except Exception as e:
        logger.error(f"TTS streaming error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/voices/search', methods=['GET'])
def search_voices():
    """Search voices by criteria"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        voices = loop.run_until_complete(tts_server.get_voices())
        loop.close()
        
        # Get search parameters
        query = request.args.get('q', '').lower()
        gender = request.args.get('gender', '').lower()
        language = request.args.get('language', '').lower()
        
        # Filter voices
        filtered_voices = voices
        
        if query:
            filtered_voices = [
                v for v in filtered_voices 
                if query in v['display_name'].lower() or query in v['locale'].lower()
            ]
        
        if gender:
            filtered_voices = [v for v in filtered_voices if v['gender'].lower() == gender]
        
        if language:
            filtered_voices = [v for v in filtered_voices if v['language'].lower() == language]
        
        return jsonify({
            'voices': filtered_voices,
            'count': len(filtered_voices),
            'query': {
                'text': query if query else None,
                'gender': gender if gender else None,
                'language': language if language else None
            }
        })
        
    except Exception as e:
        logger.error(f"Voice search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/endpoint', methods=['GET'])
def get_edge_endpoint():
    """Get the Edge TTS API endpoint"""
    return jsonify({
        'endpoint': EDGE_TTS_API_ENDPOINT,
        'type': 'websocket',
        'description': 'Microsoft Edge internal TTS WebSocket endpoint'
    })

if __name__ == '__main__':
    print("Starting Edge TTS API Server...")
    print("Available endpoints:")
    print("  GET  /           - Health check")
    print("  GET  /voices     - List all voices")
    print("  GET  /voices/search - Search voices")
    print("  POST /tts        - Text to speech (returns audio file)")
    print("  POST /tts/stream - Text to speech (returns base64)")
    print()
    
    # Run the server
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=5000,
        debug=True,
        threaded=True
    )