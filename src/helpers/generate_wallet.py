from dotenv import set_key, load_dotenv

from bip_utils import (
    Bip39MnemonicGenerator,
    Bip39SeedGenerator,
    Bip44,
    Bip44Coins,
    Bip44Changes,
)


def generate_new_wallet():
    # Step 1: Generate a 12-word mnemonic
    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12)
    print('Generated Mnemonic:', mnemonic)

    # Step 2: Create a seed from the mnemonic
    seed_generator = Bip39SeedGenerator(mnemonic)
    seed = seed_generator.Generate()

    # Step 3: Derive the Ethereum wallet using BIP44 standard
    bip44_mst = Bip44.FromSeed(seed, Bip44Coins.ETHEREUM)
    eth_account = bip44_mst.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)

    # Step 4: Retrieve wallet information
    private_key = eth_account.PrivateKey().Raw().ToHex()
    address = eth_account.PublicKey().ToAddress()

    print('ETH Wallet Address:', address)
    print('Private Key:', private_key)

    env_path = '.env'  # Path to your .env file
    load_dotenv(env_path)  # Load existing .env file if present

    set_key(env_path, 'PK', private_key)
    set_key(env_path, 'PBK', address)
