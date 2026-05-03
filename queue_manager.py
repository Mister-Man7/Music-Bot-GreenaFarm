class MusicQueue:
    def __init__(self):
        self._queues: dict[int, list] = {}
        self._playing: dict[int, bool] = {}

    def add(self, chat_id: int, track: dict):
        if chat_id not in self._queues:
            self._queues[chat_id] = []
        self._queues[chat_id].append(track)

    def next(self, chat_id: int) -> dict | None:
        if chat_id not in self._queues or not self._queues[chat_id]:
            self._playing[chat_id] = False
            return None
        # Hapus lagu pertama (yang baru selesai)
        self._queues[chat_id].pop(0)
        if not self._queues[chat_id]:
            self._playing[chat_id] = False
            return None
        return self._queues[chat_id][0]

    def get_all(self, chat_id: int) -> list:
        return self._queues.get(chat_id, [])

    def is_playing(self, chat_id: int) -> bool:
        return self._playing.get(chat_id, False)

    def set_playing(self, chat_id: int, status: bool):
        self._playing[chat_id] = status

    def position(self, chat_id: int) -> int:
        return len(self._queues.get(chat_id, []))

    def clear(self, chat_id: int):
        self._queues[chat_id] = []
        self._playing[chat_id] = False
