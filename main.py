#!/usr/bin/env python3.7
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv(".env.local")
    import txmaker
    txmaker.run_app()
