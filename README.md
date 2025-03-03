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
- **Configurable Trading**: Define markets, trigger words, and trade parameters
- **Real-Time Processing**: Low-latency detection and trade execution
- **Wallet Management**: Utilities for wallet generation and blockchain interactions

## Quick Start

1. Install requirements and dependencies
```
pip install -r requirements.txt
```

2. Set up your wallet:
   - Run `src/helpers/generate_wallet.py` to create a new wallet
   - Fund wallet with Matic and USDC.e on Polygon network

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Set required values (HOST, PK, etc.)

4. Set trading parameters:
   - Update market IDs and token IDs for the markets you want to trade
   - Configure keywords, prices, and sizes in the relevant script

5. Run one of the monitoring scripts:
   - `youtube.py` for YouTube streams
   - `twitter.py` for Twitter broadcasts
   - `radio_transcript.py` for radio streams

## Speech Recognition System

The project uses Vosk for speech recognition with the `vosk-model-small-en-us-0.15` model, which will be automatically downloaded on first run. The speech system:

1. Captures audio from the specified source (YouTube, Twitter, radio)
2. Processes audio in small chunks to minimize latency
3. Converts speech to text using Vosk recognition
4. Compares detected text against configured keyword lists
5. Triggers trades when matches are found

## Architecture

```
├── Poly_configuration/       # Core configuration and utilities
│   ├── .env.example          # Template for environment variables
│   ├── requirements.txt      # Project dependencies
│   └── src/                  # Source code
│       ├── api_keys/         # API key management
│       ├── helpers/          # Helper utilities
│       ├── markets/          # Market interaction
│       └── trades/           # Trade execution
├── clob_client.py            # CLOB client implementation
├── market_data.ipynb         # Jupyter notebook for market analysis
├── radio_transcript.py       # Radio stream monitoring
├── trade_market.py           # Market trading example
├── twitter.py                # Twitter stream monitoring
└── youtube.py                # YouTube stream monitoring
```

## Market Configuration

The system can be configured to monitor for specific keywords and execute trades on corresponding markets. Example configuration:

```python
'crypto_market': {
    'token_id': '12345...',
    'keywords': ['crypto', 'bitcoin', 'cryptocurrency'],
    'trigger_type': 'any',
    'side': 'BUY',
    'price': 0.9,
    'size': 432
}
```

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