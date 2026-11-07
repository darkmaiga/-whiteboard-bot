import os
import requests
import asyncio
import time
import edge_tts
import google.generativeai as genai
from moviepy.editor import *
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
import random
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# 1. Récupération des clés
GEMINI_KEY = os.environ['GEMINI_API_KEY']
CLIENT_ID = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']

# 2. Moteur de Sujets
TOPICS = [
    "Why the middle class is getting poorer",
    "The hidden truth about the banking system",
    "How the rich avoid paying taxes",
    "The biggest financial scam in history",
    "Why inflation is a hidden tax on the poor",
    "The secret mindset of self-made millionaires"
]
chosen_topic = random.choice(TOPICS)

# 3. Génération du script avec Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')
prompt = f"""
You are a strict financial advisor. Write a hard-hitting script about: "{chosen_topic}".
Structure: Hook, The problem, Solution steps, Call to action.
Rules: Around 120 words. English. ONLY the spoken text.
"""
try:
    script_text = model.generate_content(prompt).text.strip()
except:
    script_text = "The system is designed to keep you poor. But there is a way out. Pay yourself first. Invest in assets, not liabilities. Start today."

# 4. Création de la voix off
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 5. Téléchargement d'une musique de fond sombre
has_music = False
try:
    music_url = "https://cdn.pixabay.com/audio/2022/03/15/audio_c8c8a73467.mp3"
    headers = {'User-Agent': 'Mozilla/5.0'}
    music_data = requests.get(music_url, headers=headers).content
    if len(music_data) > 10000: 
        with open("music.mp3", "wb") as handler:
            handler.write(music_data)
        has_music = True
except Exception as e:
    pass

# 6. Fonction pour créer une image de texte (Jaune / Blanc)
def create_text_image(text, is_yellow=False, filename="temp_text.png"):
    img_width = 1080
    img_height = 400
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_size = 100
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (img_width - w) / 2
    y = (img_height - h) / 2
        
    color = "#FFD700" if is_yellow else "#FFFFFF"
    draw.text((x, y), text, font=font, fill=color, stroke_width=6, stroke_fill="black")
    img.save(filename)
    return filename

# 7. Montage vidéo
voice_audio = AudioFileClip("audio.mp3")
duration = voice_audio.duration

# Fond sombre
bg_frame = np.full((1920, 1080, 3), (20, 20, 20), dtype=np.uint8)
bg_clip = ImageClip(bg_frame).set_duration(duration)

# Ajout de l'accroche en haut
hook_img = create_text_image(chosen_topic.upper(), is_yellow=False, filename="hook.png")
hook_clip = ImageClip(hook_img).set_position(('center', 200)).set_duration(duration)

# Découpage des sous-titres en bas
words = script_text.replace('\n', ' ').split()
chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
time_per_chunk = duration / len(chunks)

subtitles = []
current_time = 0

for i, chunk in enumerate(chunks):
    is_yellow = (i % 2 == 1)
    text_img_file = f"chunk_{i}.png"
    create_text_image(chunk.upper(), is_yellow, text_img_file)
    txt_clip = ImageClip(text_img_file).set_position(('center', 1400)).set_start(current_time).set_duration(time_per_chunk)
    subtitles.append(txt_clip)
    current_time += time_per_chunk

if has_music:
    try:
        music = AudioFileClip("music.mp3")
        music = music.loop(duration=duration).volumex(0.15)
        final_audio = CompositeAudioClip([voice_audio, music])
    except: final_audio = voice_audio
else:
    final_audio = voice_audio

video = CompositeVideoClip([bg_clip, hook_clip] + subtitles).set_audio(final_audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

# 8. Upload sur YouTube
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
