import time
import requests
from openai import OpenAI

# 1. Настраиваем подключение к локальным контейнерам
whisper_client = OpenAI(base_url="http://localhost:8000/v1", api_key="cant-be-empty")
OLLAMA_URL = "http://localhost:11434/api/generate"

AUDIO_FILE = "test.ogg"  # Имя твоего файла

print("--- Начинаем тест ИИ-комбайна ---")

# --- ЭТАП 1: РАСПОЗНАВАНИЕ РЕЧИ (WHISPER) ---
print(f"\n1. Отправляем файл '{AUDIO_FILE}' в Whisper...")
start_time = time.time()

try:
    with open(AUDIO_FILE, "rb") as audio:
        transcription = whisper_client.audio.transcriptions.create(
            model="small", 
            file=audio,
            language="uk",  # Код "uk" для украинского языка
            extra_body={
                "temperature": 0.0,
                "no_speech_threshold": 0.6,
                "compression_ratio_threshold": 2.4
            }
        )
    whisper_time = time.time() - start_time
    text_result = transcription.text
    print(f"✅ Успешно! Время обработки Whisper: {whisper_time:.2f} сек.")
    print(f"📋 Распознанный текст:\n\"{text_result}\"")
except Exception as e:
    print(f"❌ Ошибка в Whisper: {e}")
    exit()

# --- ЭТАП 2: СУММАРИЗАЦИЯ (OLLAMA) ---
print("\n2. Отправляем текст в Ollama для создания саммари...")
start_time = time.time()

prompt = f"""
Проанализируй следующий текст и сделай его краткую выжимку (саммари) в виде маркированного списка основных мыслей. Отвечай строго на русском языке.

Текст для анализа:
{text_result}
"""

payload = {
    "model": "llama3:8b-instruct-q4_K_M",
    "prompt": prompt,
    "stream": False
}

try:
    response = requests.post(OLLAMA_URL, json=payload)
    ollama_time = time.time() - start_time
    
    if response.status_code == 200:
        summary = response.json().get("response")
        print(f"✅ Успешно! Время обработки Ollama: {ollama_time:.2f} сек.")
        print(f"🤖 Результат ИИ-аналитики:\n{summary}")
    else:
        print(f"❌ Ошибка Ollama (Код {response.status_code}): {response.text}")
except Exception as e:
    print(f"❌ Ошибка при запросе к Ollama: {e}")

print("\n--- Тест завершен ---")
