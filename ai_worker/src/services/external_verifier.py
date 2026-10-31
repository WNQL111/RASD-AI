import os
import json
import logging
import requests
import base64
import threading

logger = logging.getLogger(__name__)

def verify_ambiguous_event_async(event_id, snapshot_path, event_type, current_conf, provider, api_key, redis_client):
    """Runs external AI verification in a background thread to prevent lag."""
    def run():
        try:
            logger.info(f"ExternalVerifier: Starting verification for event {event_id} using {provider}...")
            
            # Read image file to base64
            if not os.path.exists(snapshot_path):
                logger.error(f"ExternalVerifier: Snapshot not found at path: {snapshot_path}")
                return
            with open(snapshot_path, "rb") as f:
                img_data = f.read()
            img_b64 = base64.b64encode(img_data).decode('utf-8')
            
            prompt = (
                f"You are a security expert verifying a potential '{event_type}' alert from a CCTV feed. "
                f"Local computer vision confidence is {current_conf * 100}%. "
                f"Analyze the image and respond with a single JSON object having format:\n"
                f"{{\n  \"agree\": true/false,\n  \"reason\": \"short description\",\n  \"confidence_score\": 0.0 to 1.0\n}}"
            )

            result = None
            if provider.lower() == "gemini" and api_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                    "mimeType": "image/jpeg",
                                    "data": img_b64
                                }
                            }
                        ]
                    }]
                }
                res = requests.post(url, json=payload, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    text_resp = data["candidates"][0]["content"]["parts"][0]["text"]
                    if "```json" in text_resp:
                        text_resp = text_resp.split("```json")[1].split("```")[0].strip()
                    result = json.loads(text_resp)

            elif provider.lower() == "openai" and api_key:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "response_format": {"type": "json_object"}
                }
                res = requests.post(url, headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    result = json.loads(data["choices"][0]["message"]["content"])

            elif provider.lower() == "ollama":
                url = "http://host.docker.internal:11434/api/generate"
                payload = {
                    "model": "llava",
                    "prompt": prompt,
                    "images": [img_b64],
                    "stream": False,
                    "format": "json"
                }
                res = requests.post(url, json=payload, timeout=15)
                if res.status_code == 200:
                    result = json.loads(res.json().get("response", "{}"))

            if result:
                logger.info(f"ExternalVerifier: Response received: {result}")
                if redis_client:
                    redis_client.publish("asis_events_channel", json.dumps({
                        "type": "external_verification_update",
                        "event_id": event_id,
                        "external_decision": result
                    }))
            else:
                logger.warning("ExternalVerifier: No valid response received.")
        except Exception as e:
            logger.error(f"ExternalVerifier: Error in background verification: {e}")

    threading.Thread(target=run, daemon=True).start()
