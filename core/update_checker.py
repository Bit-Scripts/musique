import requests
import asyncio
from packaging import version

class UpdateChecker:
    def __init__(self, current_version, github_repo):
        """
        :param current_version: Ex: "1.0.0"
        :param github_repo: Ex: "Ton-Pseudo/Bit-Scripts"
        """
        self.current_version = current_version
        self.github_repo = github_repo
        self.api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"

    async def check_for_updates(self):
        """Vérifie asynchronement s'il y a une nouveauté sur les releases Github."""
        try:
            # Envoi requête réseau asynchrone non-bloquante via asyncio.to_thread
            response = await asyncio.to_thread(requests.get, self.api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").lstrip("v")
                
                # Compare "1.0.0" à "1.1.0"
                if latest_version and version.parse(latest_version) > version.parse(self.current_version):
                    release_url = data.get("html_url")
                    return True, latest_version, release_url
            return False, None, None
        except Exception as e:
            print(f"Erreur lors de la vérification de maj : {e}")
            return False, None, None
