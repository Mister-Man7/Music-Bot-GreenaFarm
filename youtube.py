import asyncio
import yt_dlp


async def search_youtube(query: str) -> dict | None:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "cookiefile": "/data/youtube_cookies.txt",
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
        # Format opus/webm paling compatible sama pytgcalls tanpa re-encode
        "format": "bestaudio[acodec=opus]/bestaudio[ext=webm]/bestaudio",
        "noplaylist": True,
        "cookiefile": "/data/youtube_cookies.txt",
    }

    def _get_url():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if "url" in info:
                return info["url"]
            formats = info.get("formats", [])
            # Prioritas: opus > webm audio > m4a > apapun
            for codec in ["opus", "webm", "m4a"]:
                for f in reversed(formats):
                    if (f.get("acodec", "") == codec or f.get("ext", "") == codec) and f.get("vcodec") == "none":
                        return f["url"]
            # Fallback audio only
            audio_only = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
            if audio_only:
                return audio_only[-1]["url"]
            return formats[-1]["url"]

    return await asyncio.get_event_loop().run_in_executor(None, _get_url)
