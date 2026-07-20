"""Text-to-speech audio playback for Chinese words."""
import os
import platform
import subprocess
import tempfile
import threading
from typing import Dict

import pygame
from gtts import gTTS


class AudioService:
    def __init__(self):
        self.cache: Dict[str, str] = {}
        self.loading = False
        self.available = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.available = True
            print("Audio system initialized successfully")
        except (pygame.error, NotImplementedError) as e:
            print(f"Audio system not available: {e}")
            print("Audio playback will use system default player")

    def play(self, word: str) -> None:
        if self.loading:
            print("Audio already loading, please wait...")
            return
        if word in self.cache:
            self._play_cached(word)
            return
        self.loading = True
        print(f"Generating audio for: {word}")
        thread = threading.Thread(target=self._generate_and_play,
                                  args=(word,), daemon=True)
        thread.start()

    def _generate_and_play(self, word: str) -> None:
        try:
            tts = gTTS(text=word, lang='zh', slow=False)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                path = tmp.name
                tts.save(path)
            self.cache[word] = path
            self._play_cached(word)
        except Exception as e:
            print(f"Error generating audio: {e}")
        finally:
            self.loading = False

    def _play_cached(self, word: str) -> None:
        try:
            path = self.cache.get(word)
            if not path or not os.path.exists(path):
                self.cache.pop(word, None)
                return
            if self.available:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                print(f"Playing audio for: {word}")
                return
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["afplay", path], check=False)
            elif system == "Linux":
                subprocess.run(["aplay", path], check=False)
            elif system == "Windows":
                os.startfile(path)  # noqa: S606 — "start" via shell mangles paths with spaces
            print(f"Playing audio for: {word} (using system player)")
        except Exception as e:
            print(f"Error playing audio: {e}")
