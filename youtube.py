import subprocess
import time
from datetime import datetime
from vosk import Model, KaldiRecognizer
import yt_dlp
from py_clob_client.clob_types import OrderArgs
from clob_client import create_clob_client
import json
import threading
import queue

class MultiMarketTrader:
    def __init__(self, youtube_url):
        self.trading_client = create_clob_client()
        self.model = Model("vosk-model-small-en-us-0.15")
        self.rec = KaldiRecognizer(self.model, 16000)
        self.youtube_url = youtube_url
        self.audio_queue = queue.Queue(maxsize=10)
        self.executed_markets = set()
        
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

    def get_audio_stream(self):
        with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
            info = ydl.extract_info(self.youtube_url, download=False)
            audio_url = info['url']

        return subprocess.Popen([
            'ffmpeg', '-i', audio_url,
            '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-f', 'wav', '-'
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def process_audio(self):
        while True:
            audio_data = self.audio_queue.get()
            if self.rec.AcceptWaveform(audio_data):
                result = json.loads(self.rec.Result())
                text = result.get('text', '').lower()
                
                if text:
                    print(f"🎤 [{datetime.now().strftime('%H:%M:%S')}] \"{text}\"")
                    
                    for market_name, market_config in self.markets.items():
                        if market_name not in self.executed_markets and \
                           any(kw in text for kw in market_config['keywords']):
                            print(f"\n🚨 Trigger: {market_name}")
                            threading.Thread(
                                target=self.place_trade,
                                args=(market_name, market_config, 
                                      next(kw for kw in market_config['keywords'] if kw in text),
                                      time.time())
                            ).start()

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
    youtube_url = "https://www.youtube.com/watch?v=ZJR8YzV-Wgc"
    trader = MultiMarketTrader(youtube_url)
    trader.start()