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
            # Check if OpenVoice is properly installed
            openvoice_path = None
            
            # Check if OpenVoice folder exists and has content
            if os.path.exists("OpenVoice") and os.path.exists("OpenVoice/openvoice"):
                print("Found existing OpenVoice installation")
                openvoice_path = "./OpenVoice"
            elif os.path.exists("openvoice") and len(os.listdir("openvoice")) > 1:  # More than just .gitkeep
                print("Found existing openvoice installation")
                openvoice_path = "./openvoice"
            else:
                print("OpenVoice not found, installing...")
                # Clone OpenVoice repository
                result = subprocess.run(["git", "clone", "https://github.com/myshell-ai/OpenVoice.git"], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Git clone failed: {result.stderr}")
                    raise Exception("Failed to clone OpenVoice")
                
                openvoice_path = "./OpenVoice"
                
                # Install OpenVoice
                install_result = subprocess.run(["pip", "install", "-e", openvoice_path], 
                                              capture_output=True, text=True)
                if install_result.returncode != 0:
                    print(f"Installation failed: {install_result.stderr}")
                    raise Exception("Failed to install OpenVoice")
                
                print("OpenVoice cloned and installed successfully")
            
            # Add to Python path
            if openvoice_path:
                sys.path.insert(0, openvoice_path)
                print(f"Added {openvoice_path} to Python path")
            
            # Try to import OpenVoice modules
            try:
                from openvoice import se_extractor
                from openvoice.api import BaseSpeakerTTS, ToneColorConverter
                print("✅ OpenVoice modules imported successfully")
            except ImportError as e:
                print(f"Import failed: {e}")
                # If import fails, try installing again
                if openvoice_path and os.path.exists(openvoice_path):
                    subprocess.run(["pip", "install", "-e", openvoice_path], check=True)
                    from openvoice import se_extractor
                    from openvoice.api import BaseSpeakerTTS, ToneColorConverter
                    print("✅ OpenVoice installed and imported on second attempt")
                else:
                    raise
            
            # Download models if needed
            print("Checking for model files...")
            self.download_models()
            
            # Initialize models
            if self.check_models():
                print("Model files found, initializing...")
                self.initialize_models()
            else:
                print("⚠️ Model files missing, running in placeholder mode")
            
        except Exception as e:
            print(f"❌ OpenVoice setup failed: {e}")
            print("Running in placeholder mode")
            import traceback
            traceback.print_exc()
    
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
                    response = requests.get(url, stream=True, timeout=120)
                    response.raise_for_status()
                    
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"✅ Downloaded {local_path}")
                except Exception as e:
                    print(f"❌ Failed to download {local_path}: {e}")
            else:
                print(f"✅ {local_path} already exists")
    
    def check_models(self):
        """Check if all model files exist"""
        required_files = [
            "checkpoints/base_speakers/EN/config.json",
            "checkpoints/base_speakers/EN/checkpoint.pth",
            "checkpoints/converter/config.json",
            "checkpoints/converter/checkpoint.pth"
        ]
        
        missing_files = [f for f in required_files if not os.path.exists(f)]
        if missing_files:
            print(f"Missing model files: {missing_files}")
            return False
        print("✅ All model files present")
        return True
    
    def initialize_models(self):
        """Initialize OpenVoice models"""
        try:
            from openvoice import se_extractor
            from openvoice.api import BaseSpeakerTTS, ToneColorConverter
            
            print("Initializing BaseSpeakerTTS...")
            self.base_speaker_tts = BaseSpeakerTTS(
                'checkpoints/base_speakers/EN/config.json', 
                device=self.device
            )
            self.base_speaker_tts.load_ckpt('checkpoints/base_speakers/EN/checkpoint.pth')
            print("✅ BaseSpeakerTTS initialized")
            
            print("Initializing ToneColorConverter...")
            self.tone_color_converter = ToneColorConverter(
                'checkpoints/converter/config.json', 
                device=self.device
            )
            self.tone_color_converter.load_ckpt('checkpoints/converter/checkpoint.pth')
            print("✅ ToneColorConverter initialized")
            
            self.openvoice_ready = True
            print("🎉 OpenVoice models loaded successfully!")
            
        except Exception as e:
            print(f"❌ Failed to initialize models: {e}")
            import traceback
            traceback.print_exc()
            self.openvoice_ready = False
    
    def save_uploaded_audio(self, audio_file):
        """Save uploaded audio file"""
        filename = f"{uuid.uuid4()}.wav"
        filepath = self.temp_dir / filename
        audio_file.save(str(filepath))
        print(f"Saved uploaded audio to: {filepath}")
        return str(filepath)
    
    def clone_voice(self, text, reference_audio_path):
        """Clone voice"""
        print(f"Cloning voice for text: '{text[:50]}...'")
        if self.openvoice_ready:
            return self.clone_with_openvoice(text, reference_audio_path)
        else:
            print("Using placeholder audio (OpenVoice not ready)")
            return self.create_placeholder_audio(text)
    
    def clone_with_openvoice(self, text, reference_audio_path):
        """Real voice cloning with OpenVoice"""
        try:
            from openvoice import se_extractor
            
            print("Generating base audio...")
            # Generate base audio
            temp_base = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_base.close()
            
            self.base_speaker_tts.tts(
                text, temp_base.name, speaker='default', language='English'
            )
            print("✅ Base audio generated")
            
            print("Extracting voice characteristics...")
            # Extract voice characteristics
            target_se, _ = se_extractor.get_se(
                reference_audio_path, self.tone_color_converter, vad=True
            )
            print("✅ Voice characteristics extracted")
            
            print("Converting voice...")
            # Convert voice
            output_path = self.temp_dir / f"cloned_{uuid.uuid4()}.wav"
            
            # Check if default speaker embedding exists
            default_se_path = 'checkpoints/base_speakers/EN/en_default_se.pth'
            if os.path.exists(default_se_path):
                source_se = torch.load(default_se_path, map_location=self.device)
            else:
                # Create a default embedding if not found
                print("Default speaker embedding not found, using zero embedding")
                source_se = torch.zeros(256, device=self.device)
            
            self.tone_color_converter.convert(
                audio_src_path=temp_base.name,
                src_se=source_se,
                tgt_se=target_se,
                output_path=str(output_path),
                message="@MyShell"
            )
            
            # Cleanup temporary file
            os.unlink(temp_base.name)
            print(f"✅ Voice cloning completed: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"❌ OpenVoice cloning failed: {e}")
            import traceback
            traceback.print_exc()
            return self.create_placeholder_audio(text)
    
    def create_placeholder_audio(self, text):
        """Create placeholder audio"""
        import numpy as np
        
        print("Creating placeholder audio...")
        sample_rate = 22050
        duration = min(len(text) * 0.1, 10)  # 0.1 seconds per character, max 10 seconds
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        # Create a simple sine wave
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
        
        output_path = self.temp_dir / f"placeholder_{uuid.uuid4()}.wav"
        audio_tensor = torch.FloatTensor(audio).unsqueeze(0)
        torchaudio.save(str(output_path), audio_tensor, sample_rate)
        
        print(f"✅ Placeholder audio created: {output_path}")
        return str(output_path)
    
    def cleanup_file(self, filepath):
        """Clean up files"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"Cleaned up: {filepath}")
        except Exception as e:
            print(f"Cleanup failed for {filepath}: {e}")

# Global instance
print("Initializing VoiceCloner...")
voice_cloner = VoiceCloner()
