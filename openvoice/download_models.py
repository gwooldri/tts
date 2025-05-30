# download_models.py - Downloads OpenVoice model files
import os
import requests
from pathlib import Path
import zipfile

def download_file(url, local_path):
    """Download a file from URL"""
    print(f"Downloading {url}...")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Downloaded: {local_path}")

def download_openvoice_models():
    """Download OpenVoice model checkpoints"""
    
    # Create directories
    checkpoints_dir = Path("checkpoints")
    checkpoints_dir.mkdir(exist_ok=True)
    
    base_speakers_dir = checkpoints_dir / "base_speakers" / "EN"
    converter_dir = checkpoints_dir / "converter"
    
    base_speakers_dir.mkdir(parents=True, exist_ok=True)
    converter_dir.mkdir(parents=True, exist_ok=True)
    
    # Model download URLs (these are the actual OpenVoice model links)
    models_to_download = {
        # Base speaker model files
        "checkpoints/base_speakers/EN/config.json": "https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/basespeakers/EN/config.json",
        "checkpoints/base_speakers/EN/checkpoint.pth": "https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/basespeakers/EN/checkpoint.pth",
        
        # Converter model files  
        "checkpoints/converter/config.json": "https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/converter/config.json",
        "checkpoints/converter/checkpoint.pth": "https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/converter/checkpoint.pth",
    }
    
    print("Downloading OpenVoice model files...")
    
    for local_path, url in models_to_download.items():
        try:
            if not os.path.exists(local_path):
                download_file(url, local_path)
            else:
                print(f"File already exists: {local_path}")
        except Exception as e:
            print(f"Failed to download {local_path}: {e}")
    
    print("Model download completed!")

if __name__ == "__main__":
    download_openvoice_models()