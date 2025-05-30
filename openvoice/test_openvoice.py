# test_openvoice.py - Test if everything is working
from voice_service import VoiceCloner
import tempfile

def test_voice_cloner():
    print("Testing Voice Cloner...")
    
    cloner = VoiceCloner()
    
    # Create a dummy audio file for testing
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
        import torch
        import torchaudio
        
        # Create simple test audio
        sample_rate = 22050
        duration = 2
        t = torch.linspace(0, duration, int(sample_rate * duration))
        audio = 0.3 * torch.sin(2 * 3.14159 * 440 * t).unsqueeze(0)
        torchaudio.save(temp_audio.name, audio, sample_rate)
        
        # Test voice cloning
        result = cloner.clone_voice("Hello, this is a test.", temp_audio.name)
        
        if result:
            print(f"✅ Voice cloning test successful! Output: {result}")
            print("✅ Your OpenVoice integration is working!")
        else:
            print("❌ Voice cloning test failed")
        
        # Cleanup
        cloner.cleanup_file(temp_audio.name)
        if result:
            cloner.cleanup_file(result)

if __name__ == "__main__":
    test_voice_cloner()