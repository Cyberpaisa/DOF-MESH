import requests
import time
import json
import os

ROOM_ID = "f69-da87-0dce"
BASE_URL = f"https://www.agentmeet.net/api/v1/{ROOM_ID}" # Corregido URL base según instrucciones anteriores de API

class AgentMeetClient:
    def __init__(self, agent_name="Antigravity"):
        self.agent_name = agent_name
        self.agent_id = None
        self.latest_msg_id = 0

    def join(self):
        print(f"[*] Intentando unirse a la sala {ROOM_ID}...")
        try:
            # El usuario especificó api.agentmeet.net o www.agentmeet.net/api
            # Usaremos la URL proporcionada: https://www.agentmeet.net/api/v1/f69-da87-0dce/agent-join?format=json
            url = f"{BASE_URL}/agent-join?format=json"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                self.agent_id = data.get("agent_id")
                print(f"[+] Registrado con ID: {self.agent_id}")
                # Mostrar transcripción inicial si existe
                transcript = data.get("transcript", [])
                if transcript:
                    print("--- Transcripción Inicial ---")
                    for msg in transcript:
                        print(f"[{msg.get('agent_name')}]: {msg.get('content')}")
                        self.latest_msg_id = max(self.latest_msg_id, msg.get("id", 0))
                return True
            else:
                print(f"[-] Error al unirse: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[!] Excepción en join: {e}")
            return False

    def send_message(self, content):
        if not self.agent_id:
            print("[-] No registrado. Llama a join() primero.")
            return False
        
        url = f"{BASE_URL}/message"
        payload = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "content": content
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"[>] Mensaje enviado: {content}")
                return True
            else:
                print(f"[-] Error al enviar mensaje: {response.status_code}")
                return False
        except Exception as e:
            print(f"[!] Excepción en send_message: {e}")
            return False

    def check_replies(self):
        if not self.agent_id: return
        
        url = f"{BASE_URL}/wait"
        params = {
            "after": self.latest_msg_id,
            "agent_id": self.agent_id
        }
        try:
            # Long poll simulado o real (timeout 30s)
            response = requests.get(url, params=params, timeout=35)
            if response.status_code == 200:
                new_messages = response.json().get("messages", [])
                for msg in new_messages:
                    print(f"\a[NUEVO] [{msg.get('agent_name')}]: {msg.get('content')}")
                    self.latest_msg_id = max(self.latest_msg_id, msg.get("id", 0))
                return new_messages
            return []
        except requests.exceptions.Timeout:
            return []
        except Exception as e:
            print(f"[!] Error al chequear respuestas: {e}")
            return []

if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "Antigravity"
    client = AgentMeetClient(agent_name=name)
    if client.join():
        client.send_message(f"{name} (Legion Node/Provider) se ha unido al debate. Preparado para la Fase 10.")
        
        print(f"[*] {name} escuchando respuestas (presiona Ctrl+C para salir)...")
        try:
            while True:
                client.check_replies()
                time.sleep(2)
        except KeyboardInterrupt:
            print(f"\n[*] {name} saliendo...")
