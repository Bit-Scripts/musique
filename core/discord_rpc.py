import os
import asyncio
import pyimgur
from pypresence import AioPresence

class DiscordRPCManager:
    """Gestionnaire asynchrone pour la Rich Presence Discord et l'upload Imgur."""
    
    def __init__(self, client_id_discord, client_id_imgur):
        self.client_id_discord = client_id_discord
        self.client_id_imgur = client_id_imgur
        self.rpc = None
        self.uploaded_images_cache = {}

    async def connect(self):
        """Initialise la connexion à Discord RPC."""
        if not self.client_id_discord:
            print("Discord RPC désactivé : Aucun Client ID fourni.")
            return

        try:
            self.rpc = AioPresence(self.client_id_discord)
            await self.rpc.connect()
            print("Connecté à Discord RPC via AioPresence.")
        except Exception as e:
            print(f"Erreur d'initialisation Discord RPC (Discord fermé ?) : {e}")
            self.rpc = None

    async def update_rpc(self, title, artist, image_url):
        """Met à jour la présence Discord de manière asynchrone."""
        if self.rpc is None:
            return

        try:
            if not title and not artist:
                await self.rpc.clear()
                return
            
            await self.rpc.update(
                details=title or "Inconnu",
                state=artist or "Inconnu",
                large_image=image_url or "music_bot",
                large_text="Entrain d'écouter"
            )
            print("Présence Discord mise à jour.")
        except Exception as e:
            print(f"Erreur de mise à jour RPC : {e}")

    async def upload_image_and_update_rpc(self, image_path, title, artist):
        """Gère intelligemment l'upload Imgur et met à jour Discord."""
        if self.rpc is None:
            return

        if not title and not artist:
            await self.update_rpc("", "", "")
            return

        image_url = "music_bot"

        # On n'upload que si une image est réellement fournie
        if image_path and os.path.exists(image_path):
            safe_image_path = image_path.replace("file://", "")
            
            if safe_image_path in self.uploaded_images_cache:
                image_url = self.uploaded_images_cache[safe_image_path]
            elif self.client_id_imgur:
                try:
                    def upload():
                        im = pyimgur.Imgur(self.client_id_imgur)
                        return im.upload_image(safe_image_path, title="Cover").link
                        
                    url = await asyncio.to_thread(upload)
                    self.uploaded_images_cache[safe_image_path] = url
                    image_url = url
                    print(f"Upload Imgur réussi : {image_url}")
                except Exception as e:
                    print(f"Échec de l'upload Imgur : {e}")
        
        await self.update_rpc(title, artist, image_url)
        
    async def close_async(self):
        """Purge asynchrone de la présence sur les serveurs Discord avant la coupure locale."""
        if self.rpc:
            try:
                await self.rpc.clear()
            except Exception:
                pass
            try:
                self.rpc.close()
            except Exception:
                pass

    def close(self):
        """Sécurité."""
        if self.rpc:
            try:
                self.rpc.close()
            except:
                pass

