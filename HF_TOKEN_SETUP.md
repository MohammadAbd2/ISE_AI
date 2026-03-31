# Hugging Face Download Fix

## Problem
Your model download is stuck at 7% (257M/3.80G) because you're not authenticated with Hugging Face. Without authentication, downloads are severely rate-limited.

## Solution

### Option 1: Quick Setup (Recommended)

Run the setup script:
```bash
python setup_hf_token.py
```

This will guide you through getting and saving your token.

### Option 2: Manual Setup

1. **Get your HF token:**
   - Go to https://huggingface.co/settings/tokens
   - Click "New token"
   - Name it (e.g., "ISE-AI")
   - Keep "Read" permission
   - Click "Generate token"
   - Copy the token (starts with `hf_`)

2. **Set the token:**

   **For current session:**
   ```bash
   export HF_TOKEN=hf_your_token_here
   ```

   **Permanently (add to .env):**
   ```bash
   echo "HF_TOKEN=hf_your_token_here" >> backend/.env
   ```

3. **Restart your application**

## What Changed

The following files were updated to use HF authentication:
- `backend/app/services/image_generation.py`
- `backend/app/services/image_gen_capability.py`
- `backend/app/services/video_gen_capability.py`

All services now automatically authenticate when `HF_TOKEN` is set.

## Verify Authentication

After setting the token, you should see:
```
✓ Authenticated with Hugging Face
```

When the application starts.

## Download Speed Comparison

| Without Auth | With Auth |
|--------------|-----------|
| ~100 KB/s    | ~50 MB/s  |
| Heavy rate limiting | Higher rate limits |
| May get stuck | Reliable downloads |

## Still Stuck?

If the download is still slow after authentication:

1. **Check your internet connection**
2. **Try a different network** (some ISPs throttle HF)
3. **Use a mirror:**
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```
4. **Clear cache and retry:**
   ```bash
   rm -rf ~/.cache/huggingface/hub/models--stabilityai--sd-turbo/
   ```

## Monitor Download Progress

In another terminal:
```bash
watch -n 2 'du -sh ~/.cache/huggingface/hub/models--stabilityai--sd-turbo/'
```

This shows the download size increasing in real-time.
