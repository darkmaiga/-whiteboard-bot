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
import json

# 1. Clés
GEMINI_KEY = os.environ['GEMINI_API_KEY']
PIXABAY_KEY = os.environ['PIXABAY_API_KEY']
CLIENT_ID = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']

# 2. Sujet
TOPICS = [
    "Why the middle class is getting poorer",
    "The hidden truth about the banking system",
    "The biggest financial scam in history",
    "How inflation steals your wealth"
]
chosen_topic = random.choice(TOPICS)

# 3. Script et Mots-clés avec Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')
prompt = f"""
Write a hard-hitting 80-word script about: '{chosen_topic}'. English. ONLY the spoken text.
Also, provide 3 English keywords (1 word each) for images. Choose ONLY from this list: [money, bank, graph, scam, house, car, inflation, gold].
Return the result STRICTLY as a JSON object with keys: "script" and "keywords" (list of strings).
"""
try:
    response = model.generate_content(prompt).text
    response = response.replace("```json", "").replace("```", "").strip()
    data = json.loads(response)
    script_text = data['script']
    keywords = data['keywords']
except Exception as e:
    print(f"Erreur Gemini : {e}")
    script_text = "The system is designed to keep you poor. But there is a way out. Pay yourself first. Invest in assets, not liabilities. Start today."
    keywords = ["money", "bank", "graph"]

print(f"Script : {script_text}")
print(f"Mots-clés : {keywords}")

# 4. Voix off
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-GuyNeural", rate="+10%")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 5. Téléchargement des images via Pixabay
def download_pixabay_image(keyword, filename):
    # On cherche des illustrations (vectorielles) pour un rendu plus propre
    url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={keyword}&image_type=vector&orientation=vertical&per_page=3"
    response = requests.get(url).json()
    
    if response['hits']:
        img_url = response['hits'][0]['largeImageURL']
        print(f"Image Pixabay trouvée pour '{keyword}' : {img_url}")
        img_data = requests.get(img_url).content
        with open(filename, "wb") as handler:
            handler.write(img_data)
        return True
    else:
        print(f"Aucune image Pixabay pour '{keyword}', utilisation d'une icône de secours.")
        # Image de secours (pièce d'or)
        data = requests.get("https://cdn-icons-png.flaticon.com/512/217/217853.png").content
        with open(filename, "wb") as f:
            f.write(data)
        return False

# On télécharge les 3 images
img_files = []
for i, kw in enumerate(keywords[:3]):
    filename = f"img_{i}.png"
    download_pixabay_image(kw, filename)
    img_files.append(filename)

# 6. Fonction texte (identique)
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

# 7. Montage avec fond de couleur ALÉATOIRE
voice_audio = AudioFileClip("audio.mp3")
duration = voice_audio.duration

# 👉 On choisit une couleur de fond au hasard parmi une palette de gris/noirs
background_colors = [(10, 10, 10), (20, 20, 20), (30, 30, 30), (40, 40, 40)]
bg_color = random.choice(background_colors)
print(f"Couleur de fond choisie : {bg_color}")

bg_clip = ColorClip(size=(1080, 1920), color=bg_color).set_duration(duration)

hook_img = create_text_image(chosen_topic.upper(), filename="hook.png", is_hook=True)
hook_clip = ImageClip(hook_img).set_position(('center', 150)).set_duration(duration)

# Animation des images (apparition, zoom, flottement)
img1 = ImageClip(img_files[0]).resize(height=300).set_start(0).set_end(4).set_position((150, 600))
img1 = img1.resize(lambda t: 1 + 0.1 * np.sin(t * 5))

img2 = ImageClip(img_files[1]).resize(height=300).set_start(4).set_end(8).set_position((650, 1000))
img2 = img2.resize(lambda t: 0.5 + 0.5 * np.minimum(1, t * 5))

img3 = ImageClip(img_files[2]).resize(height=350).set_start(8).set_duration(duration - 8).set_position((200, 800))
img3 = img3.set_position(lambda t: (200, 800 + 20 * np.sin(t * 3)))

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

video = CompositeVideoClip([bg_clip, hook_clip, img1, img2, img3] + subtitles).set_audio(voice_audio)
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
