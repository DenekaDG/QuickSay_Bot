import os
import logging
import aiohttp
import asyncio
import subprocess
import psycopg2
import math
from celery import Celery

from config import BOT_TOKEN, GROQ_API_KEY, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, REDIS_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot"
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

DB_PARAMS = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": int(DB_PORT)
}

celery_app = Celery("audio_tasks", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300
)

def get_audio_duration(file_path):
    try:
        logger.info(f"📏 Замеряю длительность файла: {file_path}")
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(float(result.stdout.strip()))
    except Exception as e:
        logger.error(f"⚠️ Ошибка ffprobe: {e}")
    return 0

def update_user_balance(chat_id, minutes_spent):
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET balance_minutes = balance_minutes - %s WHERE telegram_id = %s",
            (minutes_spent, chat_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"💳 Баланс {chat_id}: -{minutes_spent} мин.")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления баланса в БД: {e}")
        return False

def extract_audio_from_video(video_path):
    audio_path = video_path.rsplit('.', 1)[0] + ".mp3"
    try:
        logger.info(f"🎬 Конвертирую видео через ffmpeg: {video_path}")
        command = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "4", audio_path]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(audio_path):
            return audio_path
        logger.error(f"❌ Ошибка ffmpeg: {result.stderr}")
        return None
    except Exception as e:
        logger.error(f"❌ Сбой ffmpeg: {e}")
        return None

def split_long_message(text, max_length=4000):
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
    url = f"{TELEGRAM_API_URL}{BOT_TOKEN}/sendMessage"
    messages = split_long_message(text)
    async with aiohttp.ClientSession() as session:
        for msg in messages:
            payload = {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.error(f"❌ Ошибка отправки Telegram: {resp.status}")
            except Exception as e:
                logger.error(f"❌ Сбой сети Telegram API: {e}")
            await asyncio.sleep(0.5)

async def transcribe_audio(file_path):
    try:
        logger.info(f"🎙️ Отправка в Groq Whisper: {file_path}")
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
                    return None
    except Exception as e:
        logger.error(f"❌ Ошибка Groq Whisper: {e}")
        return None

async def analyze_with_llama(text, user_style="summary"):
    try:
        logger.info(f"🧠 Анализ Llama. Режим: {user_style}")
        
        local_lang_map = {
            "ua": "УКРАИНСКИЙ", "en": "АНГЛИЙСКИЙ", "de": "НЕМЕЦКИЙ",
            "fr": "ФРАНЦУЗСКИЙ", "es": "ИСПАНСКИЙ", "it": "ИТАЛЬЯНСКИЙ"
        }

        # Настройка температуры под задачи
        if user_style in ["creative", "opponent", "diary"]:
            temperature = 0.7
        elif user_style == "insider":
            temperature = 0.4
        else:
            temperature = 0.2

        # 1. Логика перевода на 6 языков
        if str(user_style).startswith("lang_"):
            lang_code = user_style.split("_")[1]
            target_language = local_lang_map.get(lang_code, "АНГЛИЙСКИЙ")
            prompt = f"""ТЫ — ПРОФЕССИОНАЛЬНЫЙ ПЕРЕВОДЧИК. Сделай точный перевод текста на {target_language}. Весь твой ответ должен быть ИСКЛЮЧИТЕЛЬНО на целевом языке. РУССКИЙ ИСПОЛЬЗОВАТЬ ЗАПРЕЩЕНО!
Оформи ответ:
<b>🌐 Полный перевод / Full Translation:</b>
(Точный литературный перевод всего оригинального текста)

<b>📌 Суть / Summary:</b>
(Одно-два предложения с описанием главной мысли)

Текст:
{text}"""

        # 2. Новые и старые контентные режимы
        elif user_style == "creative":
            prompt = f"""Ты — харизматичный рассказчик. Перескажи этот текст живым, интересным, творческим языком, добавь немного здоровой иронии и красивых метафор. Отвечай на русском языке.\n\n<b>🎨 Креативный пересказ:</b>\n""" + f"{text}"

        elif user_style == "meeting":
            prompt = f"""Ты — корпоративный секретарь. Сформируй официальный протокол встречи (Meeting Minutes) на основе текста. Структурируй хаотичную речь. Отвечай на русском языке.
<b>💼 Официальный протокол встречи</b>
<b>📝 Обсуждаемые вопросы:</b> (Главные темы встречи)
<b>🎯 Принятые решения:</b> (Что именно решили и утвердили)
<b>⚡ Дедлайны и ответственные:</b> (Если есть указания, кто что делает и к какому числу. Если нет — напиши 'Не указаны')

Текст:
{text}"""

        elif user_style == "insider":
            prompt = f"""Выдели одну самую главную, емкую и ключевую мысль из этого текста. Избавься от всей воды, вступлений и деталей. Выдай ровно одну строку, бьющую в цель. Отвечай на русском языке.\n\n<b>⚡ Главный инсайт (В одну строку):</b>\n""" + f"«{text}»"

        elif user_style == "editor":
            prompt = f"""Ты — профессиональный редактор. Очисти этот текст от слов-паразитов, заиканий, повторов и лишних 'э-э-э'/'ну'. Сделай его грамматически идеальным, расставь знаки препинания, разбей на логические абзацы. ВНИМАНИЕ: Не сокращай смысл и полностью сохраняй все важные мысли автора. Не пересказывай! Отвечай на русском языке.\n\n<b>📝 Отредактированный чистый текст:</b>\n{text}"""

        elif user_style == "opponent":
            prompt = f"""Действуй как жесткий, но конструктивный бизнес-консультант и оппонент. Найди скрытые проблемы, логические уязвимости или риски в рассуждениях автора. Задай глубокие вопросы. Отвечай на русском языке.
<b>🧠 Анализ оппонента</b>
<b>➕ Сильные стороны мысли:</b> (Что звучит логично и правильно)
<b>⚠️ Слабые места и риски:</b> (В чем автор ошибается или где есть угрозы)
<b>🤔 Вопросы на подумать:</b> (3 глубоких вопроса, на которые автору нужно ответить самому себе)

Текст:
{text}"""

        elif user_style == "diary":
            prompt = f"""Ты — личный психологический ассистент. Проанализируй эту дневниковую запись автора. Выдели эмоциональный фон и ключевые маркеры. Отвечай на русском языке.
<b>🌱 Анализ дневника</b>
<b>🎭 Эмоциональное состояние:</b> (Какое настроение считывается: тревога, подъем, усталость, радость)
<b>🧩 Главные фокусы мыслей:</b> (О чем больше всего переживает или думает автор)
<b>🏷️ Хэштеги для базы знаний:</b> (Например: #работа #эмоции #планы)

Текст:
{text}"""

        else: # Дефолтная Суть (summary)
            prompt = f"""Ты — профессиональный ассистент. Сделай краткую, жесткую выжимку текста. Выдели только ключевую суть и конкретные задачи/действия (Action Items), если они есть. Отвечай на русском языке.
<b>📌 Главная суть:</b>
(Краткое описание сути текста в 2-3 предложениях)

<b>📋 Задачи и действия:</b>
- (Пункт 1)
- (Пункт 2)

Текст:
{text}"""
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": 2000
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                return None
    except Exception as e:
        logger.error(f"❌ Ошибка Llama: {e}")
        return None

@celery_app.task(name="tasks.process_audio_task", bind=True, max_retries=3)
def process_audio_task(self, file_path, chat_id, user_style="summary"):
    logger.info(f"🚀 Задача Celery запущена для файла: {file_path}")
    extracted_audio = None
    try:
        if not os.path.exists(file_path):
            logger.error(f"❌ Файл отсутствует: {file_path}")
            return
        
        seconds_duration = get_audio_duration(file_path)
        minutes_spent = max(1, math.ceil(seconds_duration / 60))
        
        if file_path.lower().endswith(".mp4"):
            extracted_audio = extract_audio_from_video(file_path)
            if extracted_audio:
                target_processing_file = extracted_audio
            else:
                asyncio.run(send_telegram_message(chat_id, "❌ Ошибка извлечения звука из видео."))
                return
        else:
            target_processing_file = file_path
        
        text_result = asyncio.run(transcribe_audio(target_processing_file))
        if not text_result or len(text_result.strip()) == 0:
            asyncio.run(send_telegram_message(chat_id, "❌ Не удалось распознать речь. В файле тишина."))
            return
        
        ai_summary = asyncio.run(analyze_with_llama(text_result, user_style))
        if not ai_summary or len(ai_summary.strip()) == 0:
            asyncio.run(send_telegram_message(chat_id, "❌ Нейросеть вернула пустой ответ."))
            return
        
        final_text = f"<b>📜 Оригинальный текст:</b>\n<i>{text_result}</i>\n\n{ai_summary}"
        asyncio.run(send_telegram_message(chat_id, final_text))
        update_user_balance(chat_id, minutes_spent)
        
    except Exception as e:
        logger.error(f"❌ Сбой воркера: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=5)
    finally:
        for path in [file_path, extracted_audio]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"🗑️ Удален временный файл: {path}")
                except Exception as err:
                    logger.error(f"⚠️ Ошибка удаления {path}: {err}")