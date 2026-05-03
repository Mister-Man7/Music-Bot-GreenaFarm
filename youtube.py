import asyncio
import yt_dlp


async def search_youtube(query: str) -> dict | None:
    """Cari lagu di YouTube, return info pertama."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
        "noplaylist": True,
    }

    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if not info or "entries" not in info or not info["entries"]:
                return None
            entry = info["entries"][0]
            duration_sec = entry.get("duration", 0)
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            return {
                "title": entry.get("title", "Unknown"),
                "url": entry.get("webpage_url", ""),
                "duration": f"{minutes}:{seconds:02d}",
                "thumbnail": entry.get("thumbnail", "")
            }

    return await asyncio.get_event_loop().run_in_executor(None, _search)


async def get_stream_url(youtube_url: str) -> str:
    """Ambil URL stream audio langsung dari YouTube."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }

    def _get_url():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            # Ambil URL audio terbaik
            if "url" in info:
                return info["url"]
            # Kalau ada formats, ambil yang terbaik
            formats = info.get("formats", [])
            audio_formats = [f for f in formats if f.get("acodec") != "none"]
            if audio_formats:
                return audio_formats[-1]["url"]
            return info["url"]

    return await asyncio.get_event_loop().run_in_executor(None, _get_url)
