import os
import tempfile
from PIL import Image
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
from mutagen.easyid3 import EasyID3
import wave

class MetadataExtractor:
    """Classe utilitaire pour l'extraction de tags musicaux et la gestion des pochettes."""

    @staticmethod
    def get_audio_length(file_path):
        """Retourne la durée d'un fichier audio en secondes."""
        ext = os.path.splitext(file_path)[-1].lower()
        try:
            if ext == '.mp3':
                from mutagen.mp3 import MP3
                audio = MP3(file_path)
                return audio.info.length
            elif ext == '.flac':
                audio = FLAC(file_path)
                return audio.info.length
            elif ext == '.ogg':
                audio = OggVorbis(file_path)
                return audio.info.length
            elif ext == '.wav':
                with wave.open(file_path, 'r') as audio:
                    frames = audio.getnframes()
                    rate = audio.getframerate()
                    return frames / float(rate)
        except Exception as e:
            print(f"Erreur lors de la lecture de la durée pour {file_path}: {e}")
        return 0

    @staticmethod
    def get_metadata(file_path):
        """Extrait les tags du fichier audio : artiste, titre, album, numéro de piste."""
        ext = os.path.splitext(file_path)[-1].lower()
        metadata = {}

        try:
            if ext == '.mp3':
                audio = EasyID3(file_path)
            elif ext == '.flac':
                audio = FLAC(file_path)
            elif ext == '.ogg':
                audio = OggVorbis(file_path)
            elif ext == '.wav':
                audio = WAVE(file_path)
            else:
                return None  # Format non supporté

            base_name = os.path.basename(file_path)
            file_title = os.path.splitext(base_name)[0]

            metadata['artist'] = ' '.join(audio.get('artist', ['Unknown Artist']))
            metadata['title'] = ' '.join(audio.get('title', [file_title]))
            metadata['album'] = ' '.join(audio.get('album', ['Unknown Album']))
            metadata['tracknumber'] = ' '.join(audio.get('tracknumber', ['0'])).split('/')[0]
            
            # Gérer les champs vides 
            if not metadata['title'].strip(): metadata['title'] = file_title
            
            return metadata
            
        except Exception as e:
            print(f"Erreur métadonnées sur {file_path}: {e}")
            return None

    @staticmethod
    def get_best_cover(filepath):
        """Tente d'extraire la pochette intégrée au fichier, sinon fallback intelligent."""
        ext = os.path.splitext(filepath)[-1].lower()
        try:
            if ext == '.mp3':
                from mutagen.id3 import ID3, APIC
                try:
                    audio = ID3(filepath)
                    for tag in audio.values():
                        if isinstance(tag, APIC):
                            tf = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                            tf.write(tag.data)
                            tf.close()
                            return tf.name
                except: pass
            elif ext == '.flac':
                from mutagen.flac import FLAC
                audio = FLAC(filepath)
                if audio.pictures:
                    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    tf.write(audio.pictures[0].data)
                    tf.close()
                    return tf.name
        except Exception as e:
            print(f"Erreur d'extraction pochette MP3/FLAC : {e}")

        # Recherche de fallback propre (cover.jpg, etc.)
        directory = os.path.dirname(filepath)
        if not os.path.isdir(directory):
            return None
            
        preferred_names = ['cover.jpg', 'folder.jpg', 'front.jpg', 'cover.png', 'folder.png']
        files = os.listdir(directory)
        
        for pref in preferred_names:
            for f in files:
                if f.lower() == pref:
                    return os.path.join(directory, f)
                    
        # Sinon, la première image venue...
        for f in files:
            e = os.path.splitext(f)[-1].lower()
            if e in ['.jpg', '.jpeg', '.png']:
                return os.path.join(directory, f)
                
        return None

    @staticmethod
    def resize_cover_for_cache(cover_path, size=(512, 512)):
        """Redimensionne une image de pochette pour optimiser la mémoire et l'upload Discord."""
        if not cover_path or not os.path.exists(cover_path):
            return ""
            
        try:
            with Image.open(cover_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                img.save(temp_file.name, 'JPEG', quality=95)
            return temp_file.name
        except Exception as e:
            print(f"Erreur lors du redimensionnement de l'image {cover_path} : {e}")
            return cover_path # Retour original en cas d'échec
