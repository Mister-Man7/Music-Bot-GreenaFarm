FROM python:3.11-slim

# Install ffmpeg and git (git is needed for pip to install yt-dlp from GitHub)
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

# Install the Deno binary, the JavaScript runtime yt-dlp uses (from PATH) to solve
# YouTube's n/signature challenges together with the yt-dlp-ejs solver scripts
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno
RUN deno --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
