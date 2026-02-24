import os
import numpy as np
from pydub import AudioSegment
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QUrl, QThread
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

class WaveformWorker(QThread):
    """
    QThread asynchrone pour la génération du visuel spectral audio (Waveform) 
    qui empêche le blocage de l'interface principale durant le chargement.
    """
    waveformReady = pyqtSignal(np.ndarray)

    def __init__(self, audio_file):
        super().__init__()
        self.audio_file = audio_file
        self.is_running = True

    def run(self):
        try:
            # Traitement parfois long selon la taille du fichier
            ext = os.path.splitext(self.audio_file)[-1].lower()
            format_map = {'.flac': 'flac', '.mp3': 'mp3', '.ogg': 'ogg', '.wav': 'wav'}
            audio_format = format_map.get(ext, 'mp3')
            
            # TODO : Utiliser un cache pour éviter de recalculer "samples" chaque fois
            # pour la même chanson.
            if self.is_running:
                audio = AudioSegment.from_file(self.audio_file, format=audio_format)
                samples = np.array(audio.get_array_of_samples())[::1000]
                self.waveformReady.emit(samples)
        except Exception as e:
            print(f"Erreur WaveForm pour {self.audio_file} : {e}")
        finally:
            audio = None

    def stop(self):
        self.is_running = False
        self.wait()


class AudioEngine(QObject):
    """
    Moteur audio basé sur PyQt5.QtMultimedia (QMediaPlayer).
    Remplace pygame.mixer pour une meilleure gestion native asynchrone
    et des capacités de lecture directes plus permissives pour PyQt5.
    """
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    trackFinished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        
        self.is_playing = False
        self._current_position = 0
        self._total_duration = 0
        self.current_filepath = ""

        # Signaux du lecteur vers l'interface
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)

    def load_track(self, filepath):
        """Charge une piste dans le lecteur."""
        self.current_filepath = filepath
        self.is_playing = False  # Prévient l'émission intempestive de 'trackFinished' en cas de skip manuel
        url = QUrl.fromLocalFile(filepath)
        self.player.setMedia(QMediaContent(url))
        self.player.stop()

    def play(self, start_pos_ms=0):
        if self.current_filepath:
            if start_pos_ms > 0:
                self.player.setPosition(start_pos_ms)
            self.player.play()
            self.is_playing = True

    def pause(self):
        self.is_playing = False
        self.player.pause()

    def stop(self):
        self.is_playing = False
        self.player.stop()

    def set_position(self, pos_ms):
        self.player.setPosition(pos_ms)

    def set_volume(self, volume):
        """Volume entre 0 et 100."""
        self.player.setVolume(volume)

    @property
    def current_position(self):
        return self._current_position

    @property
    def total_duration(self):
        return self._total_duration

    # --- Écouteurs Internes ---
    def _on_position_changed(self, pos):
        self._current_position = pos
        self.positionChanged.emit(pos)

    def _on_duration_changed(self, duration):
        self._total_duration = duration
        self.durationChanged.emit(duration)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.StoppedState and self.is_playing:
            # Si le lecteur s'arrête de lui-même (non pressé par l'utilisateur), fin de piste.
            self.is_playing = False
            self.trackFinished.emit()
