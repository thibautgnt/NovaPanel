"""Musique ou video en cours (Spotify, navigateur...) via les controles media de Windows."""
import asyncio
import threading

try:
    from winrt.windows.media.control import \
        GlobalSystemMediaTransportControlsSessionManager as Manager
except ImportError:  # autre systeme que Windows
    Manager = None

PLAYING = 4  # GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING


class NowPlaying:
    available = Manager is not None

    def __init__(self, interval=1.0):
        self.current = None  # {"title", "artist", "playing", "app"} ou None
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="media")

    def start(self):
        if Manager:
            self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        asyncio.run(self._loop())

    async def _loop(self):
        mgr = None
        while not self._stop.is_set():
            try:
                if mgr is None:
                    mgr = await Manager.request_async()
                sess = mgr.get_current_session()
                if sess:
                    props = await sess.try_get_media_properties_async()
                    info = sess.get_playback_info()
                    self.current = {
                        "title": props.title or "",
                        "artist": props.artist or "",
                        "playing": info.playback_status == PLAYING,
                        "app": sess.source_app_user_model_id or "",
                    } if props and props.title else None
                else:
                    self.current = None
            except Exception:
                self.current = None
                mgr = None
            await asyncio.sleep(self.interval)
