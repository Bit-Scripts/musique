import sys
import os
import time
import numpy as np
from pydub import AudioSegment
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QSlider, QHBoxLayout, QFileDialog, QListWidget, QGraphicsRectItem
from PyQt5.QtGui import QPixmap, QIcon, QLinearGradient, QBrush, QColor, QRegion, QPainter, QPainterPath, QFont
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, Qt, QSize
import pygame
import pyqtgraph as pg
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import glob

class WaveformWorker(QThread):
    waveformReady = pyqtSignal(np.ndarray)

    def __init__(self, audio_file):
        super().__init__()
        self.audio_file = audio_file

    def run(self):
        audio = AudioSegment.from_file(self.audio_file)
        # Réduisez la résolution des échantillons ici si nécessaire
        samples = np.array(audio.get_array_of_samples())[::1000]  # Par exemple, prenez un échantillon toutes les 1000 valeurs
        self.waveformReady.emit(samples)

class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.filePath = '' #'/home/paul/Musique/Tomawok - 8 millions d\'indiens.mp3'
        
        self.samples = None
        
        self.is_playing = False

        # Obtenez la durée totale de la piste ici et convertissez-la en millisecondes
        self.total_duration = 0 #int(self.get_audio_length(self.filePath) * 1000)  # Durée totale en millisecondes

        self.current_position = 0  # Position actuelle en millisecondes

        # Initialisez le timer après l'interface utilisateur
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(1000) 
        
        self.is_playing = False
        
        self.track_paths = []  # Liste pour stocker les chemins des fichiers
        self.current_track_index = 0 
        
        icon_path = './Music bot.png'  # Chemin vers votre icône
        self.setWindowIcon(QIcon(icon_path))

        # Initialisation de l'interface utilisateur après avoir défini total_duration
        self.initUI()
        pygame.init()
        pygame.display.set_mode((1, 1)) 
        pygame.mixer.music.set_endevent(pygame.USEREVENT)
        self.end_event = pygame.USEREVENT
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == self.end_event:
                self.play_next_track()
        
    def get_audio_length(self, file_path):
        audio = MP3(file_path)
        audio_length = audio.info.length  # durée en secondes
        return audio_length

    def initUI(self):
        # self.setFixedSize(400, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove the title bar
        self.setAttribute(Qt.WA_TranslucentBackground) 
        
        self.minimizeButton = QPushButton("_", self)
        self.maximizeButton = QPushButton("[ ]", self)
        self.closeButton = QPushButton("x", self)

        self.minimizeButton.setFixedSize(QSize(35, 35))
        self.maximizeButton.setFixedSize(QSize(35, 35))
        self.closeButton.setFixedSize(QSize(35, 35))

        self.minimizeButton.clicked.connect(self.showMinimized)
        self.maximizeButton.clicked.connect(self.toggleMaximizeRestore)
        self.closeButton.clicked.connect(self.close)
        
        # Layout pour les boutons de contrôle
        control_layout = QHBoxLayout()
        control_layout.addStretch()
        control_layout.addWidget(self.minimizeButton)
        control_layout.addWidget(self.maximizeButton)
        control_layout.addWidget(self.closeButton)

        # Fenêtre principale
        self.setWindowTitle('BIT SCRIPTS - Musique')
        self.setGeometry(100, 100, 400, 300)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0C1428, stop:1 #0D5E7E);
                border-radius: 10px;
            }

            QLabel, QPushButton {
                color: #FFF;
            }

            QPushButton {
                background-color: #0D5E7E;
                border-style: outset;
                border-width: 2px;
                border-radius: 10px;
                border-color: #0C1428;
                font: bold 14px;
                min-width: 1em;
                padding: 6px;
            }
            QPushButton::hover {
                background-color: #0D7EAA;
            }
            QListWidget {
                background-color: rgba(0,0,0,0);
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
        pixmap = QPixmap('./Music bot.png')  # Remplacez par le chemin de votre image
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
        
        # Slider pour le volume
        self.volumeSlider = QSlider(Qt.Horizontal, self)
        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(75)  # Mettre la valeur initiale à 75% par exemple
        self.volumeSlider.valueChanged.connect(self.setVolume)
        
        self.volumeLabel = QLabel('Volume', self)
        
        # Layout pour le volume
        self.volumeLayout = QHBoxLayout()
        self.volumeLayout.addWidget(self.volumeLabel)
        self.volumeLayout.addWidget(self.volumeSlider) 

        # Layout pour les labels et la barre de progression
        progressLayout = QHBoxLayout()
        progressLayout.addWidget(self.elapsedTimeLabel)
        progressLayout.addWidget(self.progressBar)
        progressLayout.addWidget(self.remainingTimeLabel)
        
        # Boutons de contrôle
        controlLayout = QHBoxLayout()
        btnPrevious = QPushButton(self)
        self.btnPlayPause = QPushButton('▶', self)  # Ce bouton va devenir Play/Pause
        self.btnPlayPause.clicked.connect(self.load_music)
        btnNext = QPushButton(self)
        btnPrevious.clicked.connect(self.on_btn_previous_clicked)
        btnNext.clicked.connect(self.on_btn_next_clicked)
        
        btnPrevious.setFont(QFont("Arial", 14))
        btnNext.setFont(QFont("Arial", 14))
        
        btnPrevious.setText('|◄◄')
        btnNext.setText('►►|')
        
        self.listWidget = QListWidget(self)
        self.listWidget.itemClicked.connect(self.on_list_item_clicked)
        
        controlLayout.addWidget(btnPrevious)
        controlLayout.addWidget(self.btnPlayPause)
        controlLayout.addWidget(btnNext)
        
        # Ajouter les widgets au layout principal
        mainLayout.addLayout(self.albumArtLayout)
        mainLayout.addLayout(infoLayout)
        # mainLayout.addWidget(self.waveformPlot)
        mainLayout.addLayout(progressLayout)
        mainLayout.addLayout(self.volumeLayout)
        mainLayout.addLayout(controlLayout)
        mainLayout.addWidget(self.listWidget)
        
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

    def load_music(self):
        if not self.is_playing and self.samples is None:
            # Ouvrir le QFileDialog pour sélectionner la musique
            folder_path = QFileDialog.getExistingDirectory(None, "Select Folder")
            track_list = []
            for file in os.listdir(folder_path):
                if file.endswith(".mp3"):
                    filepath = os.path.join(folder_path, file)
                    try:
                        audio = EasyID3(filepath)
                        track_num = audio.get('tracknumber', ['0'])[0].split('/')[0]
                        artist = audio.get('artist', ['Unknown Artist'])[0]
                        title = audio.get('title', [file])[0]
                        track_list.append((int(track_num), artist, title, file))
                    except Exception as e:
                        print(f"Erreur avec le fichier {filepath}: {e}")
                        track_list.append((0, 'Unknown Artist', file, file))
            track_list.sort()  # Trier par numéro de piste
            self.track_paths = []
            for track in track_list:
                track_info = f"{track[0]}. {track[1]} - {track[2]}"
                self.listWidget.addItem(track_info)
                # self.track_paths.append(filepath)
                self.track_paths.append(os.path.join(folder_path, track[3]))
            self.play_track(0)
        
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
                pygame.mixer.music.play()
            else:
                pygame.mixer.music.unpause()  # Si la musique a été mise en pause, la reprendre
            self.btnPlayPause.setText('❚❚')  # Change le texte à "Pause"
            self.is_playing = True
            
    def on_list_item_clicked(self, item):
        index = self.listWidget.row(item)
        self.play_track(index)
        
    def play_previous_track(self):
        if self.current_track_index > 0:
            self.current_track_index -= 1
            self.play_track(self.current_track_index)

    def play_next_track(self):
        if self.current_track_index < len(self.track_paths) - 1:
            self.current_track_index += 1
            self.play_track(self.current_track_index)
            pygame.mixer.music.play()

    def on_btn_previous_clicked(self):
        if pygame.mixer.music.get_pos() > 3000:  # Si plus de 3 secondes de la chanson ont joué
            pygame.mixer.music.play()  # Rejouer la chanson actuelle depuis le début
        else:
            self.play_previous_track()  # Sinon, passer à la chanson précédente

    def on_btn_next_clicked(self):
        self.play_next_track()

    def play_track(self, index):
        if 0 <= index < len(self.track_paths):
            
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.stop()
            self.filePath = self.track_paths[index]
            pygame.mixer.music.load(self.filePath)
            self.total_duration = int(self.get_audio_length(self.filePath) * 1000)
            self.progressBar.setMaximum(self.total_duration)
            self.loadWaveform()
            
            self.current_track_index = index
                    
            # Lire les métadonnées du fichier MP3
            audio = EasyID3(self.filePath)
            artist = audio.get('artist', ['Unknown Artist'])[0]  # Remplacer par 'Unknown Artist' si non disponible
            title = audio.get('title', ['Unknown Title'])[0]  # Remplacer par 'Unknown Title' si non disponible

            # Mettre à jour l'interface graphique avec les métadonnées
            self.artistLabel.setText(f'Artiste : {artist}')
            self.songLabel.setText(f'Musique : {title}')
            
            # Charger la pochette s'il y en a une dans le même dossier
            music_dir = os.path.dirname(self.filePath)
            image_files = glob.glob(os.path.join(music_dir, '*.jpg')) + \
                        glob.glob(os.path.join(music_dir, '*.jpeg')) + \
                        glob.glob(os.path.join(music_dir, '*.png'))

            if image_files:
                # Prendre la première image trouvée
                cover_path = image_files[0]
                pixmap = QPixmap(cover_path)
                if pixmap.isNull():
                    print("Échec du chargement de l'image de la pochette.")
                else:
                    self.albumArtLabel.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
            else:
                print("Aucune image de pochette trouvée.")
            
            self.total_duration = int(self.get_audio_length(self.filePath) * 1000)  # Durée totale en millisecondes
            
            # Mettre à jour le bouton pour qu'il fonctionne maintenant comme Play/Pause
            self.btnPlayPause.disconnect()
            self.btnPlayPause.clicked.connect(self.toggle_play_pause)
            self.toggle_play_pause()
        # if not pygame.mixer.get_init():
        #     pygame.mixer.init()
        # pygame.mixer.music.play()
        # self.btnPlayPause.setText('❚❚')  # Change le texte à "Pause" quand la musique commence
        # self.is_playing = True
        # self.start_time = time.time()
            
    def setVolume(self, value):
        if pygame.mixer.get_init() is not None:
            pygame.mixer.music.set_volume(value / 100)
            
    def addWaveformToLayout(self):
        # Ajouter la forme d'onde au layout principal
        centralWidget = self.centralWidget()
        mainLayout = centralWidget.layout()
        mainLayout.addWidget(self.waveformPlot)

        # Charger et afficher la forme d'onde
        self.loadWaveform()
        
    def update_progress(self):
        if pygame.mixer.get_init() is not None:  # Vérifiez si le mixer est initialisé
            self.current_position = pygame.mixer.music.get_pos()

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
        self.check_track_end()
        self.handle_events()
        
    def check_track_end(self):
        if self.current_position >= self.total_duration:
            self.play_next_track()
            
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

        
def main():
    app = QApplication(sys.argv)
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
