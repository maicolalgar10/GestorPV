import os
import requests
from datetime import datetime

class PluggyService:
    BASE_URL = "https://api.pluggy.ai"

    def __init__(self):
        self.client_id = os.environ.get("PLUGGY_CLIENT_ID")
        self.client_secret = os.environ.get("PLUGGY_CLIENT_SECRET")
        self.api_key = None

    def _authenticate(self):
        """Autentica contra Pluggy y obtiene un API Key temporal."""
        if not self.client_id or not self.client_secret:
            raise Exception("Credenciales de Pluggy no configuradas en variables de entorno.")

        url = f"{self.BASE_URL}/auth"
        payload = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Error al autenticar en Pluggy: {response.text}")
            
        data = response.json()
        self.api_key = data.get("apiKey")
        return self.api_key

    def _get_headers(self):
        """Retorna los headers necesarios, autenticándose si es necesario."""
        if not self.api_key:
            self._authenticate()
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

    def create_connect_token(self):
        """Genera un Connect Token para inicializar el widget frontend."""
        url = f"{self.BASE_URL}/connect_token"
        # Opcionalmente se pueden mandar configuraciones en el payload (ej. webhookUrl)
        response = requests.post(url, headers=self._get_headers())
        
        if response.status_code not in (200, 201):
            raise Exception(f"Fallo al obtener Pluggy Connect Token: {response.text}")
            
        data = response.json()
        return data.get("accessToken")

    def get_accounts(self, item_id):
        """Obtiene las cuentas asociadas a un item_id."""
        url = f"{self.BASE_URL}/accounts?itemId={item_id}"
        response = requests.get(url, headers=self._get_headers())
        
        if response.status_code != 200:
            raise Exception(f"Error al obtener cuentas de Pluggy: {response.text}")
            
        return response.json().get("results", [])

    def get_transactions(self, account_id, date_from=None):
        """Obtiene las transacciones de una cuenta específica."""
        url = f"{self.BASE_URL}/transactions?accountId={account_id}"
        if date_from:
            url += f"&from={date_from}"
            
        response = requests.get(url, headers=self._get_headers())
        
        if response.status_code != 200:
            raise Exception(f"Error al obtener transacciones de Pluggy: {response.text}")
            
        return response.json().get("results", [])

    def delete_item(self, item_id):
        """Elimina la vinculación bancaria (Item) en Pluggy."""
        url = f"{self.BASE_URL}/items/{item_id}"
        response = requests.delete(url, headers=self._get_headers())
        
        if response.status_code not in (200, 204, 404):
            raise Exception(f"No se pudo eliminar el item en Pluggy: {response.status_code} - {response.text}")
            
        return True
