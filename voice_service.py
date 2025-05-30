# voice_service.py
import httpx
import base64
import tempfile
import os
from typing import Optional

class OpenVoiceService:
    def __init__(self):
        self.hf_token = os.getenv("HUGGING_FACE_TOKEN")  # Optional, for higher rate limits
        self.space_url = "https://myshell-ai-openvoice.hf.space"
    
    async def clone_voice(
        self, 
        text: str, 
        reference_audio_bytes: bytes,
        language: str = "EN"
    ) -> str:
        """
        Clone voice using OpenVoice on Hugging Face
        Returns: URL or base64 of generated audio
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Prepare files for upload
                files = {
                    "audio": ("reference.wav", reference_audio_bytes, "audio/wav")
                }
                
                data = {
                    "text": text,
                    "language": language,
                    "speed": 1.0
                }
                
                headers = {}
                if self.hf_token:
                    headers["Authorization"] = f"Bearer {self.hf_token}"
                
                # Call the Hugging Face Space API
                response = await client.post(
                    f"{self.space_url}/api/predict",
                    files=files,
                    data=data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Process the response based on HF Space output format
                    return result["data"][0]  # Adjust based on actual response structure
                else:
                    raise Exception(f"Voice cloning failed: {response.text}")
                    
        except Exception as e:
            raise Exception(f"OpenVoice API error: {str(e)}")

# FastAPI endpoint
from fastapi import FastAPI, UploadFile, HTTPException, Form

app = FastAPI()
voice_service = OpenVoiceService()

@app.post("/api/voice/clone")
async def clone_voice_endpoint(
    text: str = Form(...),
    reference_audio: UploadFile = Form(...),
    language: str = Form("EN")
):
    try:
        # Read audio file
        audio_bytes = await reference_audio.read()
        
        # Call OpenVoice service
        result_audio = await voice_service.clone_voice(
            text=text,
            reference_audio_bytes=audio_bytes,
            language=language
        )
        
        return {
            "success": True,
            "audio_url": result_audio,
            "message": "Voice cloned successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))