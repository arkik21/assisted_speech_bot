import subprocess
import time
import os
from datetime import datetime
from vosk import Model, KaldiRecognizer
import yt_dlp
from py_clob_client.clob_types import OrderArgs
from clob_client import create_clob_client
import json
import threading
import queue
import logging
from logging.handlers import RotatingFileHandler
import traceback
import backoff

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('trades', exist_ok=True)
os.makedirs('detections', exist_ok=True)

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

# Set up loggers
main_logger = setup_logger('main', 'logs/main.log')
trade_logger = setup_logger('trade', 'logs/trades.log')
speech_logger = setup_logger('speech', 'logs/speech.log')

class MultiMarketTrader:
    def __init__(self, youtube_url):
        self.trading_client = None
        self.initialize_trading_client()
        
        self.model = None
        self.rec = None
        self.initialize_speech_recognition()
        
        self.youtube_url = youtube_url
        self.audio_queue = queue.Queue(maxsize=10)
        self.executed_markets = set()
        self.detection_history = []
        
        # Market configurations
        self.markets = {
           'crypto_market': {
               'token_id': '3660410095428561092102519777003195517288237825451410551527242610276838889743',
               'keywords': ['crypto', 'bitcoin', 'cryptocurrency'],
               'trigger_type': 'any',
               'side': 'BUY',
               'price': 0.9,
               'size': 432  # $388.80 total cost
           },
            'mcdonalds_market': {
                'token_id': '50356502236095665350267124222963007489686801360851223017206557156317194382898',
                'keywords': ['mcdonalds'],
                'trigger_type': 'exact',
                'side': 'BUY',
                'price': 0.5,
                'size': 775  # $387.50 total cost at $0.50 per share
            },
           'sleepy_joe_market': {
               'token_id': '4653101539264023968524739404348782737292724275999790265379600839231750780090',
               'keywords': ['sleepy joe'],
               'trigger_type': 'exact',
               'side': 'BUY',
               'price': 0.3,
               'size': 1300  # $390 total cost
           },         
           'crooked_joe_market': {
               'token_id': '81099742287114274271431275759337167201136362024111061408972055849730762251498',
               'keywords': ['crooked joe'],
               'trigger_type': 'exact',
               'side': 'BUY',
               'price': 0.3,
               'size': 1300  # $390 total cost
           },
           'doge_market': {
               'token_id': '99924137919019374354779168014821345320750518782626001937091372900606097051185',
               'keywords': ['dogecoin', 'doge', 'doge coin'],
               'trigger_type': 'any',
               'side': 'BUY',
               'price': 0.5,
               'size': 780  # $390 total cost
           },
           'greenland_market': {
               'token_id': '34510344541365974726107691584398341159796505768592867142296638107609795066241',
               'keywords': ['greenland'],
               'trigger_type': 'exact',
               'side': 'BUY',
               'price': 0.8,
               'size': 487  # $389.60 total cost
           },
       }

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
            model_name = "vosk-model-small-en-us-0.15"
            
            if not os.path.exists(model_name):
                main_logger.warning(f"Model directory {model_name} not found. Please ensure it's downloaded")
                main_logger.info("You can download it from: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
            
            self.model = Model(model_name)
            self.rec = KaldiRecognizer(self.model, 16000)
            main_logger.info("Speech recognition model loaded successfully")
        except Exception as e:
            main_logger.error(f"Failed to initialize speech recognition: {str(e)}")
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

    def place_trade(self, market_name, market_config, detected_keyword, detection_time):
        """Place a trade with comprehensive logging"""
        try:
            trade_info = {
                "timestamp": datetime.now().isoformat(),
                "market_name": market_name,
                "detected_keyword": detected_keyword,
                "detection_latency": time.time() - detection_time,
                "status": "pending"
            }
            
            trade_logger.info(f"Executing trade for {market_name} triggered by '{detected_keyword}'")
            
            resp = self.create_and_submit_order(
                token_id=market_config['token_id'],
                side=market_config['side'],
                price=market_config['price'],
                size=market_config['size']
            )
            
            if resp:
                self.executed_markets.add(market_name)
                latency = time.time() - detection_time
                
                trade_info["status"] = "success"
                trade_info["order_response"] = resp
                trade_info["execution_latency"] = latency
                
                trade_logger.info(f"Trade executed - {market_name} - Latency: {latency:.3f}s")
                trade_logger.info(f"Response: {resp}")
                
                # Save trade to file
                with open(f"trades/{market_name}_{int(time.time())}.json", 'w') as f:
                    json.dump(trade_info, f, indent=2)
            else:
                trade_info["status"] = "failed"
                trade_logger.error(f"Trade failed - {market_name}: No response from server")
        except Exception as e:
            trade_info["status"] = "error"
            trade_info["error"] = str(e)
            trade_logger.error(f"Trade failed - {market_name}: {str(e)}")
            trade_logger.error(traceback.format_exc())
            
            # Save trade error to file
            with open(f"trades/{market_name}_error_{int(time.time())}.json", 'w') as f:
                json.dump(trade_info, f, indent=2)

    def get_audio_stream(self):
        """Get audio stream with better error handling"""
        try:
            main_logger.info(f"Getting audio stream for YouTube URL: {self.youtube_url}")
            
            with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True}) as ydl:
                main_logger.info("Extracting info with yt-dlp")
                info = ydl.extract_info(self.youtube_url, download=False)
                audio_url = info['url']
                main_logger.info("Successfully extracted audio URL")
            
            main_logger.info("Starting FFmpeg process")
            process = subprocess.Popen([
                'ffmpeg', '-i', audio_url,
                '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-f', 'wav', '-'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            main_logger.info("FFmpeg process started successfully")
            return process
        except Exception as e:
            main_logger.error(f"Failed to get audio stream: {str(e)}")
            main_logger.error(traceback.format_exc())
            raise

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
                        
                        for market_name, market_config in self.markets.items():
                            if market_name in self.executed_markets:
                                continue
                                
                            detected = False
                            detected_keyword = None
                            
                            if market_config['trigger_type'] == 'exact':
                                # Check if any keyword exactly matches the text
                                if text in market_config['keywords']:
                                    detected = True
                                    detected_keyword = text
                            elif market_config['trigger_type'] == 'any':
                                # Check if any keyword is contained in the text
                                for kw in market_config['keywords']:
                                    if kw in text:
                                        detected = True
                                        detected_keyword = kw
                                        break
                            
                            if detected:
                                detection_info = {
                                    "timestamp": datetime.now().isoformat(),
                                    "market_name": market_name,
                                    "detected_keyword": detected_keyword,
                                    "full_text": text
                                }
                                
                                # Save detection to history and file
                                self.detection_history.append(detection_info)
                                with open(f"detections/{market_name}_{int(time.time())}.json", 'w') as f:
                                    json.dump(detection_info, f, indent=2)
                                
                                speech_logger.info(f"Keyword detected for {market_name}: '{detected_keyword}'")
                                threading.Thread(
                                    target=self.place_trade,
                                    args=(market_name, market_config, detected_keyword, time.time())
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
        main_logger.info(f"Starting MultiMarketTrader for URL: {self.youtube_url}")
        
        try:
            process = self.get_audio_stream()
            chunk_size = int(16000 * 1)  # 1 second chunks
            
            main_logger.info("Monitoring markets:")
            for market_name, config in self.markets.items():
                main_logger.info(f"- {market_name}: {config['keywords']}")
            
            # Start audio processing thread
            audio_thread = threading.Thread(target=self.process_audio, daemon=True)
            audio_thread.start()
            main_logger.info("Audio processing thread started")
            
            main_logger.info("Beginning audio stream reading")
            while True:
                audio_data = process.stdout.read(chunk_size)
                if not audio_data:
                    main_logger.warning("Audio stream ended or returned no data")
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

if __name__ == "__main__":
    main_logger.info("Starting application")
    
    youtube_url = "https://www.youtube.com/watch?v=ZJR8YzV-Wgc"
    main_logger.info(f"Using YouTube URL: {youtube_url}")
    
    try:
        trader = MultiMarketTrader(youtube_url)
        trader.start()
    except Exception as e:
        main_logger.critical(f"Fatal error: {str(e)}")
        main_logger.critical(traceback.format_exc())