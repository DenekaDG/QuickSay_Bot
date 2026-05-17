import os
import logging
import aiohttp
import asyncio
import subprocess
from celery import Celery
from config import BOT_TOKEN, GROQ_API_KEY

# Настраиваем логирование воркера
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot"
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

# Инициализация Celery под Docker
celery_app = Celery("audio_tasks", broker="redis://redis:6379/0", backend="redis://redis:6379/0")
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300
)

def extract_audio_from_video(video_path):
    """Вырезает аудиодорожку в формате mp3 из видеофайлов с помощью ffmpeg"""
    audio_path = video_path.rsplit('.', 1)[0] + ".mp3"
    try:
        logger.info(f"🎬 Видео-формат. Конвертирую через ffmpeg: {video_path} -> {audio_path}")
        command = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "4", audio_path]
        
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0 and os.path.exists(audio_path):
            logger.info("✅ Звук успешно извлечен.")
            return audio_path
        else:
            logger.error(f"❌ Ошибка работы ffmpeg (код {result.returncode}): {result.stderr}")
            return None
    except Exception as e:
        logger.error(f"❌ Исключение при вызове ffmpeg: {e}")
        return None

def split_long_message(text, max_length=4000):
    """Построчно разбивает длинные тексты, чтобы не превышать лимит Telegram"""
    if len(text) <= max_length:
        return [text]
    parts = []
    current_part = ""
    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part)
            current_part = line
        else:
            current_part += '\n' + line if current_part else line
    if current_part:
        parts.append(current_part)
    return parts

async def send_telegram_message(chat_id, text):
    """Асинхронная отправка сообщений пользователю"""
    url = f"{TELEGRAM_API_URL}{BOT_TOKEN}/sendMessage"
    messages = split_long_message(text)
    async with aiohttp.ClientSession() as session:
        for msg in messages:
            payload = {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.error(f"❌ Ошибка отправки сообщения {resp.status}: {await resp.text()}")
            except Exception as e:
                logger.error(f"❌ Проблема соединения с Telegram API: {e}")
            await asyncio.sleep(0.5)

async def transcribe_audio(file_path):
    """Отправляет аудиофайл в облачный Whisper на серверах Groq Cloud"""
    try:
        logger.info(f"🎙️ Отправка медиафайла в Groq Whisper: {file_path}")
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as audio_file:
                data = aiohttp.FormData()
                data.add_field('file', audio_file, filename=os.path.basename(file_path))
                data.add_field('model', 'whisper-large-v3-turbo')
                
                async with session.post(GROQ_AUDIO_URL, headers=headers, data=data, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("text", "").strip()
                    logger.error(f"❌ Groq Whisper API вернул ошибку {resp.status}: {await resp.text()}")
                    return None
    except Exception as e:
        logger.error(f"❌ Ошибка сети при транскрибации: {e}")
        return None

async def analyze_with_llama(text, user_style="business"):
    """Анализирует или переводит текст через Groq Llama 3.1"""
    try:
        logger.info(f"🧠 Передаю текст в Llama. Стиль: {user_style}")
        
        # Локальные изолированные маппинги, защищенные от внешних конфликтов импорта
        local_lang_map = {
            "en": "АНГЛИЙСКИЙ (ENGLISH)",
            "de": "НЕМЕЦКИЙ (GERMAN)",
            "pl": "ПОЛЬСКИЙ (POLISH)",
            "es": "ИСПАНСКИЙ (SPANISH)",
            "fr": "ФРАНЦУЗСКИЙ (FRENCH)",
            "it": "ИТАЛЬЯНСКИЙ (ITALIAN)"
        }

        local_style_prompts = {
            "business": "Ты — профессиональный бизнес-ассистент. Сделай краткую выжимку текста, выдели суть, ключевые мысли и задачи (Action Items). Оформляй красиво с HTML-тегами <b>.",
            "summary": "Ты — опытный редактор. Сделай подробный, структурированный конспект текста, сохранив все важные детали и хронологию. Используй списки и HTML-теги <b>.",
            "translate_ua": "ТЫ — ПРОФЕССИОНАЛЬНЫЙ ПЕРЕВОДЧИК. Твоя задача — сделать полный литературный перевод предоставленного текста строго на УКРАИНСКИЙ ЯЗЫК. Возьми оригинальный текст и переведи его от начала и до конца. Оформи ответ красиво с HTML-тегами <b>.",
            "philosophy": "Ты — глубокий мыслитель и философ. Проанализируй текст с точки зрения скрытых смыслов, логики и концепций. Оформи ответ красиво с HTML-тегами <b>.",
            "humor": "Ты — харизматичный стендап-комик и сатирик. Перескажи этот текст с юмором, иронией и шутками, не теряя общего смысла. Оформи ответ красиво с HTML-тегами <b>."
        }
        
        # 1. Сценарий: Международный перевод (lang_en, lang_de и т.д.)
        if str(user_style).startswith("lang_"):
            lang_code = user_style.split("_")[1]
            target_language = local_lang_map.get(lang_code, "АНГЛИЙСКИЙ (ENGLISH)")
            
            prompt = f"""ТЫ — ПРОФЕССИОНАЛЬНЫЙ МЕЖДУНАРОДНЫЙ ПЕРЕВОДЧИК.
Твоя задача — сделать полный точный литературный перевод предоставленного текста строго на {target_language}.
Вся твоя выжимка и весь твой ответ должны быть написаны ИСКЛЮЧИТЕЛЬНО на целевом языке ({target_language}). Использование русского или украинского языков в ответе строго запрещено!

Оформи ответ красиво с HTML-тегами:
<b>🌐 Полный перевод / Full Translation:</b>
(Здесь напиши красивый, точный перевод всего оригинального текста на целевом языке)

<b>📌 Основная суть / Summary:</b>
(Одно-два предложения с описанием главной сути текста на целевом языке)

Текст для перевода:
{text}"""

        # 2. Сценарий: Перевод на украинский
        elif user_style == "translate_ua":
            prompt = f"{local_style_prompts['translate_ua']}\n\nВесь ответ пиши строго на украинском языке!\n\nТекст:\n{text}"
            
        # 3. Сценарий: Обычные стили (бизнес, конспект, юмор)
        else:
            selected_prompt = local_style_prompts.get(user_style, local_style_prompts['business'])
            prompt = f"{selected_prompt}\n\nОтвечай строго на русском языке.\n\nТекст:\n{text}"
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,  # Низкая температура убирает галлюцинации и заставляет строго переводить
            "max_tokens": 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                logger.error(f"❌ Groq Llama API вернул ошибку {resp.status}: {await resp.text()}")
                return None
    except Exception as e:
        logger.error(f"❌ Ошибка сети при запросе к Llama: {e}")
        return None

@celery_app.task(name="tasks.process_audio_task", bind=True, max_retries=3)
def process_audio_task(self, file_path, chat_id, user_style="business"):
    """Основной конвейер Celery по обработке задач"""
    logger.info(f"🚀 Celery взял задачу в работу для файла: {file_path}")
    extracted_audio = None
    
    try:
        if not os.path.exists(file_path):
            logger.error(f"❌ Файл физически отсутствует на диске: {file_path}")
            return
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 25:  # Ограничение Groq на размер файла
            asyncio.run(send_telegram_message(chat_id, "❌ Файл превышает лимит в 25MB."))
            return
        
        target_processing_file = file_path
        
        # Обработка видео контейнера
        if file_path.lower().endswith(".mp4"):
            extracted_audio = extract_audio_from_video(file_path)
            if extracted_audio:
                target_processing_file = extracted_audio
            else:
                asyncio.run(send_telegram_message(chat_id, "❌ Ошибка извлечения звука из видео."))
                return
        
        # Шаг 1: Распознавание голоса
        text_result = asyncio.run(transcribe_audio(target_processing_file))
        if not text_result:
            asyncio.run(send_telegram_message(chat_id, "❌ Не удалось распознать аудиосообщение."))
            return
        
        # Шаг 2: ИИ-Анализ / Жесткий перевод по веткам стилей
        ai_summary = asyncio.run(analyze_with_llama(text_result, user_style))
        if not ai_summary:
            asyncio.run(send_telegram_message(chat_id, "❌ Не удалось структурировать текст."))
            return
        
        # Шаг 3: Формирование и отправка финального ответа
        final_text = f"<b>📜 Оригинальный текст:</b>\n<i>{text_result}</i>\n\n{ai_summary}"
        asyncio.run(send_telegram_message(chat_id, final_text))
        logger.info("✨ Ответ успешно доставлен в Telegram!")
        
    except Exception as e:
        logger.error(f"❌ Критический сбой воркера: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=5)
    finally:
        # Железобетонное удаление мусора с диска после обработки
        for path in [file_path, extracted_audio]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"🗑️ Удален временный файл: {path}")
                except Exception as err:
                    logger.error(f"⚠️ Не удалось стереть файл {path}: {err}")