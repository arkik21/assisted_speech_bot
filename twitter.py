import subprocess
import time
from datetime import datetime
from vosk import Model, KaldiRecognizer
import json
import threading
import queue
import requests
import m3u8
import os
import base64
from dotenv import load_dotenv
from py_clob_client.clob_types import OrderArgs
from py_clob_client.client import ClobClient
from py_clob_client.order_builder.constants import BUY
from clob_client import create_clob_client

class TwitterStreamTrader:
    def __init__(self, twitter_url):
        # Load environment variables
        load_dotenv()
        
        # Initialize Polymarket client
        self.trading_client = create_clob_client()
            
        # Rest of the initialization that was working before
        self.model = Model("vosk-model-small-en-us-0.15")
        self.rec = KaldiRecognizer(self.model, 16000)
        self.twitter_url = twitter_url
        self.audio_queue = queue.Queue(maxsize=10)
        self.executed_markets = set()
        
        # Market configurations
        self.markets = {
            'mcdonalds_market': {
                'token_id': '50356502236095665350267124222963007489686801360851223017206557156317194382898',
                'keywords': ['mcdonalds'],
                'trigger_type': 'exact',
                'side': BUY,
                'price': 0.5,
                'size': 775
            },
            'sleepy_joe_market': {
                'token_id': '4653101539264023968524739404348782737292724275999790265379600839231750780090',
                'keywords': ['sleepy joe'],
                'trigger_type': 'exact',
                'side': BUY,
                'price': 0.3,
                'size': 1300
            },
            'crooked_joe_market': {
                'token_id': '81099742287114274271431275759337167201136362024111061408972055849730762251498',
                'keywords': ['crooked joe'],
                'trigger_type': 'exact',
                'side': BUY,
                'price': 0.3,
                'size': 1300
            },
            'doge_market': {
                'token_id': '99924137919019374354779168014821345320750518782626001937091372900606097051185',
                'keywords': ['dogecoin', 'doge', 'doge coin'],
                'trigger_type': 'any',
                'side': BUY,
                'price': 0.5,
                'size': 780
            },
            'greenland_market': {
                'token_id': '34510344541365974726107691584398341159796505768592867142296638107609795066241',
                'keywords': ['greenland'],
                'trigger_type': 'exact',
                'side': BUY,
                'price': 0.8,
                'size': 487
            },
            'drill_baby_drill_market': {
                'token_id': '114025614801185921971405922012344009013796396174688027492878973701931375633661',
                'keywords': ['drill baby drill'],
                'trigger_type': 'exact',
                'side': BUY,
                'price': 0.9,
                'size': 420
            },
        }

    def get_stream_url(self):
        try:
            print("Getting stream URL using yt-dlp...")
            command = [
                'yt-dlp',
                '--format', 'audio_only/audio/worst',  # Prefer audio-only stream
                '--get-url',
                self.twitter_url
            ]
            
            # Execute yt-dlp command and get output
            stream_url = subprocess.check_output(command, stderr=subprocess.PIPE).decode().strip()
            
            if not stream_url:
                print("No stream URL found")
                return None
                
            print("Stream URL found successfully")
            
            # If the URL is an m3u8 playlist, parse it to get the audio stream
            if stream_url.endswith('.m3u8'):
                print("Parsing m3u8 playlist...")
                playlist = m3u8.load(stream_url)
                
                # Try to get audio-only stream
                for stream in playlist.playlists:
                    if 'audio_only' in stream.uri.lower():
                        return stream.uri
                
                # Fallback to first available stream
                return playlist.playlists[0].uri
            
            return stream_url
                
        except subprocess.CalledProcessError as e:
            print(f"Error running yt-dlp: {e.stderr.decode()}")
            return None
        except Exception as e:
            print(f"Error getting stream URL: {e}")
            return None

    def get_audio_stream(self):
        stream_url = self.get_stream_url()
        if not stream_url:
            raise Exception("Failed to get Twitter stream URL")

        print(f"Starting FFmpeg with stream URL...")
        return subprocess.Popen([
            'ffmpeg', 
            '-i', stream_url,
            '-acodec', 'pcm_s16le', 
            '-ar', '16000', 
            '-ac', '1', 
            '-f', 'wav',
            '-'
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def create_and_submit_order(self, token_id, side, price, size):
        try:
            order_args = OrderArgs(
                price=price,
                size=size,
                side=side,
                token_id=token_id,
            )
            signed_order = self.trading_client.create_order(order_args)
            return self.trading_client.post_order(signed_order)
        except Exception as e:
            print(f"🚫 Order Error: {str(e)}")
            return None

    def place_trade(self, market_name, market_config, detected_keyword, detection_time):
        try:
            resp = self.create_and_submit_order(
                token_id=market_config['token_id'],
                side=market_config['side'],
                price=market_config['price'],
                size=market_config['size']
            )
            
            if resp:
                self.executed_markets.add(market_name)
                latency = time.time() - detection_time
                print(f"✅ Trade executed - {market_name} - Latency: {latency:.3f}s")
                print(f"Response: {resp}\n")
        except Exception as e:
            print(f"🚫 Trade failed - {market_name}: {str(e)}\n")

    def process_audio(self):
        while True:
            try:
                audio_data = self.audio_queue.get(timeout=5)
                if self.rec.AcceptWaveform(audio_data):
                    result = json.loads(self.rec.Result())
                    text = result.get('text', '').lower()
                    
                    if text:
                        print(f"🎤 [{datetime.now().strftime('%H:%M:%S')}] \"{text}\"")
                        
                        for market_name, market_config in self.markets.items():
                            if market_name not in self.executed_markets:
                                if market_config['trigger_type'] == 'exact':
                                    if any(kw == text for kw in market_config['keywords']):
                                        print(f"\n🚨 Trigger: {market_name}")
                                        threading.Thread(
                                            target=self.place_trade,
                                            args=(market_name, market_config, 
                                                  next(kw for kw in market_config['keywords'] if kw in text),
                                                  time.time())
                                        ).start()
                                elif market_config['trigger_type'] == 'any':
                                    if any(kw in text for kw in market_config['keywords']):
                                        print(f"\n🚨 Trigger: {market_name}")
                                        threading.Thread(
                                            target=self.place_trade,
                                            args=(market_name, market_config, 
                                                  next(kw for kw in market_config['keywords'] if kw in text),
                                                  time.time())
                                        ).start()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing audio: {e}")
                time.sleep(1)

    def start(self):
        process = self.get_audio_stream()
        chunk_size = int(16000 * 1)  # 1 second chunks

        print("\n📊 Monitoring markets:")
        for market_name, config in self.markets.items():
            print(f"- {market_name}: {config['keywords']}")
        print("=" * 50 + "\n")
        
        threading.Thread(target=self.process_audio, daemon=True).start()
    
        try:
            while True:
                audio_data = process.stdout.read(chunk_size)
                if not audio_data:
                    break
                self.audio_queue.put(audio_data)

        except KeyboardInterrupt:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    # Twitter space or broadcast URL
    twitter_url = "https://x.com/i/broadcasts/1dRKZddyzbbJB"
    
    # Create and start the trader
    trader = TwitterStreamTrader(twitter_url)
    trader.start()