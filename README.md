# BIT-SCRIPTS<br/>Musique

Petit lecteur de musique écrit en Python et sans prétention.

![Design du lecteur](Apercu.png)

## Fonctionnalités
- Lecture de fichiers audio au format MP3.
- Contrôle simple avec des boutons pour jouer/pauser, passer à la chanson suivante ou revenir à la précédente.
- Affichage de la forme d'onde de la chanson en cours.
- Barre de progression indiquant le temps écoulé de la chanson.
- Fonctionnalité de volume réglable.
- Interface utilisateur personnalisée avec des boutons de contrôle de la fenêtre (minimiser, maximiser, fermer).
## Prérequis
Pour exécuter ce lecteur de musique, assurez-vous d'avoir installé les éléments suivants :

### Pour tous les systèmes :
- Python 3.x
- PyQt5
- Pygame
- PyDub
- Mutagen
- Pyqtgraph

### Pour Windows :
- FFmpeg :
  - Vous pouvez installer FFmpeg via l'un des gestionnaires de paquets en ligne de commande suivants :
    - Chocolatey :
      ```
      choco install ffmpeg
      ```
    - Winget (Essentials Build) :
      ```
      winget install "FFmpeg (Essentials Build)"
      ```
    - Winget (Full Build) :
      ```
      winget install ffmpeg
      ```
    - Scoop (Full Build) :
      ```
      scoop install ffmpeg
      ```
    - Scoop (Shared Build) :
      ```
      scoop install ffmpeg-shared
      ```
    - Pour les builds de développement (Git Master) :
      ```
      scoop install ffmpeg-gyan-nightly
      ```
  - Alternativement, vous pouvez télécharger FFmpeg manuellement depuis [le site officiel](https://ffmpeg.org/download.html), l'extraire et ajouter le dossier `bin` à la variable d'environnement `Path`.
  - Vérifiez l'installation avec `ffmpeg -version`.

### Pour Linux :
- FFmpeg :
  - Installez FFmpeg en utilisant le gestionnaire de paquets de votre distribution.
    Par exemple, sur Ubuntu/Debian, utilisez :
    ```bash
    sudo apt-get install ffmpeg
    ```
  - Vérifiez l'installation avec `ffmpeg -version`.
## Installation
1. Clonez ce dépôt ou téléchargez-le en tant qu'archive ZIP.
2. Installez les dépendances nécessaires en exécutant `pip install -r requirements.txt`.
3. Lancez le lecteur en exécutant `python main.py` depuis le répertoire du projet.
## Utilisation
Lancez l'application. Vous pourrez charger des fichiers MP3 depuis un dossier de votre choix et contrôler la lecture avec les boutons de l'interface utilisateur.

## Personnalisation
Vous pouvez personnaliser l'apparence de l'application en modifiant les fichiers de style CSS intégrés.

## Contribution
Les contributions sont les bienvenues. Si vous souhaitez améliorer ce projet, n'hésitez pas à créer une issue ou un pull request.

## Licence
Ce projet est sous licence MIT. Voir le fichier [LICENSE](./LICENSE) pour plus de détails.