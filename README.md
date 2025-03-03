# Polymarket Speech Bot

This project demonstrates how to interact programmatically with Polymarket CLOB API and set up automated trading based on speech detection. It includes step-by-step examples for wallet management, market interaction, and real-time speech-triggered trading.

## Overview

This system enables automated trading on Polymarket prediction markets by monitoring audio streams (YouTube, Twitter, radio) for specific keywords and phrases. When target words are detected, the system automatically executes pre-configured trades.

The project includes several components:
1. Wallet generation and management
2. API authentication with Polymarket
3. Market data retrieval
4. Speech recognition using Vosk
5. Automated trade execution

## Key Features

- **Speech Recognition**: Uses the `vosk-model-small-en-us-0.15` model to detect keywords in audio streams
- **Multi-Platform Support**: Can monitor YouTube videos, Twitter spaces, and radio streams
- **Configurable Trading**: Define markets, trigger words, and trade parameters via YAML configuration
- **Real-Time Processing**: Low-latency detection and trade execution
- **Wallet Management**: Utilities for wallet generation and blockchain interactions
- **Comprehensive Logging**: Structured logging with rotating log files
- **Error Handling**: Robust error handling with automatic retries

## Quick Start

1. Install requirements and dependencies
```
pip install -r requirements.txt
```

2. Set up the configuration directories:
```
mkdir -p config/sources
```

3. Copy the YAML configuration files to their appropriate locations:
   - `config/markets.yaml` - Market definitions
   - `config/settings.yaml` - Global settings
   - `config/sources/youtube.yaml` - YouTube-specific settings
   - `config/sources/twitter.yaml` - Twitter-specific settings
   - `config/sources/radio.yaml` - Radio-specific settings

4. Set up your wallet:
   - Run `src/helpers/generate_wallet.py` to create a new wallet
   - Fund wallet with Matic and USDC.e on Polygon network

5. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Set required values (HOST, PK, etc.)

6. Run one of the monitoring scripts:
   - `python youtube.py` for YouTube streams
   - `python twitter.py` for Twitter broadcasts
   - `python radio_transcript.py` for radio streams

7. (Optional) Override default URL via command line:
   - `python youtube.py --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" --debug`

## Configuration System

The project uses a YAML-based configuration system that separates code from configuration:

### Market Definitions (`config/markets.yaml`)

Define markets to monitor and their associated parameters:

```yaml
crypto_market:
  name: "Crypto/Bitcoin Mention"
  token_id: "36604100954285610921025197770031955172882378..."
  keywords:
    - "crypto"
    - "bitcoin"
    - "cryptocurrency"
  trigger_type: "any"
  side: "BUY"
  price: 0.9
  size: 432
  max_position: 1000
  description: "Will Trump say crypto or Bitcoin during inauguration speech?"
```

### Global Settings (`config/settings.yaml`)

Define global application behavior:

```yaml
trading:
  prevent_duplicate_trades: true
  max_daily_volume: 5000
  
speech:
  chunk_size: 1
  sample_rate: 16000
  model_name: "vosk-model-small-en-us-0.15"
  
paths:
  logs: "logs"
  trades: "trades"
  detections: "detections"
```

### Source-Specific Settings (`config/sources/youtube.yaml`)

Configure settings specific to each audio source:

```yaml
default_url: "https://www.youtube.com/watch?v=ZJR8YzV-Wgc"
ytdlp_options:
  format: "bestaudio"
  quiet: true
audio:
  codec: "pcm_s16le"
  sample_rate: 16000
  channels: 1
```

## Speech Recognition System

The project uses Vosk for speech recognition with the `vosk-model-small-en-us-0.15` model, which will be automatically downloaded on first run. The speech system:

1. Captures audio from the specified source (YouTube, Twitter, radio)
2. Processes audio in small chunks to minimize latency
3. Converts speech to text using Vosk recognition
4. Compares detected text against configured keyword lists
5. Triggers trades when matches are found

## Architecture

```
├── config/                 # Configuration files
│   ├── markets.yaml        # Market definitions
│   ├── settings.yaml       # Global application settings
│   └── sources/            # Audio source configurations
│       ├── youtube.yaml    # YouTube source settings
│       ├── twitter.yaml    # Twitter source settings
│       └── radio.yaml      # Radio source settings
├── logs/                   # Logging directory
│   ├── main.log            # Application logs
│   ├── trades.log          # Trade execution logs
│   └── speech.log          # Speech recognition logs
├── trades/                 # Trade records (JSON)
├── detections/             # Keyword detection records (JSON)
├── src/                    # Source code
│   ├── api_keys/           # API key management
│   ├── helpers/            # Helper utilities
│   ├── markets/            # Market interaction
│   ├── trades/             # Trade execution
│   └── utils/              # Utility functions
│       └── config_loader.py # Configuration loading utility
├── clob_client.py          # CLOB client implementation
├── radio_transcript.py     # Radio stream monitoring
├── trade_market.py         # Market trading example
├── twitter.py              # Twitter stream monitoring
└── youtube.py              # YouTube stream monitoring
```

## Logging System

The application includes a comprehensive logging system:

- **Main Logs**: General application events and startup/shutdown information
- **Trade Logs**: Detailed records of trade executions and failures
- **Speech Logs**: Transcripts of detected speech and keyword matches

Log files are automatically rotated to avoid filling up disk space, and logs include detailed information for troubleshooting.

## Requirements
- Python 3.9+
- FFmpeg (for audio processing)
- Dependencies listed in requirements.txt
- Vosk speech recognition model (downloaded automatically)

## Sidenotes

- YouTube video with more explanation - https://www.youtube.com/watch?v=ZbFTmDgSe_4
- Polymarket CLOB API - https://docs.polymarket.com/
- Polymarket CLOB Python client - https://github.com/Polymarket/py-clob-client

## Disclaimer

This is an experimental tool provided for educational purposes. Use this code at your own risk. This is just a showcase of possible functionality of said libraries and APIs.
