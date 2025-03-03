import threading
import queue
import requests
import numpy as np
import io
import time
from datetime import datetime
import subprocess
import os
from vosk import Model, KaldiRecognizer
import zipfile
import wget

class CryptoDetector:
    def __init__(self, url, chunk_duration=2):
        self.url = url
        self.chunk_duration = chunk_duration
        self.audio_queue = queue.Queue()
        self.running = False
        
        # Initialize Vosk model
        print("Loading Vosk model...")
        model_name = "vosk-model-small-en-us-0.15"
        model_zip = f"{model_name}.zip"
        
        # Download and extract model if needed
        if not os.path.exists(model_name):
            print("Downloading model... This may take a few minutes...")
            if not os.path.exists(model_zip):
                wget.download("https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
            print("\nExtracting model...")
            with zipfile.ZipFile(model_zip, 'r') as zip_ref:
                zip_ref.extractall(".")
        
        self.model = Model(model_name)
        self.rec = KaldiRecognizer(self.model, 16000)
        
        # Words to detect
        self.keywords = {'crypto', 'bitcoin', 'cryptocurrency', 'btc', 'eth'}
        print(f"Monitoring for keywords: {self.keywords}")

    def start(self):
        self.running = True
        threading.Thread(target=self._stream_audio).start()
        threading.Thread(target=self._process_audio).start()

    def stop(self):
        self.running = False

    def _stream_audio(self):
        response = requests.get(self.url, stream=True)
        bytes_per_chunk = int(128 * 1024 / 8 * self.chunk_duration)
        
        chunk_buffer = io.BytesIO()
        bytes_collected = 0

        for chunk in response.iter_content(chunk_size=4096):
            if not self.running:
                break
            if chunk:
                chunk_buffer.write(chunk)
                bytes_collected += len(chunk)
                
                if bytes_collected >= bytes_per_chunk:
                    self.audio_queue.put(chunk_buffer.getvalue())
                    chunk_buffer = io.BytesIO()
                    bytes_collected = 0

    def _process_audio(self):
        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                if audio_data:
                    # Convert audio chunk to WAV format Vosk expects
                    temp_file = f"temp_{threading.get_ident()}.wav"
                    with open(temp_file, "wb") as f:
                        f.write(audio_data)
                    
                    # Convert to required format
                    subprocess.run([
                        'ffmpeg', '-i', temp_file,
                        '-acodec', 'pcm_s16le',
                        '-ar', '16000',
                        '-ac', '1',
                        '-y',
                        f"{temp_file}_converted.wav"
                    ], capture_output=True)
                    
                    # Read converted audio
                    with open(f"{temp_file}_converted.wav", "rb") as wf:
                        data = wf.read()
                        if self.rec.AcceptWaveform(data):
                            result = self.rec.Result()
                            import json
                            text = json.loads(result)['text'].lower()
                            
                            # Only process if we have text
                            if text:
                                # Check for keywords
                                found_keywords = [word for word in self.keywords if word in text]
                                
                                if found_keywords:
                                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    print(f"\n⚠️ DETECTED at {timestamp}:")
                                    print(f"Keywords found: {found_keywords}")
                                    print(f"Context: {text}")
                                    
                                    # Save the audio for verification
                                    detection_file = f"detections/detection_{timestamp}.wav"
                                    import shutil
                                    shutil.copy(f"{temp_file}_converted.wav", detection_file)

                    # Cleanup temporary files
                    try:
                        os.remove(temp_file)
                        os.remove(f"{temp_file}_converted.wav")
                    except:
                        pass

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing audio: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    url = "https://streams.kqed.org/kqedradio.mp3"
    
    # Create output directory
    os.makedirs('detections', exist_ok=True)
    
    # Start monitoring
    detector = CryptoDetector(url)
    
    try:
        detector.start()
        print("Monitoring stream... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        detector.stop()