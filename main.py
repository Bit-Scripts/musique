import sys
import os
import platform
import random
import asyncio
import numpy as np
import qasync

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, 
    QSlider, QHBoxLayout, QFileDialog, QListWidget, QApplication
)
import json
from PyQt5.QtGui import (
    QPixmap, QIcon, QLinearGradient, QBrush, QColor, 
    QRegion, QPainter, QPainterPath, QFont, QCursor
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QPoint, 
    QRect, QStandardPaths
)
from PyQt5.QtSvg import QSvgWidget
import pyqtgraph as pg

# Imports Modulaires
from core.discord_rpc import DiscordRPCManager
from core.audio_engine import AudioEngine, WaveformWorker
from core.metadata import MetadataExtractor
from core.update_checker import UpdateChecker
from ui.components import MovableLabel, HoverButton

class FolderLoaderWorker(QThread):
    """Charge le dossier de manière asynchrone pour ne pas "freezer" l'interface principale"""
    progress = pyqtSignal(int, int) # count, total
    trackLoaded = pyqtSignal(tuple) # (num, artist, title, path, album)
    finished = pyqtSignal()

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        files_to_process = []
        added_names = set()
        for root, _, files in os.walk(self.folder_path):
            for f in files:
                lower_f = f.lower()
                if lower_f.endswith((".mp3", ".wav", ".flac", ".ogg")) and "%l" not in lower_f and "%r" not in lower_f:
                    if f not in added_names:
                        files_to_process.append(os.path.join(root, f))
                        added_names.add(f)
                    
        total = len(files_to_process)
        
        for i, file_path in enumerate(files_to_process):
            try:
                metadata = MetadataExtractor.get_metadata(file_path)
                if metadata:
                    self.trackLoaded.emit((
                        int(metadata['tracknumber'] or 0),
                        metadata['artist'],
                        metadata['title'],
                        file_path,
                        metadata['album']
                    ))
            except Exception as e:
                print(f"Erreur Worker pour {file_path}: {e}")
            self.progress.emit(i + 1, total)

        self.finished.emit()


class MusicPlayer(QMainWindow):
    def __init__(self, application_path):
        super().__init__()
        self.application_path = application_path
        
        self.setWindowIcon(QIcon(os.path.join(self.application_path, 'data', 'Music bot.png')))

        self.discord_manager = DiscordRPCManager(
            client_id_discord=os.getenv('DISCORD_CLIENT_ID'),
            client_id_imgur=os.getenv('IMGUR_CLIENT_ID')
        )
        self.audio_engine = AudioEngine()
        
        # Audio signals
        self.audio_engine.positionChanged.connect(self.on_position_changed)
        self.audio_engine.durationChanged.connect(self.on_duration_changed)
        self.audio_engine.trackFinished.connect(self.play_next_track)

        self.waveformWorker = None
        self.folderLoader = None
        
        # Etats et Listes
        self.is_playing = False
        self.is_random = False
        self.repeat_state = 0
        self.orderedPlaylist = {}
        self.track_list = []
        self.track_paths = []
        self.current_track_index = -1
        self.samples = None

        self.press_control = 0
        self.value = 0
        self.oldPos = None

        # Gestion Sauvegarde Playlist
        config_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        self.playlist_file = os.path.join(config_dir, 'playlist.json')

        self.initUI()
        self.clearWaveform()
        self.load_playlist()


    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)  
        self.setAttribute(Qt.WA_TranslucentBackground) 
        
        self.movableWidget = QWidget() 
        vbox = QVBoxLayout(self.movableWidget)
        movable_label = MovableLabel(self)
        vbox.addWidget(movable_label)
        vbox.setAlignment(Qt.AlignTop)
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)
        
        self.minimizeButton = HoverButton(
            os.path.join(self.application_path, 'data', 'reduce-one.svg'),
            os.path.join(self.application_path, 'data', 'reduce-one-hover.svg'),
            self
        )
        self.maximizeButton = HoverButton(
            os.path.join(self.application_path, 'data', 'add-one.svg'),
            os.path.join(self.application_path, 'data', 'add-one-hover.svg'),
            self
        )
        self.closeButton = HoverButton(
            os.path.join(self.application_path, 'data', 'close-one.svg'),
            os.path.join(self.application_path, 'data', 'close-one-hover.svg'),
            self
        )

        css = """QPushButton { background-color: transparent; border: none; icon-size: 35px 35px; }"""
        self.minimizeButton.setStyleSheet(css)
        self.maximizeButton.setStyleSheet(css)
        self.closeButton.setStyleSheet(css)

        self.minimizeButton.clicked.connect(self.showMinimized)
        self.maximizeButton.clicked.connect(self.toggleMaximizeRestore)
        self.closeButton.clicked.connect(self.close)

        titleLabel = QLabel("BIT SCRIPTS - Musique", self)
        titleLabel.setAlignment(Qt.AlignCenter)
        titleLabel.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        
        self.updateBtn = QPushButton("🎁 MAJ !", self)
        self.updateBtn.setFont(QFont("Arial", 10, QFont.Bold))
        self.updateBtn.setStyleSheet("background-color: #ff6b6b; color: white; border-radius: 8px; padding: 4px 8px;")
        self.updateBtn.hide()
        self.update_url = ""
        self.updateBtn.clicked.connect(self.open_update_url)

        control_layout = QHBoxLayout()
        control_layout.addStretch()
        control_layout.addWidget(titleLabel)
        control_layout.addWidget(self.updateBtn)
        control_layout.addWidget(self.minimizeButton)
        control_layout.addWidget(self.maximizeButton)
        control_layout.addWidget(self.closeButton)

        self.setWindowTitle('BIT SCRIPTS - Musique')
        self.setGeometry(100, 100, 400, 800)
        
        # === STYLE GLOBAL ===
        self.applyGlobalStylesheet()
        
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QVBoxLayout(centralWidget)
        mainLayout.addLayout(control_layout)

        # Image pochette
        self.albumArtLayout = QHBoxLayout()  
        self.albumArtLayout.addStretch()
        self.albumArtLabel = QLabel(self)
        self.default_cover = os.path.join(self.application_path, 'data', 'Music bot.png')
        self.albumArtLabel.setPixmap(QPixmap(self.default_cover).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.albumArtLayout.addWidget(self.albumArtLabel)
        self.albumArtLayout.addStretch()
        
        # Labels informations (Artist & titre)
        infoLayout = QVBoxLayout()
        self.artistLabel = QLabel('Artiste : Pas de musique chargée', self)
        self.artistLabel.setAlignment(Qt.AlignCenter)
        self.songLabel = QLabel('Musique : Pas de musique chargée', self)
        self.songLabel.setAlignment(Qt.AlignCenter)
        infoLayout.addWidget(self.artistLabel)
        infoLayout.addWidget(self.songLabel)

        # WaveForm / Visualizer PyqtGraph
        self.waveformPlot = pg.PlotWidget()
        self.waveformPlot.getAxis('left').setVisible(False)
        self.waveformPlot.getAxis('bottom').setVisible(False)
        self.set_gradient_background(self.waveformPlot)
        self.playedWaveform = self.waveformPlot.plot(pen=pg.mkPen('b', width=2))  
        self.remainingWaveform = self.waveformPlot.plot(pen=pg.mkPen('g', width=2))
        
        # Progession (Temps + Slider)
        self.elapsedTimeLabel = QLabel('0:00', self)
        self.remainingTimeLabel = QLabel('-0:00', self)
        self.progressBar = QSlider(Qt.Horizontal, self)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        self.progressBar.sliderReleased.connect(self.on_progressbar_released)

        progressLayout = QHBoxLayout()
        progressLayout.addWidget(self.elapsedTimeLabel)
        progressLayout.addWidget(self.progressBar)
        progressLayout.addWidget(self.remainingTimeLabel)
        
        # Volume
        self.volumeSlider = QSlider(Qt.Horizontal, self)
        self.volumeSlider.setMinimum(0) 
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(75) 
        self.volumeSlider.valueChanged.connect(self.setVolume)
        
        self.volumeMinusLabel = QLabel(self)
        self.load_svg_in_label(self.volumeMinusLabel, os.path.join(self.application_path, 'data', 'volume-down.svg'))
        self.volumePlusLabel = QLabel(self)
        self.load_svg_in_label(self.volumePlusLabel, os.path.join(self.application_path, 'data', 'volume-up.svg'))
        
        self.volumeLayout = QHBoxLayout()
        self.volumeLayout.addWidget(self.volumeMinusLabel)
        self.volumeLayout.addWidget(self.volumeSlider) 
        self.volumeLayout.addWidget(self.volumePlusLabel) 

        # Controls & Buttons
        controlLayout = QHBoxLayout()
        btnPrevious = QPushButton('|◄◄')
        self.btnPlayPause = QPushButton('▶')
        btnNext = QPushButton('►►|')
        
        btnPrevious.setFont(QFont("Arial", 14))
        btnNext.setFont(QFont("Arial", 14))
        
        btnPrevious.clicked.connect(self.play_previous_track)
        self.btnPlayPause.clicked.connect(self.load_music)
        btnNext.clicked.connect(self.play_next_track)

        self.apply_style_to_button(btnPrevious, True)
        self.apply_style_to_button(self.btnPlayPause, True)
        self.apply_style_to_button(btnNext, True)

        self.randomButton = QPushButton()
        self.randomButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'shuffle.svg')))
        self.randomButton.clicked.connect(self.on_random_clicked)
        self.apply_style_to_button(self.randomButton, False)

        self.repeatButton = QPushButton()
        self.repeatButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'refresh.svg')))
        self.repeatButton.clicked.connect(self.on_repeat_clicked)
        self.apply_style_to_button(self.repeatButton, False)
        
        controlRandomRepeatLayout = QHBoxLayout()
        controlRandomRepeatLayout.addWidget(self.randomButton)
        controlRandomRepeatLayout.addWidget(self.repeatButton)
        
        self.listWidget = QListWidget(self)
        self.listWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.listWidget.itemClicked.connect(self.on_list_item_clicked)
        
        controlLayout.addWidget(btnPrevious)
        controlLayout.addWidget(self.btnPlayPause)
        controlLayout.addWidget(btnNext)
        
        controlAllLayout = QVBoxLayout()
        controlAllLayout.addLayout(controlLayout)
        controlAllLayout.addLayout(controlRandomRepeatLayout)
        
        # Playlist manager (Add / Clear)
        self.addButton = QPushButton()
        self.addButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'edit-add.svg')))
        self.apply_style_to_button(self.addButton, True)
        self.clearButton = QPushButton()
        self.clearButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'edit-clear.svg')))
        self.apply_style_to_button(self.clearButton, True)

        self.addButton.clicked.connect(self.load_music)
        self.clearButton.clicked.connect(self.on_clear_clicked)

        playlistManagerLayout = QHBoxLayout()
        playlistManagerLayout.addWidget(self.addButton)
        playlistManagerLayout.addWidget(self.clearButton)
        
        # Assemblage Principal
        mainLayout.addWidget(self.movableWidget)
        mainLayout.addLayout(self.albumArtLayout)
        mainLayout.addLayout(infoLayout)
        mainLayout.addLayout(progressLayout)
        mainLayout.addLayout(self.volumeLayout)
        mainLayout.addLayout(controlAllLayout)
        mainLayout.addWidget(self.listWidget)
        mainLayout.addLayout(playlistManagerLayout)
        mainLayout.addWidget(self.waveformPlot)
        

    def applyGlobalStylesheet(self):
        self.setStyleSheet("""
            QMainWindow { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0C1428, stop:1 #0D5E7E); border-radius: 10px; }
            QLabel, QPushButton { color: #FFF; }
            QPushButton::hover { background-color: #0D7EAA; }
            QListWidget { background-color: rgba(0,0,0,0); color: #fff; min-height: 150px;}
            QSlider::groove:horizontal { border: 1px solid #bbb; background: white; height: 10px; border-radius: 4px; }
            QSlider::sub-page:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0D5E7E, stop:1 #0C1428); border: 1px solid #777; height: 10px; border-radius: 4px; }
            QSlider::add-page:horizontal { background: #fff; border: 1px solid #777; height: 10px; border-radius: 4px; }
            QSlider::handle:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0D5E7E, stop:1 #0C1428); border: 1px solid #5c5c5c; width: 18px; margin-top: -2px; margin-bottom: -2px; border-radius: 3px; }
            QPlotWidget { min-height: 60px; }
            QScrollBar:vertical { border: 1px solid #999; background:white; width:10px; margin: 0px;}
            QScrollBar:horizontal { border: 1px solid #999; background:white; height:10px; margin: 0px;}
            QScrollBar::handle:vertical { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0D5E7E, stop:1 #0C1428); min-height: 0px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

    def set_gradient_background(self, plot_widget):
        gradient = QLinearGradient(0, 0, plot_widget.width(), 0)
        gradient.setColorAt(0, QColor("#0C1428"))
        gradient.setColorAt(1, QColor("#218EB8"))
        plot_widget.setBackground(QBrush(gradient))


    def apply_style_to_button(self, button, activate):
        if not isinstance(button, QPushButton): return
        color = "#0D5E7E" if activate else "#7E7E7E"
        hover_color = "#0D7EAA" if activate else "#AAAAAA"
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border-style: outset; border-width: 2px;
                border-radius: 10px; border-color: #0C1428;
                font: bold 14px; min-width: 1em; padding: 6px; icon-size: 20px;
            }}
            QPushButton::hover {{ background-color: {hover_color}; }}
        """)

    def load_svg_in_label(self, label, svg_path, size=QSize(30, 30)):
        svg_widget = QSvgWidget(svg_path)
        svg_renderer = svg_widget.renderer()
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        svg_renderer.render(painter)
        painter.end()
        label.setPixmap(pixmap)

    # ==== LECTURE DOSSIERS & QTHREAD ====
    def load_music(self):
        default_folder = QStandardPaths.writableLocation(QStandardPaths.MusicLocation)
        opts = QFileDialog.DontUseNativeDialog if platform.system() == 'Linux' else QFileDialog.ShowDirsOnly
        folder_path = QFileDialog.getExistingDirectory(None, "Select Folder", default_folder, opts)
        
        if not folder_path: return

        # Vider la liste actuelle avant d'importer le nouveau dossier pour éviter la superposition
        self.on_clear_clicked()

        # On lance le chargement asynchrone (Non-Bloquant)
        self.artistLabel.setText(f'Chargement des morceaux...')
        self.folderLoader = FolderLoaderWorker(folder_path)
        self.folderLoader.trackLoaded.connect(self._on_track_loaded)
        self.folderLoader.finished.connect(self._on_folder_scan_finished)
        self.folderLoader.start()

    def _on_track_loaded(self, track_data):
        """Reçoit une musique traitée du QThread et l'ajoute"""
        num, artist, title, path, album = track_data
        self.track_list.append((num, artist, title, path))
        self.track_paths.append(path)
        
        if album not in self.orderedPlaylist:
            self.orderedPlaylist[album] = []
        self.orderedPlaylist[album].append(track_data)
        
        self.listWidget.addItem(f"{num}. {artist} - {title}")

    def _on_folder_scan_finished(self):
        """Quand l'analyse du répertoire est accomplie"""
        self.artistLabel.setText(f'Chargement complet !')
        if self.is_random:
            self.random_order()
            
        self.btnPlayPause.disconnect()
        self.btnPlayPause.clicked.connect(self.toggle_play_pause)
        
        self.save_playlist()
        
        if self.track_paths and self.current_track_index == -1:
            self.play_track(0)

    # ==== CONTROLE LECTURE ====
    def toggle_play_pause(self):
        if self.current_track_index == -1: return

        if self.is_playing:
            self.audio_engine.pause()
            self.btnPlayPause.setText('▶')
            self.is_playing = False
        else:
            self.audio_engine.play()
            self.btnPlayPause.setText('❚❚')
            self.is_playing = True

    def on_list_item_clicked(self, item):
        index = self.listWidget.row(item)
        self.play_track(index)

    def play_track(self, index):
        if 0 <= index < len(self.track_paths):
            self.current_track_index = index
            filepath = self.track_paths[index]
            self.audio_engine.load_track(filepath)
            
            # MAJ UI Metadonnées
            track = self.track_list[index]
            artist, title = track[1], track[2]
            self.artistLabel.setText(f"Artiste : {artist}")
            self.songLabel.setText(f"Musique : {title}")
            
            # Recherche Image Couverture (Tag MP3 en priorité)
            cover_path = MetadataExtractor.get_best_cover(filepath) or self.default_cover
            resized_cover = MetadataExtractor.resize_cover_for_cache(cover_path)
            self.albumArtLabel.setPixmap(QPixmap(resized_cover).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            self.audio_engine.play()
            self.btnPlayPause.setText('❚❚')
            self.is_playing = True

            # Waveform
            self.progressBar.setValue(0)
            self.loadWaveform(filepath)

            # Envoi asynchrone Discord (qui upload Imgur)
            if hasattr(self, 'current_rpc_task') and self.current_rpc_task:
                self.current_rpc_task.cancel()
                
            # Si c'est l'image par défaut, inutile de l'uploader sur Imgur (music_bot est pré-inclus dans l'App Discord)
            rpc_cover = resized_cover if cover_path != self.default_cover else ""
            self.current_rpc_task = asyncio.create_task(self.discord_manager.upload_image_and_update_rpc(rpc_cover, title, artist))

    def play_previous_track(self):
        if self.audio_engine.current_position > 3000:
            self.audio_engine.set_position(0)
        elif self.current_track_index > 0:
            self.play_track(self.current_track_index - 1)

    def play_next_track(self):
        if not self.track_paths or self.current_track_index == -1: 
            return

        if self.repeat_state == 0:  # Pas de répétition globale optionnelle (stoppe fin de liste)
            if self.current_track_index < len(self.track_paths) - 1:
                self.play_track(self.current_track_index + 1)
        elif self.repeat_state == 1:  # Playlist en boucle
            nx = (self.current_track_index + 1) % len(self.track_paths)
            self.play_track(nx)
        elif self.repeat_state == 2:  # Répéter morceau
            self.audio_engine.set_position(0)
            self.audio_engine.play()

    def setVolume(self, value):
        self.audio_engine.set_volume(value)
        if value == 0: self.load_svg_in_label(self.volumeMinusLabel, os.path.join(self.application_path, 'data', 'volume-mute.svg'))
        else: self.load_svg_in_label(self.volumeMinusLabel, os.path.join(self.application_path, 'data', 'volume-down.svg'))
        
        if value == 100: self.load_svg_in_label(self.volumePlusLabel, os.path.join(self.application_path, 'data', 'volume-notice.svg'))
        else: self.load_svg_in_label(self.volumePlusLabel, os.path.join(self.application_path, 'data', 'volume-up.svg'))
        
    def on_progressbar_released(self):
        click_position = QCursor.pos()
        slider_length = self.progressBar.width()
        click_x = click_position.x() - self.progressBar.mapToGlobal(QPoint(0,0)).x()
        percentage = click_x / slider_length

        new_pos = int(percentage * self.audio_engine.total_duration)
        self.audio_engine.set_position(new_pos)

    # ==== GESTION DES EVENEMENTS LECTEUR AUDIO ====
    def on_duration_changed(self, duration_ms):
        self.progressBar.setMaximum(duration_ms)
        self.update_time_labels(self.audio_engine.current_position, duration_ms)

    def on_position_changed(self, pos_ms):
        if not self.progressBar.isSliderDown():
            self.progressBar.setValue(pos_ms)
        self.update_time_labels(pos_ms, self.audio_engine.total_duration)
        self.update_waveform_visual(pos_ms, self.audio_engine.total_duration)

    def update_time_labels(self, pos_ms, dur_ms):
        el_mins, el_secs = pos_ms // 60000, (pos_ms % 60000) // 1000
        rem = max(0, dur_ms - pos_ms)
        rm_mins, rm_secs = rem // 60000, (rem % 60000) // 1000
        self.elapsedTimeLabel.setText(f'{el_mins}:{el_secs:02d}')
        self.remainingTimeLabel.setText(f'-{rm_mins}:{rm_secs:02d}')

    # ==== WAFERFORM WAVE SYNC ====
    def loadWaveform(self, filepath):
        if self.waveformWorker and self.waveformWorker.isRunning():
            self.waveformWorker.stop()

        self.waveformWorker = WaveformWorker(filepath)
        self.waveformWorker.waveformReady.connect(self._on_waveform_ready)
        self.waveformWorker.start()

    def _on_waveform_ready(self, samples):
        self.samples = samples
        self.waveformPlot.clear() 
        self.remainingWaveform = self.waveformPlot.plot(self.samples, pen=pg.mkPen('g', width=2))
        self.playedWaveform = self.waveformPlot.plot(pen=pg.mkPen('b', width=2))
        self.waveformPlot.getAxis('left').setVisible(False)
        self.waveformPlot.getAxis('bottom').setVisible(False)
        
    def update_waveform_visual(self, pos_ms, dur_ms):
        if self.samples is not None and dur_ms > 0:
            progress = pos_ms / dur_ms
            idx = int(len(self.samples) * progress)
            self.playedWaveform.setData(self.samples[:idx])

    def clearWaveform(self):
        emptyData = np.array([])
        self.playedWaveform.setData(emptyData)
        self.remainingWaveform.setData(emptyData)

    # ==== UTILS ====
    def on_clear_clicked(self):
        self.current_track_index = -1
        self.track_paths.clear()
        self.track_list.clear()
        self.audio_engine.stop()
        
        self.orderedPlaylist.clear()
        self.listWidget.clear()
        self.is_playing = False
        self.btnPlayPause.setText('▶')
        self.albumArtLabel.setPixmap(QPixmap(self.default_cover).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.artistLabel.setText("Artiste : Pas de musique")
        self.songLabel.setText("Musique : Pas de musique")
        self.clearWaveform()
        
        if hasattr(self, 'current_rpc_task') and self.current_rpc_task:
            self.current_rpc_task.cancel()
        self.current_rpc_task = asyncio.create_task(self.discord_manager.upload_image_and_update_rpc("", "", ""))
        
        self.save_playlist()
        
        self.btnPlayPause.disconnect()
        self.btnPlayPause.clicked.connect(self.load_music)

    def on_random_clicked(self):
        self.is_random = not self.is_random
        if self.is_random:
            self.random_order()
            self.apply_style_to_button(self.randomButton, True)
        else:
            self.restore_original_order()
            self.apply_style_to_button(self.randomButton, False)

        if self.audio_engine.current_filepath:
            try:
                self.current_track_index = self.track_paths.index(self.audio_engine.current_filepath)
            except ValueError:
                self.current_track_index = 0

    def random_order(self):
        if not self.track_list: return
        combined_list = list(zip(self.track_list, self.track_paths))
        random.shuffle(combined_list)
        self.track_list, self.track_paths = map(list, zip(*combined_list))
        self.update_list_widget()

    def restore_original_order(self):
        self.track_paths.clear()
        self.track_list.clear()
        self.listWidget.clear()
        for album in self.orderedPlaylist:
            for track in self.orderedPlaylist[album]:
                num, artist, title, path, _ = track
                self.listWidget.addItem(f"{num}. {artist} - {title}")
                self.track_paths.append(path)
                self.track_list.append((num, artist, title, path))

    def update_list_widget(self):
        self.listWidget.clear()
        for track in self.track_list:
            self.listWidget.addItem(f"{track[0]}. {track[1]} - {track[2]}")

    def save_playlist(self):
        try:
            data = {
                'track_list': self.track_list,
                'track_paths': self.track_paths,
                'orderedPlaylist': self.orderedPlaylist
            }
            with open(self.playlist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde playlist : {e}")

    def load_playlist(self):
        if os.path.exists(self.playlist_file):
            try:
                with open(self.playlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.track_list = [tuple(t) for t in data.get('track_list', [])]
                self.track_paths = data.get('track_paths', [])
                self.orderedPlaylist = data.get('orderedPlaylist', {})
                
                if self.track_list:
                    self.update_list_widget()
                    self.artistLabel.setText(f'Playlist restaurée ({len(self.track_list)} titres)')
                    self.btnPlayPause.disconnect()
                    self.btnPlayPause.clicked.connect(self.toggle_play_pause)
            except Exception as e:
                print(f"Erreur chargement playlist : {e}")

    def on_repeat_clicked(self):
        self.repeat_state = (self.repeat_state + 1) % 3
        if self.repeat_state == 2:
            self.repeatButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'refresh-1.svg')))
        else:
            self.repeatButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'refresh.svg')))
        self.apply_style_to_button(self.repeatButton, self.repeat_state > 0)

    # ==== FENETRE REDIMENSIONNABLE & CUSTOM MOVEMENT ====
    def eventFilter(self, obj, e):
        if e.type() == 129 and self.press_control == 0: self.pos_control(e)
        if e.type() == 2:
            self.press_control = 1
            self.origin = self.mapToGlobal(e.pos())
            self.ori_geo = self.geometry()
        if e.type() == 3:
            self.press_control = 0
            self.pos_control(e)
        if e.type() == 5 and self.cursor().shape() != Qt.ArrowCursor:
            self.resizing(self.origin, e, self.ori_geo, self.value)
        return True

    def pos_control(self, e):
        rect = self.rect()
        tl, tr, bl, br = rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()
        pos = e.pos()
        if pos in QRect(QPoint(tl.x()+5,tl.y()), QPoint(tr.x()-5,tr.y()+5)): self.setCursor(Qt.SizeVerCursor); self.value = 1
        elif pos in QRect(QPoint(bl.x()+5,bl.y()), QPoint(br.x()-5,br.y()-5)): self.setCursor(Qt.SizeVerCursor); self.value = 2
        elif pos in QRect(QPoint(tr.x()-5,tr.y()+5), QPoint(br.x(),br.y()-5)): self.setCursor(Qt.SizeHorCursor); self.value = 3
        elif pos in QRect(QPoint(tl.x()+5,tl.y()+5), QPoint(bl.x(),bl.y()-5)): self.setCursor(Qt.SizeHorCursor); self.value = 4
        elif pos in QRect(QPoint(tr.x(),tr.y()), QPoint(tr.x()-5,tr.y()+5)): self.setCursor(Qt.SizeBDiagCursor); self.value = 5
        elif pos in QRect(QPoint(bl.x(),bl.y()), QPoint(bl.x()+5,bl.y()-5)): self.setCursor(Qt.SizeBDiagCursor); self.value = 6
        elif pos in QRect(QPoint(tl.x(),tl.y()), QPoint(tl.x()+5,tl.y()+5)): self.setCursor(Qt.SizeFDiagCursor); self.value = 7
        elif pos in QRect(QPoint(br.x(),br.y()), QPoint(br.x()-5,br.y()-5)): self.setCursor(Qt.SizeFDiagCursor); self.value = 8
        else: self.setCursor(Qt.ArrowCursor)       

    def resizing(self, ori, e, geo, value):
        last = self.mapToGlobal(e.pos())-ori
        if value == 1:
            h = geo.height() - last.y()
            if h > self.minimumHeight(): self.setGeometry(geo.x(), geo.y() + last.y(), geo.width(), h)
        elif value == 2: self.resize(geo.width(), geo.height() + last.y())
        elif value == 3: self.resize(geo.width() + last.x(), geo.height())
        elif value == 4:
            w = geo.width() - last.x()
            if w > self.minimumWidth(): self.setGeometry(geo.x() + last.x(), geo.y(), w, geo.height())
        elif value == 8: self.setGeometry(geo.x(), geo.y(), geo.width() + last.x(), geo.height() + last.y())  

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.oldPos = e.globalPos()
    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and hasattr(self, 'oldPos') and self.oldPos is not None:
            delta = QPoint(e.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = e.globalPos()
    def mouseReleaseEvent(self, e):
        self.oldPos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#0C1428"))
        gradient.setColorAt(1, QColor("#0D5E7E"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen) 
        painter.drawRoundedRect(self.rect(), 15, 15)

    def toggleMaximizeRestore(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def open_update_url(self):
        import webbrowser
        if self.update_url:
            webbrowser.open(self.update_url)

    def closeEvent(self, event):
        # Nettoyage synchrones
        if self.waveformWorker: self.waveformWorker.stop()
        
        # Nettoyage asynchrone (purge de la présence Discord serveur avant la fin de process locale)
        if hasattr(self, 'discord_manager') and hasattr(self.discord_manager, 'close_async'):
            if not hasattr(self, '_closing_task_started'):
                self._closing_task_started = True
                event.ignore()      # On empêche la mort immédiate
                self.hide()         # Illusion pour l'utilisateur
                
                async def do_close():
                    try:
                        await self.discord_manager.close_async()
                    except Exception:
                        pass
                    finally:
                        self.close() # Rappel de closeEvent qui passera au Else !
                
                asyncio.create_task(do_close())
                return

        # Cas de repassage : la purge Discord a été faite (ou non-existante), l'app crash
        if hasattr(self, 'discord_manager') and hasattr(self.discord_manager, 'close'):
            self.discord_manager.close()
        
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("bs-musique")
    app.setOrganizationName("Bit-Scripts")
    
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    from pathlib import Path
    import platform
    if getattr(sys, 'frozen', False):
        if platform.system() == 'Darwin':
            app_path = Path(sys.executable).parent.parent / "Resources"
        else:
            app_path = sys._MEIPASS
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))

    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(app_path, '.env'))

    player = MusicPlayer(app_path)
    player.show()

    # Fermeture du splashscreen Pyinstaller généré (Image)
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass

    async def check_for_updates_task():
        checker = UpdateChecker(current_version="1.0.0", github_repo="Paul123321/Bit-Scripts")
        has_update, new_ver, url = await checker.check_for_updates()
        if has_update:
            player.updateBtn.setText(f"🎁 v{new_ver}")
            player.update_url = url
            player.updateBtn.show()

    loop.create_task(check_for_updates_task())
    loop.create_task(player.discord_manager.connect())

    with loop:
        loop.run_forever()

if __name__ == '__main__':
    main()
