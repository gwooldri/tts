# voice_service.py
import os
import sys
import tempfile
import uuid
from pathlib import Path
import torch
import torchaudio
import subprocess

class VoiceCloner:
    def __init__(self):
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(exist_ok=True)
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        # Initialize OpenVoice on first run
        self.openvoice_ready = False
        self.setup_openvoice()
    
    def setup_openvoice(self):
        """Set up OpenVoice for Railway deployment"""
        try:
            # Check if OpenVoice is already installed
            if not os.path.exists("OpenVoice"):
                print("Installing OpenVoice...")
                subprocess.run(["git", "clone", "https://github.com/myshell-ai/OpenVoice.git"], check=True)
                subprocess.run(["pip", "install", "-e", "./OpenVoice"], check=True)
            
            # Add OpenVoice to path
            sys.path.append("./OpenVoice")
            
            # Try to import OpenVoice
            from openvoice import se_extractor
            from openvoice.api import BaseSpeakerTTS, ToneColorConverter
            
            # Download models if needed
            self.download_models()
            
            # Initialize models
            if self.check_models():
                self.initialize_models()
            
        except Exception as e:
            print(f"OpenVoice setup failed: {e}")
            print("Running in placeholder mode")
    
    def download_models(self):
        """Download model files"""
        import requests
        
        checkpoints_dir = Path("checkpoints")
        checkpoints_dir.mkdir(exist_ok=True)
        
        base_speakers_dir = checkpoints_dir / "base_speakers" / "EN"
        converter_dir = checkpoints_dir / "converter"
        
        base_speakers_dir.mkdir(parents=True, exist_ok=True)
        converter_dir.mkdir(parents=True, exist_ok=True)
        
        models = {
            "checkpoints/base_speakers/EN/config.json": "https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/basespeakers/EN/config.json",
            "checkpoints/base_speakers/EN/checkpoint.pth": "https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/basespeakers/EN/checkpoint.pth",
            "checkpoints/converter/config.json": "https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/converter/config.json",
            "checkpoints/converter/checkpoint.pth": "https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/converter/checkpoint.pth",
        }
        
        for local_path, url in models.items():
            if not os.path.exists(local_path):
                try:
                    print(f"Downloading {local_path}...")
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Downloaded {local_path}")
                except Exception as e:
                    print(f"Failed to download {local_path}: {e}")
    
    def check_models(self):
        """Check if all model files exist"""
        required_files = [
            "checkpoints/base_speakers/EN/config.json",
            "checkpoints/base_speakers/EN/checkpoint.pth",
            "checkpoints/converter/config.json",
            "checkpoints/converter/checkpoint.pth"
        ]
        
        return all(os.path.exists(f) for f in required_files)
    
    def initialize_models(self):
        """Initialize OpenVoice models"""
        try:
            from openvoice import se_extractor
            from openvoice.api import BaseSpeakerTTS, ToneColorConverter
            
            self.base_speaker_tts = BaseSpeakerTTS(
                'checkpoints/base_speakers/EN/config.json', 
                device=self.device
            )
            self.base_speaker_tts.load_ckpt('checkpoints/base_speakers/EN/checkpoint.pth')
            
            self.tone_color_converter = ToneColorConverter(
                'checkpoints/converter/config.json', 
                device=self.device
            )
            self.tone_color_converter.load_ckpt('checkpoints/converter/checkpoint.pth')
            
            self.openvoice_ready = True
            print("OpenVoice models loaded successfully!")
            
        except Exception as e:
            print(f"Failed to initialize models: {e}")
            self.openvoice_ready = False
    
    def save_uploaded_audio(self, audio_file):
        """Save uploaded audio file"""
        filename = f"{uuid.uuid4()}.wav"
        filepath = self.temp_dir / filename
        audio_file.save(str(filepath))
        return str(filepath)
    
    def clone_voice(self, text, reference_audio_path):
        """Clone voice"""
        if self.openvoice_ready:
            return self.clone_with_openvoice(text, reference_audio_path)
        else:
            return self.create_placeholder_audio(text)
    
    def clone_with_openvoice(self, text, reference_audio_path):
        """Real voice cloning with OpenVoice"""
        try:
            from openvoice import se_extractor
            
            # Generate base audio
            temp_base = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_base.close()
            
            self.base_speaker_tts.tts(
                text, temp_base.name, speaker='default', language='English'
            )
            
            # Extract voice characteristics
            target_se, _ = se_extractor.get_se(
                reference_audio_path, self.tone_color_converter, vad=True
            )
            
            # Convert voice
            output_path = self.temp_dir / f"cloned_{uuid.uuid4()}.wav"
            source_se = torch.load('checkpoints/base_speakers/EN/en_default_se.pth', map_location=self.device)
            
            self.tone_color_converter.convert(
                audio_src_path=temp_base.name,
                src_se=source_se,
                tgt_se=target_se,
                output_path=str(output_path),
                message="@MyShell"
            )
            
            os.unlink(temp_base.name)
            return str(output_path)
            
        except Exception as e:
            print(f"OpenVoice cloning failed: {e}")
            return self.create_placeholder_audio(text)
    
    def create_placeholder_audio(self, text):
        """Create placeholder audio"""
        import numpy as np
        
        sample_rate = 22050
        duration = min(len(text) * 0.1, 10)
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        
        output_path = self.temp_dir / f"placeholder_{uuid.uuid4()}.wav"
        audio_tensor = torch.FloatTensor(audio).unsqueeze(0)
        torchaudio.save(str(output_path), audio_tensor, sample_rate)
        
        return str(output_path)
    
    def cleanup_file(self, filepath):
        """Clean up files"""
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass

# Global instance
voice_cloner = VoiceCloner()