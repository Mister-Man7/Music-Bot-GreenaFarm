import asyncio
import yt_dlp


async def search_youtube(query: str) -> dict | None:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extract_flat": False,
    }

    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if not info or "entries" not in info or not info["entries"]:
                return None
            entry = info["entries"][0]
            duration_sec = entry.get("duration", 0) or 0
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            return {
                "title": entry.get("title", "Unknown"),
                "url": entry.get("webpage_url") or entry.get("url", ""),
                "duration": f"{minutes}:{seconds:02d}",
            }

    return await asyncio.get_event_loop().run_in_executor(None, _search)


async def get_stream_url(youtube_url: str) -> str:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
    }

    def _get_url():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            formats = info.get("formats", [])
            # Cari format audio terbaik
            audio_formats = [
                f for f in formats
                if f.get("acodec") != "none" and f.get("vcodec") == "none"
            ]
            if audio_formats:
                # Sort by quality
                audio_formats.sort(key=lambda x: x.get("abr", 0) or 0, reverse=True)
                return audio_formats[0]["url"]
            # Fallback ke format terbaik
            if formats:
                return formats[-1]["url"]
            return info.get("url", "")

    return await asyncio.get_event_loop().run_in_executor(None, _get_url)
