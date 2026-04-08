#!/usr/bin/env python3
"""
Helper script to set up Hugging Face authentication.
Run this to configure your HF_TOKEN for faster model downloads.
"""

import os
from pathlib import Path

def setup_hf_token():
    """Guide user through HF token setup."""
    
    print("=" * 60)
    print("Hugging Face Token Setup")
    print("=" * 60)
    print()
    print("Your model download is stuck because you're not authenticated.")
    print("Without authentication, Hugging Face severely rate-limits downloads.")
    print()
    print("To get your token:")
    print("1. Go to: https://huggingface.co/settings/tokens")
    print("2. Click 'New token'")
    print("3. Give it a name (e.g., 'ISE-AI')")
    print("4. Select 'Read' permission (default)")
    print("5. Click 'Generate token'")
    print("6. Copy the token (starts with 'hf_')")
    print()
    
    token = input("Paste your HF token here: ").strip()
    
    if not token.startswith("hf_"):
        print("⚠️  Warning: Token doesn't start with 'hf_'. Please check it.")
        return False
    
    # Save to .env file
    env_path = Path("backend/.env")
    
    # Read existing .env if it exists
    existing_content = ""
    if env_path.exists():
        existing_content = env_path.read_text()
        
        # Check if HF_TOKEN already exists
        if "HF_TOKEN=" in existing_content:
            print("✓ HF_TOKEN already exists in .env file")
            update = input("Do you want to update it? (y/n): ").strip().lower()
            if update != 'y':
                return False
    
    # Add or update HF_TOKEN
    lines = existing_content.strip().split("\n") if existing_content else []
    new_lines = []
    token_added = False
    
    for line in lines:
        if line.startswith("HF_TOKEN="):
            token_added = True
            new_lines.append(f"HF_TOKEN={token}")
        else:
            new_lines.append(line)
    
    if not token_added:
        new_lines.append(f"HF_TOKEN={token}")
    
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(new_lines) + "\n")
    
    print()
    print("✓ HF_TOKEN saved to backend/.env")
    print()
    print("Now you need to export it for the current session:")
    print()
    print(f"  export HF_TOKEN={token}")
    print()
    print("Or restart your application after adding it to .env")
    print()
    print("After setting the token, re-run your model download.")
    print("It should be much faster now!")
    print()
    
    return True


if __name__ == "__main__":
    setup_hf_token()
