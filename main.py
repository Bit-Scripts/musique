import platform
if platform.system() == 'Linux' or platform.system() == 'Darwin':
    import subprocess
elif platform.system() == 'Windows':
    import psutil
import tempfile
from PIL import Image
import sys
import os
import random
from pathlib import Path
import numpy as np
from pydub import AudioSegment
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QSlider, QHBoxLayout, QFileDialog, QListWidget
from PyQt5.QtGui import QPixmap, QIcon, QLinearGradient, QBrush, QColor, QRegion, QPainter, QPainterPath, QFont, QCursor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, Qt, QSize, QPoint, QRect, QStandardPaths
from PyQt5.QtSvg import QSvgWidget
import pygame.mixer
import pyqtgraph as pg
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.wavpack import WavPack
from mutagen.wave import WAVE
import wave
from mutagen.easyid3 import EasyID3
import glob
import qasync
import asyncio
import pyimgur
import threading
from dotenv import load_dotenv

# Charge les variables d'environnement du fichier .env
extDataDir = None
if getattr(sys, 'frozen', False):
    # Chemin lorsqu'exécuté en tant que bundle .app avec PyInstaller
    if platform.system() == 'Darwin':  # macOS
        extDataDir = Path(sys.executable).parent.parent / "Resources"
    else:
        extDataDir = sys._MEIPASS
else:
    # Chemin pour le mode de développement
    extDataDir = os.getcwd()
    
load_dotenv(dotenv_path=os.path.join(extDataDir, '.env'))

def is_discord_running():
    # Cette fonction vérifie si Discord est en cours d'exécution sur l'ordinateur
    if platform.system() == 'Linux' or platform.system() == 'Darwin':
        try:
            # Remplacer par la méthode appropriée pour votre système d'exploitation
            process = subprocess.check_output(["pgrep", "Discord"])
            return process is not None
        except subprocess.CalledProcessError:
            return False
    elif platform.system() == 'Windows':
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'] == 'Discord.exe':
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False
    
if is_discord_running():
    from pypresence import Presence
    
def update_discord_rpc(title, artist, image, mainwindow):
    if is_discord_running():
        try:
            if title == "" and artist == "" and image == "":
                mainwindow.RPC.clear(pid=os.getpid())
                mainwindow.RPC.close()
                mainwindow.RPC.connect()
                return
            # Mise à jour de la présence avec les nouvelles informations
            mainwindow.RPC.update(details=title, state=artist, large_image=image, large_text="Entrain d'écouter")
            print("Réussite de la mise à jour de la présence Discord")
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la présence Discord: {e}")

class WaveformWorker(QThread):
    waveformReady = pyqtSignal(np.ndarray)

    def __init__(self, audio_file):
        super().__init__()
        self.audio_file = audio_file
        self.is_running = True

    def run(self):
        try:
            audio = AudioSegment.from_file(self.audio_file)
            # Réduisez la résolution des échantillons ici si nécessaire
            samples = np.array(audio.get_array_of_samples())[::1000]  # Par exemple, prenez un échantillon toutes les 1000 valeurs
            self.waveformReady.emit(samples)
        finally:
            # Assurez-vous de libérer les ressources ici
            audio = None 

    def stop(self):
        self.is_running = False
        self.wait()

class movable_label(QLabel):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        # self.setStyleSheet("background-color: #ccc")
        self.setMinimumHeight(30)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.parent.press_control == 0:
                self.pos = e.pos()
                self.main_pos = self.parent.pos()
        super().mousePressEvent(e)
        
    def mouseMoveEvent(self, e):
        if self.parent.cursor().shape() == Qt.ArrowCursor and isinstance(self.pos, QPoint):
            self.last_pos = e.pos() - self.pos
            self.main_pos += self.last_pos
            self.parent.move(self.main_pos)
        super(movable_label, self).mouseMoveEvent(e)

class HoverButton(QPushButton):
    def __init__(self, icon_path, hover_icon_path, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.hover_icon_path = hover_icon_path
        self.setIcon(QIcon(self.icon_path))

    def enterEvent(self, event):
        # Changement d'icône lorsque la souris entre dans le bouton
        self.setIcon(QIcon(self.hover_icon_path))

    def leaveEvent(self, event):
        # Retour à l'icône normale lorsque la souris quitte le bouton
        self.setIcon(QIcon(self.icon_path))

class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        if is_discord_running():
            client_id = os.getenv('DISCORD_CLIENT_ID')  # Remplacez par votre ID client Discord
            self.RPC = Presence(client_id)
            self.RPC.connect()
            self.uploaded_images_cache = {}
        else:
            print('Discord n\'a pas été détecté sur votre système d\'exploitation, vous ne pouvez donc pas profiter de Discord Rich Presence sur cette ordinateur.')
        
        self.movableWidget = QWidget() 
        vbox = QVBoxLayout(self.movableWidget)
        vbox.addWidget(movable_label(self))
        vbox.setAlignment(Qt.AlignTop)
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)
        
        # Initialisation des attributs de layout
        self.control_layout = QHBoxLayout()
        self.albumArtLayout = QHBoxLayout()
        self.infoLayout = QVBoxLayout()
        self.progressLayout = QHBoxLayout()
        self.volumeLayout = QHBoxLayout()
        self.controlAllLayout = QVBoxLayout()
        self.playlistManagerLayout = QHBoxLayout()
        
        self.waveformWorker = None
        
        if getattr(sys, 'frozen', False):
            # Exécuté en mode binaire
            if platform.system() == 'Darwin':  # macOS
                self.application_path = Path(sys.executable).parent.parent / "Resources"
            else:
                self.application_path = sys._MEIPASS
        else:
            # Exécuté en mode script
            self.application_path = os.path.dirname(os.path.abspath(__file__))
        
        self.press_control = 0
        
        self.filePath = ''
        
        self.samples = None
        
        self.is_playing = False
        
        self.is_random = False
        
        self.repeat_state = 0
        
        self.orderedPlaylist = {}
        
        self.track_list = []
        
        self.oldPos = 0
        
        self.newPos = 0.0
        
        self.volumeMinusLabel = None
        self.volumePlusLabel = None
        
        # Initialiser le QTimer pour vérifier l'état de la lecture
        self.playback_checker = QTimer(self)
        self.playback_checker.timeout.connect(self.check_playback_status)
        self.playback_checker.start(1000)
        
        self.is_manual_track_change = False
        self.manual_change_timer = QTimer(self)
        self.manual_change_timer.timeout.connect(self.reset_manual_track_change)
        self.manual_change_timer.setSingleShot(True)

        # Obtenez la durée totale de la piste ici et convertissez-la en millisecondes
        self.total_duration = 0 #int(self.get_audio_length(self.filePath) * 1000)  # Durée totale en millisecondes

        self.current_position = 0  # Position actuelle en millisecondes

        # Initialisez le timer après l'interface utilisateur
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(1000) 
        
        self.is_playing = False
        
        self.volume = 80
        
        self.track_paths = list()  # Liste pour stocker les chemins des fichiers
        self.current_track_index = 0 
        
        icon_path = os.path.join(self.application_path, 'data', 'Music bot.png')  # Chemin vers votre icône
        self.setWindowIcon(QIcon(icon_path))
        
        self.audio_file = None

        # Initialisation de l'interface utilisateur après avoir défini total_duration
        self.initUI()
        pygame.mixer.init()
        
    def resize_cover(self, cover_path, size=(252, 252)):
        with Image.open(cover_path) as img:
            # Redimensionner l'image
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Convertir en RGB si l'image est en mode RGBA
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            # Créer un fichier temporaire
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            img.save(temp_file.name, 'JPEG')

        return temp_file.name
        
    async def envoyer_image(self, chemin_fichier, title, artist):
        if is_discord_running():
            try:
                if chemin_fichier == "" and title == "" and artist == "":
                    print("Aucune information fournie pour l'image, la mise à jour RPC sera vide.")
                    threading.Thread(target=update_discord_rpc, args=("", "", "", self)).start()
                    return
                uploaded_image = None
                image_path_sans_prefixe = chemin_fichier[7:] if chemin_fichier.startswith("file://") else chemin_fichier
                if image_path_sans_prefixe in self.uploaded_images_cache:
                    print(f"L'image a déjà été téléchargée. URL: {self.uploaded_images_cache[image_path_sans_prefixe]}")
                    uploaded_image = self.uploaded_images_cache[image_path_sans_prefixe]
                client_id = os.getenv('IMGUR_CLIENT_ID')
                if not client_id:
                    raise ValueError("La clé API d'Imgur n'est pas définie dans les variables d'environnement.")
                    
                try:
                    # Téléchargez l'image et mettez à jour le cache
                    im = pyimgur.Imgur(client_id)
                    if uploaded_image is None:
                        uploaded_image = im.upload_image(image_path_sans_prefixe, title="Uploaded with PyImgur")
                        self.uploaded_images_cache[image_path_sans_prefixe] = uploaded_image.link
                        print(f"Image téléchargée avec succès. URL: {uploaded_image.link}")
                        uploaded_image = uploaded_image.link
                except Exception as e:
                    print(f"Une erreur est survenue lors du téléchargement de l'image : {e}")
                    return None
                if uploaded_image:
                    # Mettez à jour Discord RPC avec l'image Imgur
                    print("Réussite du téléchargement de l'image sur Imgur également")
                else:
                    print("Échec du téléchargement de l'image sur Imgur également")
                    uploaded_image = "music_bot"
            except Exception as e:
                print(f"Échec de la connexion ou du téléchargement de l'image : {e}")
                uploaded_image = "music_bot"
            threading.Thread(target=update_discord_rpc, args=(title, artist, uploaded_image, self)).start()

    def check_playback_status(self):
        if not pygame.mixer.music.get_busy() and self.is_playing and not self.is_manual_track_change:
            # La musique a fini de jouer, passer à la piste suivante
            self.play_next_track()
        
    def eventFilter(self, obj, e):
        #hovermoveevent
        if e.type() == 129:
            if self.press_control == 0:
                self.pos_control(e)#cursor position control for cursor shape setup

        #mousepressevent
        if e.type() == 2:
            self.press_control = 1
            self.origin = self.mapToGlobal(e.pos())
            self.ori_geo = self.geometry()

        #mousereleaseevent
        if e.type() == 3:

            self.press_control = 0
            self.pos_control(e)
        
        #mousemoveevent
        if e.type() == 5:
            if self.cursor().shape() != Qt.ArrowCursor:
                self.resizing(self.origin, e, self.ori_geo, self.value)

        return True

    def pos_control(self, e):
        rect = self.rect()
        top_left = rect.topLeft()
        top_right = rect.topRight()
        bottom_left = rect.bottomLeft()
        bottom_right = rect.bottomRight()
        pos = e.pos()

        #top catch
        if pos in QRect(QPoint(top_left.x()+5,top_left.y()), QPoint(top_right.x()-5,top_right.y()+5)):
            self.setCursor(Qt.SizeVerCursor)
            self.value = 1

        #bottom catch
        elif pos in QRect(QPoint(bottom_left.x()+5,bottom_left.y()), QPoint(bottom_right.x()-5,bottom_right.y()-5)):
            self.setCursor(Qt.SizeVerCursor)
            self.value = 2
        
        #right catch
        elif pos in QRect(QPoint(top_right.x()-5,top_right.y()+5), QPoint(bottom_right.x(),bottom_right.y()-5)):
            self.setCursor(Qt.SizeHorCursor)
            self.value = 3

        #left catch
        elif pos in QRect(QPoint(top_left.x()+5,top_left.y()+5), QPoint(bottom_left.x(),bottom_left.y()-5)):
            self.setCursor(Qt.SizeHorCursor)
            self.value = 4

        #top_right catch
        elif pos in QRect(QPoint(top_right.x(),top_right.y()), QPoint(top_right.x()-5,top_right.y()+5)):
            self.setCursor(Qt.SizeBDiagCursor)
            self.value = 5

        #botom_left catch
        elif pos in QRect(QPoint(bottom_left.x(),bottom_left.y()), QPoint(bottom_left.x()+5,bottom_left.y()-5)):
            self.setCursor(Qt.SizeBDiagCursor)
            self.value = 6

        #top_left catch
        elif pos in QRect(QPoint(top_left.x(),top_left.y()), QPoint(top_left.x()+5,top_left.y()+5)):
            self.setCursor(Qt.SizeFDiagCursor)
            self.value = 7

        #bottom_right catch
        elif pos in QRect(QPoint(bottom_right.x(),bottom_right.y()), QPoint(bottom_right.x()-5,bottom_right.y()-5)):
            self.setCursor(Qt.SizeFDiagCursor)
            self.value = 8
        
        #default
        else:
            self.setCursor(Qt.ArrowCursor)       

    def resizing(self, ori, e, geo, value):    
        #top_resize
        if self.value == 1:
            last = self.mapToGlobal(e.pos())-ori
            first = geo.height()
            first -= last.y()
            Y = geo.y()
            Y += last.y()

            if first > self.minimumHeight():
                self.setGeometry(geo.x(), Y, geo.width(), first)                    
        
        #bottom_resize
        if self.value == 2:
            last = self.mapToGlobal(e.pos())-ori
            first = geo.height()
            first += last.y()
            self.resize(geo.width(), first)

        #right_resize
        if self.value == 3:
            last = self.mapToGlobal(e.pos())-ori
            first = geo.width()
            first += last.x()
            self.resize(first, geo.height())

        #left_resize
        if self.value == 4:
            last = self.mapToGlobal(e.pos())-ori
            first = geo.width()
            first -= last.x()
            X = geo.x()
            X += last.x()

            if first > self.minimumWidth():
                self.setGeometry(X, geo.y(), first, geo.height())

        #top_right_resize
        if self.value == 5:
            last = self.mapToGlobal(e.pos())-ori
            first_width = geo.width()
            first_height = geo.height()
            first_Y = geo.y()
            first_width += last.x()
            first_height -= last.y()
            first_Y += last.y()
                
            if first_height > self.minimumHeight():
                self.setGeometry(geo.x(), first_Y, first_width, first_height)

        #bottom_right_resize
        if self.value == 6:
            last = self.mapToGlobal(e.pos())-ori
            first_width = geo.width()
            first_height = geo.height()
            first_X = geo.x()
            first_width -= last.x()
            first_height += last.y()
            first_X += last.x()
                
            if first_width > self.minimumWidth():
                self.setGeometry(first_X, geo.y(), first_width, first_height)

        #top_left_resize
        if self.value == 7:
            last = self.mapToGlobal(e.pos())-ori
            first_width = geo.width()
            first_height = geo.height()
            first_X = geo.x()
            first_Y = geo.y()
            first_width -= last.x()
            first_height -= last.y()
            first_X += last.x()
            first_Y += last.y()
                
            if first_height > self.minimumHeight() and first_width > self.minimumWidth():
                self.setGeometry(first_X, first_Y, first_width, first_height)

        #bottom_right_resize
        if self.value == 8:
            last = self.mapToGlobal(e.pos())-ori
            first_width = geo.width()
            first_height = geo.height()
            first_width += last.x()
            first_height += last.y()                    
            
            self.setGeometry(geo.x(), geo.y(), first_width, first_height)  
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.oldPos is not None:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None
        
    def get_audio_length(self, file_path):
        ext = os.path.splitext(file_path)[-1].lower()

        if ext == '.mp3':
            audio = MP3(file_path)
            audio_length = audio.info.length
        elif ext == '.flac':
            audio = FLAC(file_path)
            audio_length = audio.info.length
        elif ext == '.ogg':
            audio = OggVorbis(file_path)
            audio_length = audio.info.length
        elif ext == '.wav':
            with wave.open(file_path, 'r') as audio:
                frames = audio.getnframes()
                rate = audio.getframerate()
                audio_length = frames / float(rate)
        else:
            audio_length = 0  # ou gérer l'erreur

        return audio_length  # durée en secondes

    def load_svg_in_label(self, label, svg_path, size=QSize(30, 30)):
        svg_widget = QSvgWidget(svg_path)
        svg_renderer = svg_widget.renderer()
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        svg_renderer.render(painter)
        painter.end()
        label.setPixmap(pixmap)

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove the title bar
        self.setAttribute(Qt.WA_TranslucentBackground) 
        
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

        css = """
                QPushButton {
                    background-color: transparent;
                    border: none;
                    icon-size: 35px 35px;
                }
            """
        # Appliquer le même style pour les trois boutons
        self.minimizeButton.setStyleSheet(css)
        self.maximizeButton.setStyleSheet(css)
        self.closeButton.setStyleSheet(css)

        # Connecter les signaux et les slots
        self.minimizeButton.clicked.connect(self.showMinimized)
        self.maximizeButton.clicked.connect(self.toggleMaximizeRestore)
        self.closeButton.clicked.connect(self.close)

        # Créez un nouveau QLabel pour le titre
        titleLabel = QLabel("BIT SCRIPTS - Musique", self)
        titleLabel.setAlignment(Qt.AlignCenter)
        # Configurez le style et la taille de police si nécessaire
        titleLabel.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")

        # Ajouter les boutons au layout
        control_layout = QHBoxLayout()
        control_layout.addStretch()
        control_layout.addWidget(titleLabel)
        control_layout.addWidget(self.minimizeButton)
        control_layout.addWidget(self.maximizeButton)
        control_layout.addWidget(self.closeButton)

        # Fenêtre principale
        self.setWindowTitle('BIT SCRIPTS - Musique')
        self.setGeometry(100, 100, 400, 800)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0C1428, stop:1 #0D5E7E);
                border-radius: 10px;
            }

            QLabel, QPushButton {
                color: #FFF;
            }
            
            QPushButton::hover {
                background-color: #0D7EAA;
            }

            QListWidget {
                background-color: rgba(0,0,0,0);
                color: #fff;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0D5E7E, stop:1 #0C1428);
                border: 1px solid #777;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::add-page:horizontal {
                background: #fff;
                border: 1px solid #777;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0D5E7E, stop:1 #0C1428);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin-top: -2px;
                margin-bottom: -2px;
                border-radius: 3px;
            }
            
            QScrollBar:vertical {
                border: 1px solid #999999;
                background:white;
                width:10px; 
                margin: 0px 0px 0px 0px;
            }
            QScrollBar:horizontal {
                border: 1px solid #999999;
                background:white;
                height:10px; 
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0D5E7E, stop:1 #0C1428);
                min-height: 0px;
            }
            QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0D5E7E, stop:1 #0C1428);
                min-height: 0px;
            }
            QScrollBar::add-line:vertical, 
            QScrollBar::add-line:horizontal {
                background: none;
            }
            QScrollBar::sub-line:vertical, 
            QScrollBar::sub-line:horizontal {
                background: none;
            }
            QScrollBar::up-arrow:vertical, 
            QScrollBar::down-arrow:vertical, 
            QScrollBar::up-arrow:horizontal, 
            QScrollBar::down-arrow:horizontal {
                background: none;
            }
            QScrollBar::add-page:vertical, 
            QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, 
            QScrollBar::sub-page:horizontal {
                background: none;
            }
            
            QPlotWidget {
                min-height: 60px;
            }

            QListWidget {
                min-height: 150px;
            }
        """)
        
        # QWidget qui contiendra tous les autres widgets
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        
        # Layout principal pour centralWidget
        mainLayout = QVBoxLayout(centralWidget)
        mainLayout.addLayout(control_layout)

        # Image de l'album centrée
        self.albumArtLayout = QHBoxLayout()  # Layout pour centrer l'image de l'album
        self.albumArtLayout.addStretch()
        self.albumArtLabel = QLabel(self)
        pixmap = QPixmap(os.path.join(self.application_path, 'data', './Music bot.png'))  # Remplacez par le chemin de votre image
        self.albumArtLabel.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
        self.albumArtLayout.addWidget(self.albumArtLabel)
        self.albumArtLayout.addStretch()
        
        # Layout pour les informations sur la musique
        infoLayout = QVBoxLayout()  # Utiliser QVBoxLayout pour un retour à la ligne

        # Layout pour centrer le label de l'artiste
        self.artistLabelLayout = QHBoxLayout()
        self.artistLabelLayout.addStretch()  # Ajouter un stretch avant le label pour le centrer
        self.artistLabel = QLabel('Artiste : Pas de musique chargée', self)
        self.artistLabel.setAlignment(Qt.AlignCenter)  # Centrer le texte dans le label
        self.artistLabelLayout.addWidget(self.artistLabel)
        self.artistLabelLayout.addStretch()  # Ajouter un stretch après le label pour le centrer

        # Ajouter le QHBoxLayout de l'artiste au QVBoxLayout principal
        infoLayout.addLayout(self.artistLabelLayout)

        # Layout pour centrer le label de la musique
        self.songLabelLayout = QHBoxLayout()
        self.songLabelLayout.addStretch()  # Ajouter un stretch avant le label pour le centrer
        self.songLabel = QLabel('Musique : Pas de musique chargée', self)
        self.songLabel.setAlignment(Qt.AlignCenter)  # Centrer le texte dans le label
        self.songLabelLayout.addWidget(self.songLabel)
        self.songLabelLayout.addStretch()  # Ajouter un stretch après le label pour le centrer

        # Ajouter le QHBoxLayout de la musique au QVBoxLayout principal
        infoLayout.addLayout(self.songLabelLayout)

        # Utiliser pyqtgraph pour afficher la forme d'onde
        self.waveformPlot = pg.PlotWidget()
        self.waveformPlot.getAxis('left').setVisible(False)
        self.waveformPlot.getAxis('bottom').setVisible(False)
        self.set_gradient_background(self.waveformPlot)

        # Ajout du rect_item au PlotWidget
        self.playedWaveform = self.waveformPlot.plot(pen='b')  # Tracé pour la partie lue
        self.remainingWaveform = self.waveformPlot.plot(pen='g')
        
        # Labels pour le temps écoulé et le temps restant
        self.elapsedTimeLabel = QLabel('0:00', self)
        self.remainingTimeLabel = QLabel('-5:00', self)  # "-5:00" est un exemple pour 5 minutes

        # Slider pour la barre de progression
        self.progressBar = QSlider(Qt.Horizontal, self)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(self.total_duration)
        self.progressBar.setValue(self.current_position)
        self.progressBar.sliderReleased.connect(self.on_progressbar_released)
        
        # Slider pour le volume
        self.volumeSlider = QSlider(Qt.Horizontal, self)
        self.volumeSlider.setMinimum(0) 
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(75)  # Mettre la valeur initiale à 75% par exemple
        self.volumeSlider.valueChanged.connect(self.setVolume)
        
        self.volumeMinusLabel = QLabel(self)
        self.load_svg_in_label(self.volumeMinusLabel, os.path.join(self.application_path, 'data', 'volume-down.svg'))

        self.volumePlusLabel = QLabel(self)
        self.load_svg_in_label(self.volumePlusLabel, os.path.join(self.application_path, 'data', 'volume-up.svg'))
        
        # Layout pour le volume
        self.volumeLayout = QHBoxLayout()
        self.volumeLayout.addWidget(self.volumeMinusLabel)
        self.volumeLayout.addWidget(self.volumeSlider) 
        self.volumeLayout.addWidget(self.volumePlusLabel) 

        # Layout pour les labels et la barre de progression
        progressLayout = QHBoxLayout()
        progressLayout.addWidget(self.elapsedTimeLabel)
        progressLayout.addWidget(self.progressBar)
        progressLayout.addWidget(self.remainingTimeLabel)
        
        # Boutons de contrôle
        controlLayout = QHBoxLayout()
        btnPrevious = QPushButton(self)
        self.btnPlayPause = QPushButton('▶', self)  # Ce bouton va devenir Play/Pause
        self.btnPlayPause.clicked.connect(self.load_music_slot_connect)
        btnNext = QPushButton(self)
        btnPrevious.clicked.connect(self.on_btn_previous_clicked_slot_connect)
        btnNext.clicked.connect(self.on_btn_next_clicked_clicked_slot_connect)
        
        btnPrevious.setFont(QFont("Arial", 14))
        btnNext.setFont(QFont("Arial", 14))
        
        btnPrevious.setText('|◄◄')
        btnNext.setText('►►|')
        
        self.randomButton = QPushButton(self)
        self.randomButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'shuffle.svg')))
        self.randomButton.clicked.connect(self.on_random_clicked)

        self.repeatButton = QPushButton(self)
        self.repeatButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'refresh.svg')))
        self.repeatButton.clicked.connect(self.on_repeat_clicked)
        
        controlRandomRepeatLayout = QHBoxLayout()
        controlRandomRepeatLayout.addWidget(self.randomButton)
        controlRandomRepeatLayout.addWidget(self.repeatButton)
        
        
        self.listWidget = QListWidget(self)
        self.listWidget.itemClicked.connect(self.on_list_item_clicked)
        
        controlLayout.addWidget(btnPrevious)
        controlLayout.addWidget(self.btnPlayPause)
        controlLayout.addWidget(btnNext)
        
        controlAllLayout = QVBoxLayout()
        controlAllLayout.addLayout(controlLayout)
        controlAllLayout.addLayout(controlRandomRepeatLayout)
        
        self.apply_style_to_button(btnPrevious, True)
        self.apply_style_to_button(self.btnPlayPause, True)
        self.apply_style_to_button(btnNext, True)
        self.apply_style_to_button(self.randomButton, False)
        self.apply_style_to_button(self.repeatButton, False)
        
        # Créer les boutons de gestions de la playlist
        self.addButton = QPushButton()
        self.addButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'edit-add.svg')))
        self.apply_style_to_button(self.addButton, True)
        self.clearButton = QPushButton()
        self.clearButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'edit-clear.svg')))
        self.apply_style_to_button(self.clearButton, True)

        # Connecter les signaux aux slots correspondants
        self.addButton.clicked.connect(self.load_music_slot_connect)
        self.clearButton.clicked.connect(self.on_clear_clicked)

        # Ajouter les boutons à un layout
        playlistManagerLayout = QHBoxLayout()
        playlistManagerLayout.addWidget(self.addButton)
        playlistManagerLayout.addWidget(self.clearButton)
        
        # Ajouter les widgets au layout principal
        mainLayout.addWidget(self.movableWidget)
        mainLayout.addLayout(self.albumArtLayout)
        mainLayout.addLayout(infoLayout)
        mainLayout.addLayout(progressLayout)
        mainLayout.addLayout(self.volumeLayout)
        mainLayout.addLayout(controlAllLayout)
        mainLayout.addWidget(self.listWidget)
        mainLayout.addLayout(playlistManagerLayout)
        mainLayout.addWidget(self.waveformPlot)
        self.clearWaveform()
        
    # Méthode pour gérer le relâchement de la barre de progression
    def on_progressbar_released(self):
        # Obtenir la position du clic en pourcentage
        click_position = QCursor.pos()
        slider_length = self.progressBar.width()
        click_x = click_position.x() - self.progressBar.mapToGlobal(QPoint(0,0)).x()
        percentage = click_x / slider_length

        # Calculer la nouvelle position en secondes
        new_position_seconds = percentage * self.total_duration / 1000

        # Déplacer la lecture à la nouvelle position
        self.set_playback_position(new_position_seconds)

    # Méthode pour changer la position de lecture
    def set_playback_position(self, newPos):
        if self.filePath:
            self.is_playing = False
            print('newPos:', newPos)
            self.newPos = newPos
            self.current_position = self.newPos * 1000  # Convertir en millisecondes si nécessaire
            pygame.mixer.music.load(self.filePath)
            pygame.mixer.music.play(start=self.newPos)
            self.is_playing = True
            self.update_progress_bar_and_waveform()

    def update_progress_bar_and_waveform(self):
        self.progressBar.setValue(int(self.current_position))
        
        if self.samples is not None:
            progress = self.current_position / self.total_duration
            index = int(len(self.samples) * progress)
            played_samples = self.samples[:index]
            self.playedWaveform.setData(played_samples)
    
    def clearWaveform(self):
        emptyData = np.array([])
        self.playedWaveform.setData(emptyData)
        self.remainingWaveform.setData(emptyData)
        
    def on_clear_clicked(self):
        self.current_track_index = -1
        self.track_list.clear()
        self.track_paths.clear()
        self.listWidget.clear()
        self.is_playing = False
        pygame.mixer.music.stop()
        self.btnPlayPause.setText('▶')
        self.samples = None
        self.artistLabel.setText(f'Artiste : Pas de musique chargée')
        self.songLabel.setText(f'Musique : Pas de musique chargée')
        pixmap = QPixmap(os.path.join(self.application_path, 'data', './Music bot.png'))  # Remplacez par le chemin de votre image
        self.albumArtLabel.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
        self.clearWaveform()
        self.btnPlayPause.disconnect()
        self.btnPlayPause.clicked.connect(self.load_music_slot_connect)
        self.waveformPlot.getAxis('left').setVisible(False)
        self.waveformPlot.getAxis('bottom').setVisible(False)
        if is_discord_running():
            try:
                asyncio.create_task(self.play_track_async("", "", ""))
                print("Réussite de la remise à zéro du RPC Discord")
            except Exception as e:
                print(f"Erreur lors de la tentative de retirer les infos de la connexion RPC : {e}")
        
    def apply_style_to_button(self, button, activate):
        if isinstance(button, QPushButton) and activate:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #0D5E7E;
                    border-style: outset;
                    border-width: 2px;
                    border-radius: 10px;
                    border-color: #0C1428;
                    font: bold 14px;
                    min-width: 1em;
                    padding: 6px;
                    icon-size: 20px;
                }
                QPushButton::hover {
                    background-color: #0D7EAA;
                }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #7E7E7E;
                    border-style: outset;
                    border-width: 2px;
                    border-radius: 10px;
                    border-color: #0C1428;
                    font: bold 14px;
                    min-width: 1em;
                    padding: 6px;
                    icon-size: 20px;
                }
                QPushButton::hover {
                    background-color: #AAAAAA;
                }
            """)
        
    def setMaskForRoundedCorners(self):
        # Set a mask for rounded corners
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 15, 15)  # 15 is the radius for rounded corners
        mask = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(mask)

    def paintEvent(self, event):
        # Override the paint event to draw the background with rounded corners
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # For smooth edges
    
        # Create the linear gradient
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#0C1428"))
        gradient.setColorAt(1, QColor("#0D5E7E"))

        # Set the gradient as the brush
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)  # No border
        painter.drawRoundedRect(self.rect(), 15, 15)

    def set_gradient_background(self, plot_widget):
        gradient = QLinearGradient(0, 0, plot_widget.width(), 0)
        gradient.setColorAt(0, QColor("#0C1428"))
        gradient.setColorAt(1, QColor("#218EB8"))

        brush = QBrush(gradient)
        plot_widget.setBackground(brush)
        
    def toggleMaximizeRestore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def get_metadata(self, file_path):
        ext = os.path.splitext(file_path)[-1].lower()
        metadata = {}

        if ext == '.mp3':
            audio = EasyID3(file_path)
        elif ext == '.flac':
            audio = FLAC(file_path)
        elif ext == '.ogg':
            audio = OggVorbis(file_path)
        elif ext == '.wav':
            audio = WAVE(file_path)
        else:
            return None  # Format non supporté ou inconnu
        
        # Obtenez le nom de base du fichier sans l'extension
        base_name = os.path.basename(file_path)
        file_title = os.path.splitext(base_name)[0]

        # Assurez-vous de récupérer la chaîne complète si la valeur est une liste
        metadata['artist'] = ' '.join(audio.get('artist', ['Unknown Artist']))
        metadata['title'] = ' '.join(audio.get('title', [file_title]))
        metadata['album'] = ' '.join(audio.get('album', ['Unknown Album']))
        metadata['tracknumber'] = ' '.join(audio.get('tracknumber', ['0'])).split('/')[0]

        return metadata

    def load_music(self):
        try:
            # Ouvrir le QFileDialog pour sélectionner la musique
            default_music_folder = QStandardPaths.writableLocation(QStandardPaths.MusicLocation)
            if platform.system() == 'Linux':
                folder_path = QFileDialog.getExistingDirectory(None, "Select Folder", default_music_folder, QFileDialog.DontUseNativeDialog)
            else:
                folder_path = QFileDialog.getExistingDirectory(None, "Select Folder", default_music_folder)
            if not folder_path:
                return
            print("Chemins des pistes chargées :", folder_path)
            if is_discord_running():
                if self.RPC is None:
                    self.RPC.connect()
            if not self.track_list:
                first = True
            else:
                first = False
            temp_track_list = []
            temp_track_paths = []
            temp_ordered_playlist = {}
            for file in os.listdir(folder_path):
                if file.endswith((".mp3", ".wav", ".flac", ".ogg")):
                    self.filePath = os.path.join(folder_path, file)
                    try:
                        metadata = self.get_metadata(self.filePath)
                        if metadata:
                            temp_track_list.append((int(metadata['tracknumber']), metadata['artist'], metadata['title'], self.filePath))
                            temp_track_paths.append(self.filePath)
                            album_name = metadata['album']
                            if album_name not in temp_ordered_playlist:
                                temp_ordered_playlist[album_name] = []
                            temp_ordered_playlist[album_name].append((int(metadata['tracknumber']), metadata['artist'], metadata['title'], self.filePath)) 
                    except Exception as e:
                        print(f"Erreur avec le fichier {self.filePath}: {e}") 
            self.track_list.extend(temp_track_list)
            self.track_paths.extend(temp_track_paths)
            for album in temp_ordered_playlist:
                if album not in self.orderedPlaylist:
                    self.orderedPlaylist[album] = []
                self.orderedPlaylist[album].extend(temp_ordered_playlist[album])
            self.random_order()
            # Jouer la première piste si nécessaire
            if self.track_paths and not self.is_playing:
                print("Tentative de jouer : ", self.track_paths[0])
                self.play_track(0)
            
            # Mettre à jour le bouton pour qu'il fonctionne maintenant comme Play/Pause
            self.btnPlayPause.disconnect()
            self.btnPlayPause.clicked.connect(self.toggle_play_pause)
            if first:
                self.toggle_play_pause()
        except Exception as e:
            print(f"Erreur lors du chargement de la musique : {e}")
        
    def on_random_clicked(self):
        self.is_random = not self.is_random

        if self.is_random:
            self.random_order()
            self.apply_style_to_button(self.randomButton, True)
        else:
            self.restore_original_order()
            self.apply_style_to_button(self.randomButton, False)

        # Mettre à jour self.current_track_index avec la nouvelle position de la chanson actuelle
        if self.filePath:
            try:
                self.current_track_index = self.track_paths.index(self.filePath)
            except ValueError:
                print("Chanson actuelle non trouvée dans la liste de pistes.")
                self.current_track_index = 0
    
    def random_order(self):
        if self.is_random:
            combined_list = list(zip(self.track_list, self.track_paths))
            random.shuffle(combined_list)
            self.track_list, self.track_paths = map(list, zip(*combined_list))
        self.update_list_widget()

    def restore_original_order(self):
        self.track_paths = []
        self.listWidget.clear()
        for album in self.orderedPlaylist:
            for track in self.orderedPlaylist[album]:
                track_num, artist, title, filepath = track
                self.listWidget.addItem(f"{track_num}. {artist} - {title}")
                self.track_paths.append(filepath)

    def update_list_widget(self):
        self.listWidget.clear()
        self.track_paths.clear()
        for track in self.track_list:
            self.listWidget.addItem(f"{track[0]}. {track[1]} - {track[2]}")
            self.track_paths.append(track[3])
            
    def toggle_play_pause(self):
        # Vérifiez d'abord si pygame.mixer est initialisé
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        # Ensuite, vérifiez si la musique a été chargée
        if not self.filePath:
            # Vous pouvez ajouter ici un message pour l'utilisateur ou ouvrir le dialogue pour charger un fichier
            return
        self.addWaveformToLayout()
        if self.is_playing:
            pygame.mixer.music.pause()
            self.btnPlayPause.setText('▶')  # Change le texte à "Play"
            self.is_playing = False
        else:
            if pygame.mixer.music.get_pos() == -1:  # Si la musique n'a jamais été jouée ou a fini
                self.current_position = 0
                self.newPos = 0
                pygame.mixer.music.play()
            else:
                pygame.mixer.music.unpause()  # Si la musique a été mise en pause, la reprendre
            self.btnPlayPause.setText('❚❚')  # Change le texte à "Pause"
            self.is_playing = True
            
    def on_list_item_clicked(self, item):
        self.initiate_manual_track_change()
        index = self.listWidget.row(item)
        self.play_track(index)
        
    def play_previous_track(self):
        if self.current_track_index > 0:
            self.current_track_index -= 1
            self.play_track(0)

    def play_next_track(self):
        if self.repeat_state == 0:
            # Si on est à la fin de la playlist, arrêter ou recommencer depuis le début
            if self.current_track_index < len(self.track_paths) - 1:
                self.current_track_index += 1
            else:
                self.current_track_index = 0  # Optionnel : recommencer la playlist
                self.reinit_play(self.current_track_index)
                return  # Arrêter la lecture si vous ne souhaitez pas recommencer automatiquement

        elif self.repeat_state == 1:
            # Répéter la playlist entière
            self.current_track_index = (self.current_track_index + 1) % len(self.track_paths)

        elif self.repeat_state == 2:
            # Répéter le morceau actuel, donc ne pas changer l'index
            pass

        self.play_track(self.current_track_index)
        self.newPos = 0
        pygame.mixer.music.play()
        
    def reinit_play(self, index):
        if index >= len(self.track_paths) or index < 0:
            return
        # Choisir la chanson portant l'index demandé
        self.current_track_index = index
        # Récupérer le chemin d'accès de la chanson choisie
        self.filePath = self.track_paths[self.current_track_index]
        # Précharger la chanson choisie au cas où l'utilisateur décide de relancer la lecture
        pygame.mixer.music.load(self.filePath)

        try:
            # Lire les métadonnées du fichier MP3
            audio = EasyID3(self.filePath)
            artist = audio.get('artist', ['Unknown Artist'])[0]
            title = audio.get('title', ['Unknown Title'])[0]
            # Mettre à jour l'interface graphique avec les métadonnées
            self.artistLabel.setText(f'Artiste : {artist}')
            self.songLabel.setText(f'Musique : {title}')
        except Exception as e:
            print(f"Erreur lors de la lecture des métadonnées: {e}")
            # Mettre à jour l'interface graphique avec des valeurs par défaut
            self.artistLabel.setText('Artiste : Inconnu')
            self.songLabel.setText('Musique : Inconnue')

        # Remettre le lecteur à zéro
        pygame.mixer.music.stop()
        self.btnPlayPause.setText('▶')

        # Mettre à jour la forme d'onde par rapport à la musique choisie
        self.loadWaveform()

    def on_btn_previous_clicked(self):
        self.initiate_manual_track_change()
        if pygame.mixer.music.get_pos() > 3000:  # Si plus de 3 secondes de la chanson ont joué
            self.current_position = 0
            self.newPos = 0
            pygame.mixer.music.play()  # Rejouer la chanson actuelle depuis le début
        else:
            self.play_previous_track()  # Sinon, passer à la chanson précédente

    def on_btn_next_clicked(self):
        self.initiate_manual_track_change()
        self.play_next_track()
        
    def initiate_manual_track_change(self):
        if self.is_playing:
            pygame.mixer.music.stop()  # Arrête la piste actuelle
            self.is_playing = False
        self.is_manual_track_change = True
        QTimer.singleShot(3000, self.reset_manual_track_change)  # Remet le flag à False après 3 secondes

    def reset_manual_track_change(self):
        self.newPos = 0
        pygame.mixer.music.play()
        self.is_manual_track_change = False

    async def play_track_async(self, cover_path, title, artist):
        await self.envoyer_image(cover_path, title, artist)

    def find_images(self, directory):
        image_extensions = ['.jpg', '.jpeg', '.png']
        image_files = []

        # Parcourir les fichiers dans le répertoire
        for file in os.listdir(directory):
            # Obtenez le nom du fichier et son extension
            _, extension = os.path.splitext(file)

            # Vérifiez si l'extension du fichier est parmi celles recherchées
            if extension.lower() in image_extensions:
                # Ajoutez le chemin complet du fichier à la liste
                image_files.append(os.path.join(directory, file))

        return image_files

    def play_track(self, index):
        if 0 <= index < len(self.track_paths):
            self.filePath = self.track_paths[index]
            ext = os.path.splitext(self.filePath)[-1].lower()
            
            if ext in ['.flac', '.mp3', '.ogg']:
                # Convertir le fichier en WAV pour la lecture
                format_map = {'.flac': 'flac', '.mp3': 'mp3', '.ogg': 'ogg'}
                audio_format = format_map.get(ext, 'mp3')  # Par défaut à 'mp3' si le format n'est pas trouvé
                audio = AudioSegment.from_file(self.filePath, format=audio_format)
                temp_file = tempfile.NamedTemporaryFile(delete=True, suffix='.wav')  # Nom de fichier temporaire
                audio.export(temp_file, format='wav')
                self.filePath = temp_file
            
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.stop()
            self.filePath = self.track_paths[index]
            pygame.mixer.music.load(self.filePath)
            self.total_duration = int(self.get_audio_length(self.filePath) * 1000)
            self.progressBar.setMaximum(self.total_duration)
            self.loadWaveform()
            
            self.current_track_index = index
                    
            # Lire les métadonnées du fichier Audio
            audio = self.get_metadata(self.filePath)
            artist = audio.get('artist', ['Unknown Artist'])  # Remplacer par 'Unknown Artist' si non disponible
            title = audio.get('title', ['Unknown Title']) # Remplacer par 'Unknown Title' si non disponible

            # Mettre à jour l'interface graphique avec les métadonnées
            self.artistLabel.setText(f'Artiste : {artist}')
            self.songLabel.setText(f'Musique : {title}')
            
            # Charger la pochette s'il y en a une dans le même dossier
            music_dir = os.path.dirname(self.filePath)
            
            image_files = self.find_images(music_dir)
                        
            if image_files:
                # Prendre la première image trouvée
                cover_path = image_files[0]
            else:
                cover_path = os.path.join(self.application_path, 'data', 'Music bot.png')
            cover_path = self.resize_cover(cover_path)
            pixmap = QPixmap(cover_path)
            if cover_path:
                self.albumArtLabel.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
            else:
                print("Aucune image de pochette trouvée.")
            self.total_duration = int(self.get_audio_length(self.filePath) * 1000)  # Durée totale en millisecondes
            if is_discord_running():
                asyncio.create_task(self.play_track_async(cover_path, title, artist))
        
    def on_repeat_clicked(self):
        if self.repeat_state < 2:
            self.repeat_state += 1
        else:
            self.repeat_state = 0
        if self.repeat_state == 2:
            self.repeatButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'refresh-1.svg')))
        else:
            self.repeatButton.setIcon(QIcon(os.path.join(self.application_path, 'data', 'refresh.svg')))
        if self.repeat_state == 1 or self.repeat_state == 2:
            self.apply_style_to_button(self.repeatButton, True)
        else:
            self.apply_style_to_button(self.repeatButton, False)
            
            
    def setVolume(self, value):
        if pygame.mixer.get_init() is not None:
            pygame.mixer.music.set_volume(value / 100)
            if value == 0:
                self.load_svg_in_label(self.volumeMinusLabel, os.path.join(self.application_path, 'data', 'volume-mute.svg'))
            else:
                self.load_svg_in_label(self.volumeMinusLabel, os.path.join(self.application_path, 'data', 'volume-down.svg'))
            if value == 100:
                self.load_svg_in_label(self.volumePlusLabel, os.path.join(self.application_path, 'data', 'volume-notice.svg'))
            else:
                self.load_svg_in_label(self.volumePlusLabel, os.path.join(self.application_path, 'data', 'volume-up.svg'))
            
            
    def addWaveformToLayout(self):
        # Ajouter la forme d'onde au layout principal
        centralWidget = self.centralWidget()
        mainLayout = centralWidget.layout()
        mainLayout.addWidget(self.waveformPlot)

        # Charger et afficher la forme d'onde
        self.loadWaveform()
        
    def update_progress(self):
        if pygame.mixer.get_init() is not None:  # Vérifiez si le mixer est initialisé
            self.current_position = int(self.newPos * 1000) + pygame.mixer.music.get_pos()

            if self.current_position == -1 and self.newPos == 0.0:  # Si la musique n'est pas en cours de lecture
                self.current_position = 0
                self.elapsedTimeLabel.setText('0:00')
                self.remainingTimeLabel.setText(f'-{self.total_duration // 60000}:{(self.total_duration % 60000) // 1000:02}')
            else:
                # Mettre à jour la barre de progression
                self.progressBar.setValue(self.current_position)

                # Calculer et afficher le temps écoulé
                elapsed_minutes = self.current_position // 60000
                elapsed_seconds = (self.current_position % 60000) // 1000
                self.elapsedTimeLabel.setText(f'{elapsed_minutes}:{elapsed_seconds:02}')

                # Calculer et afficher le temps restant
                remaining_time = self.total_duration - self.current_position
                remaining_minutes = abs(remaining_time) // 60000
                remaining_seconds = (abs(remaining_time) % 60000) // 1000
                self.remainingTimeLabel.setText(f'-{remaining_minutes}:{remaining_seconds:02}')
            
            if self.samples is not None:  # Assurez-vous que samples est défini
                progress = self.current_position / self.total_duration
                index = int(len(self.samples) * progress)
                # Mettre à jour le tracé de la partie lue
                played_samples = self.samples[:index]
                self.playedWaveform.setData(played_samples)
            
    def loadWaveform(self):
        self.waveformWorker = WaveformWorker(self.filePath)
        self.waveformWorker.waveformReady.connect(self.updateWaveform)
        self.waveformWorker.start()

    def updateWaveform(self, samples):
        # Cette fonction est appelée une fois que les échantillons sont chargés
        self.samples = samples
        self.waveformPlot.clear()  # Nettoyez le tracé précédent

        # Tracé pour la partie restante (statique, couleur verte)
        self.remainingWaveform = self.waveformPlot.plot(self.samples, pen=pg.mkPen('g', width=2))
        
        # Tracé pour la partie lue (dynamique, couleur bleue)
        # Initialement vide, sera mis à jour avec update_progress
        self.playedWaveform = self.waveformPlot.plot(pen=pg.mkPen('b', width=2))

        self.waveformPlot.getAxis('left').setVisible(False)
        self.waveformPlot.getAxis('bottom').setVisible(False)
        
    def load_music_slot_connect(self):
        # QTimer.singleShot(0, lambda: asyncio.ensure_future(self.load_music()))        
        self.load_music()        
        
    def on_btn_previous_clicked_slot_connect(self):
        # QTimer.singleShot(0, lambda: asyncio.ensure_future(self.on_btn_previous_clicked()))   
        self.on_btn_previous_clicked()    
        
    def on_btn_next_clicked_clicked_slot_connect(self):
        # QTimer.singleShot(0, lambda: asyncio.ensure_future(self.on_btn_next_clicked()))
        self.on_btn_next_clicked()        
        
    def closeEvent(self, event):
        if self.waveformWorker and self.waveformWorker.isRunning():
            self.waveformWorker.stop()  # Arrêtez le thread
            self.waveformWorker.quit() 
            self.waveformWorker.wait()   # Attendez la fin du thread
        super().closeEvent(event)
        
def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    player = MusicPlayer()
    player.show()

    with loop:
        loop.run_forever()

if __name__ == '__main__':
    main()
