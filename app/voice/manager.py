# -*- coding: utf-8 -*-
"""Female voice reminders: Piper (huayan / Alba) with SAPI fallback."""

import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import wave

from app.core.config import APP_DATA, PROJECT_DIR

VOICE_DIR = os.path.join(PROJECT_DIR, "voices")
if not os.path.isdir(VOICE_DIR):
    VOICE_DIR = os.path.dirname(os.path.abspath(__file__))
ZH_MODEL = os.path.join(VOICE_DIR, "voice_zh_huayan.onnx")
ZH_CONFIG = os.path.join(VOICE_DIR, "voice_zh_huayan.json")
EN_MODEL = os.path.join(VOICE_DIR, "voice_en_alba.onnx")
EN_CONFIG = os.path.join(VOICE_DIR, "voice_en_alba.json")

# Chinese is 10% slower; English stays at normal speed.
ZH_LENGTH_SCALE = 1.10
EN_LENGTH_SCALE = 1.00


def has_chinese(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def voice_lang(text):
    return "zh" if has_chinese(text) else "en"


class PiperBackend:
    name = "piper"

    def __init__(self, settings=None):
        self.settings = settings
        self._voices = {}
        self.zh_model = self._path("voice_zh_model", "voice_zh_huayan.onnx")
        self.zh_config = self._path("voice_zh_config", "voice_zh_huayan.json")
        self.en_model = self._path("voice_en_model", "voice_en_alba.onnx")
        self.en_config = self._path("voice_en_config", "voice_en_alba.json")
        self.zh_scale = float(settings.get("voice_zh_length_scale", 1.10)) if settings else 1.10
        self.en_scale = float(settings.get("voice_en_length_scale", 1.00)) if settings else 1.00

    def _path(self, key, default):
        value = self.settings.get(key, default) if self.settings else default
        return value if os.path.isabs(value) else os.path.join(VOICE_DIR, value)

    def available(self):
        return os.path.exists(self.zh_model) and os.path.exists(self.en_model)

    def _voice(self, lang):
        if lang in self._voices:
            return self._voices[lang]
        from piper import PiperVoice  # type: ignore

        model = self.zh_model if lang == "zh" else self.en_model
        config = self.zh_config if lang == "zh" else self.en_config
        voice = PiperVoice.load(model, config_path=config)
        self._voices[lang] = voice
        return voice

    def synth(self, text, lang, out_wav):
        length_scale = self.zh_scale if lang == "zh" else self.en_scale
        try:
            from piper import SynthesisConfig  # type: ignore
            voice = self._voice(lang)
            chunks = list(voice.synthesize(
                text, syn_config=SynthesisConfig(length_scale=length_scale)))
            if not chunks:
                return False
            first = chunks[0]
            with wave.open(out_wav, "wb") as wf:
                wf.setnchannels(first.sample_channels)
                wf.setsampwidth(first.sample_width)
                wf.setframerate(first.sample_rate)
                for c in chunks:
                    wf.writeframes(c.audio_int16_bytes)
            return True
        except Exception:
            pass

        # Fallback to the piper CLI if the Python API differs by version.
        model = self.zh_model if lang == "zh" else self.en_model
        config = self.zh_config if lang == "zh" else self.en_config
        try:
            cmd = ["piper", "--model", model, "--config", config,
                   "--output_file", out_wav, "--length_scale", str(length_scale)]
            subprocess.run(cmd, input=text, text=True, capture_output=True,
                           timeout=30, check=False)
            return os.path.exists(out_wav) and os.path.getsize(out_wav) > 44
        except Exception:
            return False


class SapiBackend:
    name = "sapi"

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()

    def available(self):
        try:
            import pyttsx3  # noqa: F401
            return True
        except Exception:
            return False

    def _get_engine(self):
        if self._engine is None:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._pick_female()
        return self._engine

    def _pick_female(self):
        try:
            voices = self._engine.getProperty("voices")
            for v in voices:
                blob = f"{v.name} {v.id}".lower()
                if any(x in blob for x in ("huihui", "zira", "female", "女")):
                    self._engine.setProperty("voice", v.id)
                    return
        except Exception:
            pass

    def speak(self, text, lang, volume=1.0):
        with self._lock:
            eng = self._get_engine()
            try:
                eng.setProperty("rate", -1 if lang == "zh" else 0)
                eng.setProperty("volume", max(0.0, min(1.0, float(volume))))
            except Exception:
                pass
            eng.say(text)
            eng.runAndWait()

    def stop(self):
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass


def play_wav(path):
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME)
        return True
    except Exception:
        pass
    try:
        import sounddevice as sd
        import soundfile as sf
        data, sr = sf.read(path, dtype="float32")
        sd.play(data, sr)
        sd.wait()
        return True
    except Exception:
        return False


class VoiceService:
    SOURCE_KEYS = {
        "chat": "voice_chat_enabled",
        "mail": "voice_mail_enabled",
        "pet": "voice_pet_enabled",
        "test": "voice_enabled",
    }

    def __init__(self, settings, on_error=None):
        self.settings = settings
        self.on_error = on_error
        self.piper = PiperBackend(settings)
        self.sapi = SapiBackend()
        self._q = queue.Queue()
        self._stop = threading.Event()
        self._thread = None
        self._gen = 0
        self._gen_lock = threading.Lock()
        self._last_spoken = {}
        self._last_lock = threading.Lock()
        self._tmp = os.path.join(APP_DATA, "tmp")
        os.makedirs(self._tmp, exist_ok=True)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def speak(self, text, source="chat", interrupt=False, force=False):
        if not self.settings.get("voice_enabled", True):
            return
        key = self.SOURCE_KEYS.get(source, "voice_enabled")
        if not self.settings.get(key, True):
            return
        if not text:
            return
        # Guard against duplicate automatic reads (e.g. a signal firing twice).
        now = time.monotonic()
        norm = " ".join(text.split())
        with self._last_lock:
            last = self._last_spoken.get((source, norm))
            if not force and last is not None and now - last < 2.5:
                return
            self._last_spoken[(source, norm)] = now
        if interrupt:
            self.interrupt()
        with self._gen_lock:
            gen = self._gen
        self._q.put((text, source, gen))

    def interrupt(self):
        with self._gen_lock:
            self._gen += 1
            gen = self._gen
        self._drain()
        self._stop_audio()
        return gen

    def _drain(self):
        while True:
            try:
                self._q.get_nowait()
                self._q.task_done()
            except queue.Empty:
                break

    def _stop_audio(self):
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except Exception:
            pass
        self.sapi.stop()

    def status(self):
        if self.piper.available():
            return "Piper huayan / Alba"
        if self.sapi.available():
            return "Windows SAPI 女声（回退）"
        return "无可用语音"

    def _loop(self):
        while not self._stop.is_set():
            try:
                text, source, gen = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                with self._gen_lock:
                    current = self._gen
                if gen == current:
                    self._speak_now(text, gen)
            except Exception as exc:
                if self.on_error:
                    self.on_error(str(exc))
            finally:
                self._q.task_done()

    def _speak_now(self, text, gen=None):
        lang = voice_lang(text)
        if self.piper.available():
            out = os.path.join(self._tmp, f"voice_{lang}.wav")
            try:
                if self.piper.synth(text, lang, out):
                    if gen is not None:
                        with self._gen_lock:
                            if gen != self._gen:
                                return
                    if play_wav(out):
                        return
            except Exception:
                pass
        if gen is not None:
            with self._gen_lock:
                if gen != self._gen:
                    return
        if self.sapi.available():
            self.sapi.speak(text, lang, self.settings.get("voice_volume", 0.9))
            return
        raise RuntimeError("没有可用的女声引擎")

    def stop(self):
        self._stop.set()
        self.interrupt()
        self.sapi.stop()
