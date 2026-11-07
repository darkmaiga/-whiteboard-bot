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
import textwrap
import random
from PIL import Image, ImageDraw, ImageFont

# 1. Récupération des clés
GEMINI_KEY = os.environ['GEMINI_API_KEY']
CLIENT_ID = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']

# 2. Moteur de Sujets
TOPICS = [
    "How to get out of credit card debt fast",
    "The hidden truth about crypto scams",
    "Why buying a new car is a terrible financial mistake",
    "The 50/30/20 budget rule explained",
    "How inflation is secretly stealing your wealth",
    "Why you need an emergency fund before investing",
    "The difference between assets and liabilities"
]
chosen_topic = random.choice(TOPICS)

# 3. Génération du script (Court : ~100 mots pour 45s)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
prompt = f"""
You are a strict financial advisor. Write a hard-hitting script about: "{chosen_topic}".
Structure: Hook, The problem, Solution steps, Call to action.
Rules: Around 100 words. English. ONLY the spoken text.
"""
try:
    script_text = model.generate_content(prompt).text.strip()
except:
    script_text = "Pay yourself first. Before you pay your rent, before you buy that coffee, move 10% of your income into a savings account. This is the secret to building wealth. Start today, your future self will thank you."
print(f"Script généré :\n{script_text}\n")

# 4. Création de la voix off
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 5. Choix du fond "Tableau Blanc" (Blanc, Gris clair, ou Beige)
colors = ["#FFFFFF", "#F4F4F4", "#FDF5E6"]
bg_color = random.choice(colors)

# 6. Fonction pour créer l'image d'un bloc de mots (Texte NOIR sur fond clair)
def create_word_image(text, filename="temp_word.png"):
    img_width = 1080
    img_height = 300
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_size = 90
    try:
        # On télécharge une belle police
        font_url = "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
        font_data = requests.get(font_url).content
        with open("Montserrat.ttf", "wb") as f:
            f.write(font_data)
        font = ImageFont.truetype("Montserrat.ttf", font_size)
    except:
        font = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (img_width - w) / 2
    y = (img_height - h) / 2
        
    # Texte noir (pour le style tableau blanc) avec un léger contour blanc
    draw.text((x, y), text, font=font, fill="black", stroke_width=2, stroke_fill="white")
    img.save(filename)
    return filename

# 7. Montage vidéo
voice_audio = AudioFileClip("audio.mp3")
duration = voice_audio.duration

# Création du fond uni
bg_clip = ColorClip(size=(1080, 1920), color=bg_color).set_duration(duration)

# Découpage en blocs de 3 mots
words = script_text.replace('\n', ' ').split()
chunks = [" ".join(words[i:i+3]) for i in range(0, len(words), 3)]
time_per_chunk = duration / len(chunks)

subtitles = []
current_time = 0

for i, chunk in enumerate(chunks):
    text_img_file = f"chunk_{i}.png"
    create_word_image(chunk.upper(), text_img_file)
    txt_clip = ImageClip(text_img_file).set_position(('center', 500)).set_start(current_time).set_duration(time_per_chunk)
    subtitles.append(txt_clip)
    current_time += time_per_chunk

# Assemblage
video = CompositeVideoClip([bg_clip] + subtitles).set_audio(voice_audio)
video.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

# 8. Upload sur YouTube
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build('youtube', 'v3', credentials=creds)
body = {
    'snippet': {'title': f'{chosen_topic[:80]} 💡 #shorts', 'description': f'{chosen_topic}. Automated finance tips.', 'tags': ['finance', 'money', 'shorts'], 'categoryId': '27'},
    'status': {'privacyStatus': 'public', 'selfDeclaredMadeForUserKids': False}
}
media = MediaFileUpload("short.mp4", mimetype='video/mp4', resumable=True)
request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
request.execute()
print("Vidéo publiée avec succès sur YouTube ! 🚀")
