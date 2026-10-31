import os
import json
import logging
import hashlib
import time
import requests
import base64
from datetime import datetime
from sqlalchemy.orm import Session
from models.verification import VerificationRequest

logger = logging.getLogger(__name__)

# Queue configuration: list of verification request arguments to process sequentially or rate-limited
verification_queue = []
queue_lock = False

class VerificationService:
    """
    Enterprise Verification Service.
    Handles Gemini API requests, SHA256 caching, rate limit queuing, retries, and costs.
    """
    @staticmethod
    def calculate_image_hash(image_bytes: bytes) -> str:
        """Computes SHA256 hash of the snapshot image bytes to support caching."""
        return hashlib.sha256(image_bytes).hexdigest()

    @staticmethod
    def process_verification(
        event_id: str,
        image_path: str,
        event_type: str,
        current_conf: float,
        provider: str,
        api_key: str,
        db: Session
    ) -> dict:
        """
        Processes external AI verification. Checks cache first, applies retries,
        and saves request records to the database.
        """
        start_time = time.time()
        
        # 1. Read image data
        if not os.path.exists(image_path):
            logger.error(f"VerificationService: Image not found at {image_path}")
            return None
            
        with open(image_path, "rb") as f:
            img_bytes = f.read()
            
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        image_hash = VerificationService.calculate_image_hash(img_bytes)

        # 2. Cache Check (MD5/SHA256 of image content)
        # Check if we have an existing completed verification request with the same raw image hash
        cached_req = db.query(VerificationRequest).filter(
            VerificationRequest.raw_response.like(f"%{image_hash}%"),
            VerificationRequest.status == "VERIFIED"
        ).first()

        if cached_req and cached_req.raw_response:
            try:
                raw_data = json.loads(cached_req.raw_response)
                cached_decision = raw_data.get("decision")
                logger.info(f"VerificationService: CACHE HIT for image hash {image_hash}. Reusing request ID {cached_req.id}.")
                
                # Save new request referencing cache
                new_req = VerificationRequest(
                    event_id=event_id,
                    provider=provider,
                    request_time=datetime.utcnow(),
                    response_time=datetime.utcnow(),
                    status="VERIFIED",
                    agree=cached_req.agree,
                    confidence=cached_req.confidence,
                    reason_ar=cached_req.reason_ar,
                    reason_en=cached_req.reason_en,
                    raw_response=cached_req.raw_response,
                    cost=0.0,
                    cached=True,
                    latency=round(time.time() - start_time, 2)
                )
                db.add(new_req)
                db.commit()
                return cached_decision
            except Exception as e:
                logger.warning(f"VerificationService: Failed to load cached response: {e}")

        # 3. Create the specialized Prompt
        prompt = (
            f"You are an independent AI security verification system.\n"
            f"Analyze the provided image or clip and determine whether the local AI event '{event_type}' (Local confidence: {current_conf * 100}%) is actually correct.\n"
            f"Never assume an event happened unless there is clear visual evidence.\n\n"
            f"Reject the following false positives:\n"
            f"- Statues, Dolls, Mannequins, Posters, TV screens, Reflections, Shadows as active threats.\n"
            f"- For violence: Reject friends walking, standing together, queue, people talking, handshake, hug, children playing, crowd.\n"
            f"- For collision: Reject cars stopping, traffic lights, parking, normal passing, slow movement, lane changes.\n"
            f"- For theft: Reject owner carrying object, person inspecting item, cashier interaction, picking then returning, shared ownership, temporary movement.\n\n"
            f"Return ONLY a valid JSON object in this format:\n"
            f"{{\n"
            f"  \"agree\": true|false,\n"
            f"  \"confidence\": 0-100,\n"
            f"  \"category\": \"string\",\n"
            f"  \"reason_ar\": \"detailed explanation in Arabic\",\n"
            f"  \"reason_en\": \"detailed explanation in English\",\n"
            f"  \"observations\": [],\n"
            f"  \"risk\": \"low|medium|high|critical\",\n"
            f"  \"recommendation\": \"actionable recommendation\",\n"
            f"  \"requires_manual_review\": true|false\n"
            f"}}"
        )

        # 4. Prepare request record
        req_record = VerificationRequest(
            event_id=event_id,
            provider=provider,
            request_time=datetime.utcnow(),
            status="PENDING"
        )
        db.add(req_record)
        db.commit()

        # 5. Execute API Query with Retries and Timeout
        retries = 3
        timeout_sec = 8.0
        response_json = None
        cost = 0.0

        for attempt in range(retries):
            try:
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
                    res = requests.post(url, json=payload, timeout=timeout_sec)
                    if res.status_code == 200:
                        data = res.json()
                        text_resp = data["candidates"][0]["content"]["parts"][0]["text"]
                        if "```json" in text_resp:
                            text_resp = text_resp.split("```json")[1].split("```")[0].strip()
                        response_json = json.loads(text_resp)
                        cost = 0.0003 # Flat rate estimation for flash image input
                        break

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
                    res = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
                    if res.status_code == 200:
                        data = res.json()
                        response_json = json.loads(data["choices"][0]["message"]["content"])
                        cost = 0.0005
                        break
                        
                elif provider.lower() == "ollama":
                    # Local Ollama connection
                    url = "http://host.docker.internal:11434/api/generate"
                    payload = {
                        "model": "llava",
                        "prompt": prompt,
                        "images": [img_b64],
                        "stream": False,
                        "format": "json"
                    }
                    res = requests.post(url, json=payload, timeout=12.0)
                    if res.status_code == 200:
                        response_json = json.loads(res.json().get("response", "{}"))
                        break
            except Exception as e:
                logger.warning(f"VerificationService: Attempt {attempt+1} failed for event {event_id}: {e}")
                time.sleep(1.0)

        latency = round(time.time() - start_time, 2)
        
        # 6. Save results to Database
        if response_json:
            req_record.response_time = datetime.utcnow()
            req_record.status = "VERIFIED" if response_json.get("agree", True) else "DISAGREED"
            req_record.agree = response_json.get("agree", True)
            req_record.confidence = response_json.get("confidence", 80.0)
            req_record.reason_ar = response_json.get("reason_ar", "")
            req_record.reason_en = response_json.get("reason_en", "")
            req_record.cost = cost
            # Store image hash inside raw response to support future cache hit lookups
            response_json["image_hash"] = image_hash
            req_record.raw_response = json.dumps({"decision": response_json, "image_hash": image_hash})
            req_record.latency = latency
            db.commit()
            return response_json
        else:
            req_record.status = "MANUAL_REVIEW"
            db.commit()
            return None
