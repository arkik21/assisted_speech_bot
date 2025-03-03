import subprocess
import time
from datetime import datetime
import json
import threading
import queue
import requests
import m3u8
import os
import traceback
import argparse
import sys
import logging
from logging.handlers import RotatingFileHandler
import backoff

from vosk import Model, KaldiRecognizer
from py_clob_client.clob_types import OrderArgs
from clob_client import create_clob_client

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import configuration loader
from utils.config_loader import get_config

# Get configuration
config = get_config()

# Create directory paths from configuration
for path_name, path in config.settings.get('paths', {}).items():
    os.makedirs(path, exist_ok=True)

# Configure logging
def setup_logger(name, log_file, level=logging.INFO):
    """Function to set up a logger with a specific name and file"""
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler with rotation (10MB max size, keep 5 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Get log paths from configuration
logs_dir = config.get_setting('paths', 'logs', 'logs')
main_logger = setup_logger('twitter_main', os.path.join(logs_dir, 'twitter_main.log'))
trade_logger = setup_logger('twitter_trade', os.path.join(logs_dir, 'twitter_trades.log'))
speech_logger = setup_logger('twitter_speech', os.path.join(logs_dir, 'twitter_speech.log'))

# Set debug mode from configuration
if config.get_setting('app', 'debug', False):
    main_logger.setLevel(logging.DEBUG)
    trade_logger.setLevel(logging.DEBUG)
    speech_logger.setLevel(logging.DEBUG)
    main_logger.debug("Debug mode enabled")

class TwitterStreamTrader:
    def __init__(self, twitter_url=None):
        """Initialize the Twitter Stream Trader with configuration"""
        self.trading_client = None
        self.initialize_trading_client()
        
        self.model = None
        self.rec = None
        self.initialize_speech_recognition()
        
        # Get Twitter URL from arguments or configuration
        twitter_config = config.get_source_config('twitter')
        self.twitter_url = twitter_url or twitter_config.get('default_url')
        if not self.twitter_url:
            raise ValueError("Twitter URL not provided and not found in configuration")
            
        main_logger.info(f"Using Twitter URL: {self.twitter_url}")
        
        # Initialize queue and tracking variables
        self.audio_queue = queue.Queue(maxsize=10)
        self.executed_markets = set()
        self.detection_history = []
        
        # Load markets from configuration
        self.markets = {}
        for market_id, market_data in config.get_enabled_markets().items():
            self.markets[market_id] = market_data
            main_logger.info(f"Loaded market: {market_id} - {market_data.get('name')}")

    def initialize_trading_client(self):
        """Initialize trading client with retries"""
        try:
            main_logger.info("Initializing trading client")
            self.trading_client = create_clob_client()
            main_logger.info("Trading client initialized successfully")
        except Exception as e:
            main_logger.error(f"Failed to initialize trading client: {str(e)}")
            main_logger.error(traceback.format_exc())
            raise

    def initialize_speech_recognition(self):
        """Initialize speech recognition with error handling"""
        try:
            main_logger.info("Loading Vosk model")
            model_name = config.get_setting('speech', 'model_name', "vosk-model-small-en-us-0.15")
            
            if not os.path.exists(model_name):
                main_logger.warning(f"Model directory {model_name} not found. Please ensure it's downloaded")
                main_logger.info(f"You can download it from: https://alphacephei.com/vosk/models/{model_name}.zip")
            
            self.model = Model(model_name)
            self.rec = KaldiRecognizer(self.model, config.get_setting('speech', 'sample_rate', 16000))
            main_logger.info("Speech recognition model loaded successfully")
        except Exception as e:
            main_logger.error(f"Failed to initialize speech recognition: {str(e)}")
            main_logger.error(traceback.format_exc())
            raise

    def get_stream_url(self):
        """Get the audio stream URL from a Twitter space or broadcast"""
        try:
            main_logger.info(f"Getting stream URL for Twitter URL: {self.twitter_url}")
            
            # Get yt-dlp options from configuration
            twitter_config = config.get_source_config('twitter')
            ytdlp_options = twitter_config.get('ytdlp_options', {'format': 'audio_only/audio/worst', 'quiet': True})
            
            ytdlp_cmd = ['yt-dlp', '--get-url']
            for key, value in ytdlp_options.items():
                if isinstance(value, bool):
                    if value:
                        ytdlp_cmd.append(f'--{key}')
                else:
                    ytdlp_cmd.append(f'--{key}')
                    ytdlp_cmd.append(str(value))
            
            ytdlp_cmd.append(self.twitter_url)
            
            main_logger.debug(f"Running yt-dlp command: {' '.join(ytdlp_cmd)}")
            
            # Execute yt-dlp command and get output
            stream_url = subprocess.check_output(ytdlp_cmd, stderr=subprocess.PIPE).decode().strip()
            
            if not stream_url:
                main_logger.error("No stream URL found")
                return None
                
            main_logger.info("Stream URL found successfully")
            
            # If the URL is an m3u8 playlist, parse it to get the audio stream
            if stream_url.endswith('.m3u8'):
                main_logger.info("Parsing m3u8 playlist...")
                playlist = m3u8.load(stream_url)
                
                # Try to get audio-only stream
                for stream in playlist.playlists:
                    if 'audio_only' in stream.uri.lower():
                        main_logger.info("Found audio-only stream")
                        return stream.uri
                
                # Fallback to first available stream
                if playlist.playlists:
                    main_logger.info("Using first available stream from playlist")
                    return playlist.playlists[0].uri
            
            return stream_url
                
        except subprocess.CalledProcessError as e:
            main_logger.error(f"Error running yt-dlp: {e.stderr.decode()}")
            return None
        except Exception as e:
            main_logger.error(f"Error getting stream URL: {e}")
            main_logger.error(traceback.format_exc())
            return None

    def get_audio_stream(self):
        """Set up audio processing pipeline from Twitter stream"""
        try:
            stream_url = self.get_stream_url()
            if not stream_url:
                raise Exception("Failed to get Twitter stream URL")

            main_logger.info(f"Starting FFmpeg with stream URL...")
            
            # Get audio processing options from configuration
            twitter_config = config.get_source_config('twitter')
            audio_config = twitter_config.get('audio', {})
            codec = audio_config.get('codec', 'pcm_s16le')
            sample_rate = audio_config.get('sample_rate', 16000)
            channels = audio_config.get('channels', 1)
            
            process = subprocess.Popen([
                'ffmpeg', 
                '-i', stream_url,
                '-acodec', codec, 
                '-ar', str(sample_rate), 
                '-ac', str(channels), 
                '-f', 'wav',
                '-'
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            main_logger.info("FFmpeg process started successfully")
            return process
        except Exception as e:
            main_logger.error(f"Failed to set up audio stream: {e}")
            main_logger.error(traceback.format_exc())
            raise

    @backoff.on_exception(backoff.expo, 
                         (Exception),
                         max_tries=5,
                         jitter=backoff.full_jitter)
    def create_and_submit_order(self, token_id, side, price, size):
        """Create and submit order with exponential backoff retry"""
        try:
            trade_logger.info(f"Creating order: token_id={token_id}, side={side}, price={price}, size={size}")
            
            order_args = OrderArgs(
                price=price,
                size=size,
                side=side,
                token_id=token_id,
            )
            
            signed_order = self.trading_client.create_order(order_args)
            trade_logger.info(f"Order created successfully")
            
            response = self.trading_client.post_order(signed_order)
            trade_logger.info(f"Order submitted successfully: {response}")
            
            return response
        except Exception as e:
            trade_logger.error(f"Order Error: {str(e)}")
            trade_logger.error(traceback.format_exc())
            raise

    def place_trade(self, market_id, market_config, detected_keyword, detection_time):
        """Place a trade with comprehensive logging"""
        try:
            trade_info = {
                "timestamp": datetime.now().isoformat(),
                "market_id": market_id,
                "market_name": market_config.get('name', market_id),
                "detected_keyword": detected_keyword,
                "detection_latency": time.time() - detection_time,
                "status": "pending"
            }
            
            trade_logger.info(f"Executing trade for {market_id} triggered by '{detected_keyword}'")
            
            # Check if we've already executed this market
            if config.get_setting('trading', 'prevent_duplicate_trades', True) and market_id in self.executed_markets:
                trade_logger.warning(f"Skipping trade for {market_id} - already executed")
                trade_info["status"] = "skipped"
                trade_info["reason"] = "already_executed"
                return
            
            resp = self.create_and_submit_order(
                token_id=market_config['token_id'],
                side=market_config['side'],
                price=market_config['price'],
                size=market_config['size']
            )
            
            if resp:
                self.executed_markets.add(market_id)
                latency = time.time() - detection_time
                
                trade_info["status"] = "success"
                trade_info["order_response"] = resp
                trade_info["execution_latency"] = latency
                
                trade_logger.info(f"Trade executed - {market_id} - Latency: {latency:.3f}s")
                trade_logger.info(f"Response: {resp}")
                
                # Save trade to file
                trades_dir = config.get_setting('paths', 'trades', 'trades')
                with open(f"{trades_dir}/{market_id}_{int(time.time())}.json", 'w') as f:
                    json.dump(trade_info, f, indent=2)
            else:
                trade_info["status"] = "failed"
                trade_logger.error(f"Trade failed - {market_id}: No response from server")
                
                # Save trade error to file
                trades_dir = config.get_setting('paths', 'trades', 'trades')
                with open(f"{trades_dir}/{market_id}_failed_{int(time.time())}.json", 'w') as f:
                    json.dump(trade_info, f, indent=2)
        except Exception as e:
            trade_info["status"] = "error"
            trade_info["error"] = str(e)
            trade_logger.error(f"Trade failed - {market_id}: {str(e)}")
            trade_logger.error(traceback.format_exc())
            
            # Save trade error to file
            trades_dir = config.get_setting('paths', 'trades', 'trades')
            with open(f"{trades_dir}/{market_id}_error_{int(time.time())}.json", 'w') as f:
                json.dump(trade_info, f, indent=2)

    def process_audio(self):
        """Process audio with better error handling and logging"""
        while True:
            try:
                audio_data = self.audio_queue.get(timeout=5)
                if not audio_data:
                    speech_logger.warning("Received empty audio data")
                    continue
                    
                if self.rec.AcceptWaveform(audio_data):
                    result = json.loads(self.rec.Result())
                    text = result.get('text', '').lower()
                    
                    if text:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        speech_logger.info(f"[{timestamp}] \"{text}\"")
                        
                        # Record all transcripts if configured
                        if config.get_setting('app', 'record_all_transcripts', False):
                            transcript_dir = os.path.join(config.get_setting('paths', 'logs', 'logs'), 'transcripts')
                            os.makedirs(transcript_dir, exist_ok=True)
                            with open(f"{transcript_dir}/transcript_{int(time.time())}.txt", 'w') as f:
                                f.write(f"{timestamp}: {text}")
                        
                        for market_id, market_config in self.markets.items():
                            if market_id in self.executed_markets and config.get_setting('trading', 'prevent_duplicate_trades', True):
                                continue
                                
                            detected = False
                            detected_keyword = None
                            
                            # Get keywords and trigger type from configuration
                            keywords = market_config.get('keywords', [])
                            trigger_type = market_config.get('trigger_type', 'any')
                            
                            # Override trigger type if configured globally
                            if config.get_setting('speech', 'exact_matching', False):
                                trigger_type = 'exact'
                            
                            if trigger_type == 'exact':
                                # Check if any keyword exactly matches the text
                                if text in keywords:
                                    detected = True
                                    detected_keyword = text
                            elif trigger_type == 'any':
                                # Check if any keyword is contained in the text
                                for kw in keywords:
                                    if kw in text:
                                        detected = True
                                        detected_keyword = kw
                                        break
                            
                            if detected:
                                detection_info = {
                                    "timestamp": datetime.now().isoformat(),
                                    "market_id": market_id,
                                    "market_name": market_config.get('name', market_id),
                                    "detected_keyword": detected_keyword,
                                    "full_text": text
                                }
                                
                                # Save detection to history and file
                                self.detection_history.append(detection_info)
                                
                                # Save detection to file if configured
                                if config.get_setting('speech', 'save_detections', True):
                                    detections_dir = config.get_setting('paths', 'detections', 'detections')
                                    with open(f"{detections_dir}/{market_id}_{int(time.time())}.json", 'w') as f:
                                        json.dump(detection_info, f, indent=2)
                                
                                speech_logger.info(f"Keyword detected for {market_id}: '{detected_keyword}'")
                                threading.Thread(
                                    target=self.place_trade,
                                    args=(market_id, market_config, detected_keyword, time.time())
                                ).start()
            except queue.Empty:
                speech_logger.debug("Audio queue timeout - continuing")
                continue
            except Exception as e:
                speech_logger.error(f"Error processing audio: {str(e)}")
                speech_logger.error(traceback.format_exc())
                time.sleep(1)  # Pause briefly before retrying

    def start(self):
        """Start the monitoring process with better error handling"""
        main_logger.info(f"Starting TwitterStreamTrader for URL: {self.twitter_url}")
        
        try:
            process = self.get_audio_stream()
            chunk_size = int(config.get_setting('speech', 'sample_rate', 16000) * 
                            config.get_setting('speech', 'chunk_size', 1))
            
            main_logger.info("Monitoring markets:")
            for market_id, market_config in self.markets.items():
                keywords = market_config.get('keywords', [])
                main_logger.info(f"- {market_id} ({market_config.get('name', '')}): {keywords}")
            
            # Start audio processing thread
            audio_thread = threading.Thread(target=self.process_audio, daemon=True)
            audio_thread.start()
            main_logger.info("Audio processing thread started")
            
            main_logger.info("Beginning audio stream reading")
            while True:
                audio_data = process.stdout.read(chunk_size)
                if not audio_data:
                    main_logger.warning("Audio stream ended or returned no data")
                    
                    # Auto restart if configured
                    if config.get_setting('app', 'auto_restart', True):
                        main_logger.info("Attempting to restart audio stream...")
                        process.terminate()
                        process.wait()
                        process = self.get_audio_stream()
                        continue
                    else:
                        break
                        
                self.audio_queue.put(audio_data)
                
        except KeyboardInterrupt:
            main_logger.info("Received keyboard interrupt, shutting down")
            if 'process' in locals():
                process.terminate()
                process.wait()
            main_logger.info("Shutdown complete")
        except Exception as e:
            main_logger.error(f"Error in main loop: {str(e)}")
            main_logger.error(traceback.format_exc())
            if 'process' in locals():
                process.terminate()
                process.wait()

def main():
    """Main entry point with command line argument handling"""
    parser = argparse.ArgumentParser(description='Polymarket trading based on Twitter speech recognition')
    parser.add_argument('--url', type=str, help='Twitter URL to monitor')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Override debug setting if provided
    if args.debug:
        main_logger.setLevel(logging.DEBUG)
        trade_logger.setLevel(logging.DEBUG)
        speech_logger.setLevel(logging.DEBUG)
        main_logger.debug("Debug mode enabled via command line")
    
    main_logger.info("Starting Twitter monitoring application")
    
    try:
        trader = TwitterStreamTrader(args.url)
        trader.start()
    except Exception as e:
        main_logger.critical(f"Fatal error: {str(e)}")
        main_logger.critical(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())