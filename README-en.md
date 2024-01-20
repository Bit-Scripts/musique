# BIT-SCRIPTS<br/>Musique

A modest music player written in Python. 
  
Pour la version en français de cette page de documentation aller [ici](./README.md).
  
## Table of Contents
- [Application Screenshots](#application-screenshots)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Discord RPC Integration](#discord-rpc-intégration)
- [Customization](#customization)
- [Contribution](#contribution)
- [FAQ and Troubleshooting](#faq-and-troubleshooting)
- [License](#license)
- [Contacts](#contacts)

## Application Screenshots
### Player Design:
![Player Design](Apercu.png)  
### Adding Music:
![Adding Music](Ajout-Musiques.png)
### In Action:  
https://github.com/Bit-Scripts/musique/assets/22844238/d0c22e06-2d05-4f93-a2ca-5435c50c4171  
### Discord RPC:
![Discord RPC](./Intégration-de-Discord-RPC.png)

## Features
- Plays audio files in MP3, WAVE, OGG, and FLAC formats.
- Simple controls with buttons to play/pause, skip to the next song, or go back to the previous one.
- Displays the waveform of the current song.
- Progress bar indicating the elapsed song time.
- Adjustable volume functionality.
- Customized user interface with window control buttons (minimize, maximize, close).
## Prerequisites
To run this music player, ensure you have installed the following:

### For all systems:
- [Python 3.x](https://www.python.org/downloads/) (not required if you use the binary)
- [PyQt5](https://pypi.org/project/PyQt5/) (not required if you use the binary)
- [Pygame](https://pypi.org/project/pygame/) (not required if you use the binary)
- [PyDub](https://pypi.org/project/pydub/) (not required if you use the binary)
- [Mutagen](https://pypi.org/project/mutagen/) (not required if you use the binary)
- [Pyqtgraph](https://pypi.org/project/pyqtgraph/) (not required if you use the binary)
- [FFmpeg](https://ffmpeg.org/download.html) **(essential for all systems)**

### For Windows:
- FFmpeg :
  - Install FFmpeg using one of the following command-line package managers:
    - Chocolatey ([How to install Chocolatey](https://chocolatey.org/install)):
      ```
      choco install ffmpeg
      ```
    - Winget ([How to install Winget](https://aymeric-cucherousset.fr/installer-winget-sur-windows/)):
      ```
      winget install ffmpeg
      ```
    - Scoop ([How to install Scoop](https://www.useweb.fr/blog/developpement/post/scoop-package-manager/)):
      ```
      scoop install ffmpeg
      ```
  - Alternatively, you can manually download FFmpeg from [the official website](https://ffmpeg.org/download.html), extract it, and add the `bin` folder to your system's `Path` environment variable.
  - Verify the installation with `ffmpeg -version`.

### For Linux:
Installation instructions for dependencies are provided for Ubuntu/Debian and Arch Linux/Manjaro. If you are using a different distribution, such as Fedora or RHEL, please consult your distribution's documentation for specific installation instructions for FFmpeg and other required dependencies.
- FFmpeg :
  - Install FFmpeg using your distribution's package manager.
    For example, on Ubuntu/Debian, use:
    ```bash
    sudo apt-get install ffmpeg
    ```
    Or on Arch Linux/Manjaro, use:
    ```bash
    sudo pacman -S ffmpeg
    ```
  - Verify the installation with `ffmpeg -version`.
- Other dependencies:
  - Install other dependencies using your distribution's package manager.
    For example, on Ubuntu/Debian, use:
    ```bash
    sudo apt-get install python3-pyqt5.qtsvg python3-opengl libgirepository1.0-dev
    ```
    Or on Arch Linux/Manjaro, use:
    ```bash
    sudo pacman -S python-pyqt5 python-opengl gobject-introspection qt5-wayland qt5-x11extras sdl2 sdl2_image sdl2_mixer sdl2_ttf
    ```
  
## Installation
1. For a quick installation, download the latest binary versions of the application [here](https://github.com/Bit-Scripts/musique/releases/latest). If you use the binary, you don't need to install Python or other dependencies, except for FFmpeg.
2. For manual installation, clone this repository or download it as a ZIP archive, then install the necessary dependencies by running pip install -r requirements.txt.  
3. Launch the player by executing `python main.py` from the project directory.  
  
## Usage
Start the application. You can load music files from a folder of your choice and control playback with the user interface buttons.  
  
## Discord RPC Integration
To enhance the user experience, I implemented displaying the currently playing music in Discord through the Discord RPC feature.
Here is a preview of the [Discord RPC integration](#discord-rpc).  
  
## Customization
You can customize the appearance of the application by modifying the integrated CSS style files.

## Contribution
We warmly welcome contributions to this project!    
  
If you have ideas for improvement, bug fixes, or wish to add new features, feel free to create a pull request or an [issue](https://github.com/Bit-Scripts/musique/issues). 
  
Even if you're new to open source, we'll be delighted to guide you through the process.   
  
To get started, you can:  
- Fork the project and test the code on your machine.
- Submit pull requests with your changes or additions.
- Create [issues](https://github.com/Bit-Scripts/musique/issues) to discuss bugs, improvement suggestions, or new features.
  
We commit to reading and responding to your requests.
  
## FAQ and Troubleshooting

### In all cases
- **Music Formats**  
Q: What audio formats can my music player play?  
A: The player supports MP3, WAVE, OGG, and FLAC formats. If you encounter problems with these formats, make sure you have the latest complete version of FFmpeg installed.   
  
- **Where are my music files**  
Q: The application can't find my music files.  
A: Ensure the files are in a supported format (flac, mp3, ogg, or wav) and the path is correct.  
  
- **Album Covers**  
Q: The integration of album covers doesn't seem to work.  
A: Album covers should be in jpg, jpeg, or png format and located in the same folder as the music files.   
  
- **Supported Operating Systems for the Audio Player**  
Q: On which operating systems can I use Bit-Scripts Music?  
A: Currently, Bit-Scripts Music is available for Microsoft Windows and most Linux distributions.    
  
- **Resource Issues**  
Q: Why does the music player sometimes slow down or freeze?  
A: This can be due to insufficient system resources, large audio files, or compatibility issues. Try closing other running applications and reducing the size of your music library. If the problem persists, please contact us via an issue, [here](https://github.com/Bit-Scripts/musique/issues).    
  
- **Issues with FFmpeg**  
Q: How do I configure FFmpeg to work with the music player?  
A: After installing the full version of FFmpeg, add its path to your system's Path environment variable. Consult the FFmpeg documentation for more details or create an issue [here](https://github.com/Bit-Scripts/musique/issues) for assistance.  
  
### Installation from Binaries
- **Updating**  
Q: How can I update my music player from the binary?  
A: Visit the [releases page](https://github.com/Bit-Scripts/musique/releases/latest) to download the latest version. If you are using the binary, simply replace the old executable file with the new one.  
  
### Installation via Python Files 
- **Installation Issues**  
Q: How do I resolve the "X" error during installation?  
A: Ensure that you have properly installed all dependencies. If the problem persists, don't hesitate to create an [issue on our GitHub page](https://github.com/Bit-Scripts/musique/issues).  
  
- **Updating**  
Q: How can I update my music player from a copy of the Python files?  
A: Perform a `git pull` in the application folder.  
  
- **Graphical Interface Issues**   
Q: What should I do if the graphical interface doesn't display correctly when launching the application with Python?  
A: Ensure that all dependencies, especially PyQt5 and Pyqtgraph, are properly installed. If the problem persists, try restarting the application or your system.  
  
In case of problems, open an [issue on GitHub](https://github.com/Bit-Scripts/musique/issues), and we commit to resolving your issue as soon as possible (please allow us at least two weeks, but the problem will be fixed).  
  
## License
This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for more details.  
  
## Legal Notices and Acknowledgments
### Icons
The icons used in this application are from [Iconduck](https://iconduck.com/sets/iconpark-icon-set/categories/music) and have been slightly modified to fit the design of the application. We would like to thank Iconduck for their remarkable work and contribution to the open-source community.  

### Contributions
[Red Moon](https://github.com/Quentin-D31): A big thank you to Red Moon for testing the application on Arch Linux and for his valuable feedback which helped to improve the user experience on different platforms.  
[Paul/Paullux](https://github.com/Paullux): For the initial development and ongoing maintenance of the project. If you would like to contribute to the project, please feel free to create a pull request or an issue on our [GitHub page](https://github.com/Bit-Scripts).  
  
We would like to thank everyone who contributes to the success of this project, whether through testing, suggestions, code contributions, or simply by sharing the project with others.  
  
## Contacts
We are continuously working to improve the project. Do not hesitate to contact us to share your feedback or ideas for improvement.    
  
- To interact with us, feel free to visit our [Discord server](https://discord.gg/6J5EX5hCeW) where you can ask questions or seek help.      
- You can contact me by email if needed; I suggest getting my email address either through [Discord](https://discord.gg/6J5EX5hCeW) or my [personal GitHub profile](https://github.com/Paullux).  
- If you like this project:  
Visit our website, [bit-scripts.github.io](https://bit-scripts.github.io/index.html), to find our other creations.  