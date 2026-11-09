import os
import requests
import asyncio
import edge_tts
import google.generativeai as genai
from moviepy.editor import *
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
import random
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap

# 1. Clés
GEMINI_KEY = os.environ['GEMINI_API_KEY']
CLIENT_ID = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']

# 2. Sujet
TOPICS = ["Why the middle class is getting poorer", "The hidden truth about the banking system", "The biggest financial scam in history"]
chosen_topic = random.choice(TOPICS)

# 3. Script
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')
prompt = f"Write a hard-hitting 80-word script about: '{chosen_topic}'. English. ONLY the spoken text."
try:
    script_text = model.generate_content(prompt).text.strip()
except:
    script_text = "The system is designed to keep you poor. But there is a way out. Pay yourself first. Invest in assets, not liabilities. Start today."

# 4. Voix off (On change pour "Guy" qui a une voix plus grave et on accélère un peu pour le dynamisme)
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-GuyNeural", rate="+10%")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 5. Téléchargement de 3 images différentes (Banque, Argent, Graphique)
images = {
    "money": "https://cdn-icons-png.flaticon.com/512/217/217853.png",
    "bank": "https://cdn-icons-png.flaticon.com/512/2830/2830305.png",
    "chart": "https://cdn-icons-png.flaticon.com/512/2936/2936886.png"
}
for name, url in images.items():
    data = requests.get(url).content
    with open(f"{name}.png", "wb") as f:
        f.write(data)

# 6. Fonction texte
def create_text_image(text, is_yellow=False, filename="temp_text.png", is_hook=False):
    img_width, img_height = 1080, 400
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_size = 50 if is_hook else 65 
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
    lines = textwrap.wrap(text, width=18)
    total_height = len(lines) * (font_size + 10)
    y_start = (img_height - total_height) / 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (img_width - w) / 2
        y = y_start + i * (font_size + 10)
        color = "#FFD700" if is_yellow else "#FFFFFF"
        draw.text((x, y), line, font=font, fill=color, stroke_width=4, stroke_fill="black")
    img.save(filename)
    return filename

# 7. Montage
voice_audio = AudioFileClip("audio.mp3")
duration = voice_audio.duration

bg_clip = ColorClip(size=(1080, 1920), color=(10, 10, 10)).set_duration(duration)

hook_img = create_text_image(chosen_topic.upper(), filename="hook.png", is_hook=True)
hook_clip = ImageClip(hook_img).set_position(('center', 150)).set_duration(duration)

# 👉 GESTION DES IMAGES (Chacune disparaît avant que l'autre n'apparaisse)
# Image 1 (Argent) : Apparaît à 0s, disparaît à 4s, en haut à gauche
coin_clip = ImageClip("money.png").resize(height=300).set_start(0).set_end(4).set_position((150, 600))
coin_clip = coin_clip.resize(lambda t: 1 + 0.1 * np.sin(t * 5))

# Image 2 (Banque) : Apparaît à 4s, disparaît à 8s, en bas à droite
bank_clip = ImageClip("bank.png").resize(height=300).set_start(4).set_end(8).set_position((650, 1000))
bank_clip = bank_clip.resize(lambda t: 0.5 + 0.5 * np.minimum(1, t * 5)) # Effet pop-in

# Image 3 (Graphique) : Apparaît à 8s jusqu'à la fin, à gauche
chart_clip = ImageClip("chart.png").resize(height=400).set_start(8).set_position((100, 900))
chart_clip = chart_clip.set_position(lambda t: (100, 900 + 20 * np.sin(t * 3)))

# Sous-titres
words = script_text.replace('\n', ' ').split()
chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
time_per_chunk = duration / len(chunks)
subtitles = []
current_time = 0

for i, chunk in enumerate(chunks):
    is_yellow = (i % 2 == 1)
    text_img_file = f"chunk_{i}.png"
    create_text_image(chunk.upper(), is_yellow, text_img_file)
    txt_clip = ImageClip(text_img_file).set_position(('center', 1500)).set_start(current_time).set_duration(time_per_chunk)
    txt_clip = txt_clip.resize(lambda t: 1 + 0.05 * np.sin(t * 10))
    subtitles.append(txt_clip)
    current_time += time_per_chunk

video = CompositeVideoClip([bg_clip, hook_clip, coin_clip, bank_clip, chart_clip] + subtitles).set_audio(voice_audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

# 8. Upload
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build('youtube', 'v3', credentials=creds)
body = {
    'snippet': {'title': f'{chosen_topic[:80]} 💡 #shorts', 'description': f'{chosen_topic}. Automated finance tips.', 'tags': ['finance', 'money', 'shorts'], 'categoryId': '27'},
    'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
}
media = MediaFileUpload("short.mp4", mimetype='video/mp4', resumable=True)
request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
request.execute()
print("Vidéo publiée avec succès sur YouTube ! 🚀")
