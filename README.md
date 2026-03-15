# sora-automatic-video-generator

This project generates and uploads Shorts automatically using Sora (OpenAI) and the YouTube API. It builds video prompts, generates MP4s, and publishes them on a defined schedule, with a cache to avoid repetition.

## Features

- **End-to-end generation**: idea, prompt, MP4 video, and upload in one flow.
- **Sora API**: generates vertical 720x1280 videos at 4/8/12s.
- **Scheduled uploads**: UTC times for generation and uploads.
- **Smart cache**: avoids repeating recent styles or concepts.

## Project Structure

- `main.py`: orchestration for generation, cache, scheduling, and upload.
- `video_uploader.py`: YouTube auth, upload, and basic stats.
- `prompts/`: system and user prompts.
- `videos/`: generated MP4 output.
- `cache.json`: recent history with metadata and stats (auto-generated).

## Prerequisites

You need:
- Python
- uv
- Sora access and an OpenAI API key
- YouTube OAuth credentials (`client_secret.json`)

### Install uv

**Windows (PowerShell)**

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**macOS/Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version
```

## Installation and Setup

1. **Clone the Repository**

   ```bash
   git clone https://github.com/fverri/sora-automatic-video-generator.git
   ```

2. **Install Python Dependencies (uv)**

   ```bash
   cd sora-automatic-video-generator
   ```

   ```bash
   uv sync
   ```

3. **Configure Secrets**

   Place your YouTube OAuth file at `client_secret.json`.
   The first run will generate `token.pickle` after auth.

## Setup Guide (Step-by-Step)

1. **Install uv**

   Follow the instructions in the Prerequisites section to install uv.

2. **Create the .env File**

   Create `.env` with your OpenAI key:

   ```env
   OPENAI_API_KEY=your_key_here
   ```

3. **Add YouTube OAuth**

   Place `client_secret.json` at the repo root. Use this guide:
   https://www.youtube.com/watch?v=sp3qM2URcig

4. **First-time Auth**

   Run the script once to complete OAuth and generate `token.pickle`.

## Usage

From the repo root:

```bash
uv run python main.py
```

The script:
- Waits for the generation time (UTC)
- Generates videos with Sora
- Waits for each upload time (UTC)
- Uploads to YouTube Shorts and updates `cache.json`

## Configuration

Edit `main.py`:

- `GENERATE_AT`: UTC time for daily generation
- `UPLOAD_TIMES`: UTC times for each upload
- `CACHE_SIZE`: number of items in `cache.json`

You can tune creative style in `prompts/system_prompt.txt` and `prompts/user_prompt.txt`.

## Output

Videos are saved as:

```text
videos/output_video_<n>.mp4
```

If upload fails, the MP4 remains in `videos/`.

## Notes

- Sora access is required for `model="sora-2-pro"`.
- All times are handled in UTC.

## License

MIT. See `LICENSE`.
