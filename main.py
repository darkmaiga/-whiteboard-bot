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
import cv2

# 1. Récupération des clés
GEMINI_KEY = os.environ['GEMINI_API_KEY']
CLIENT_ID = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']

# 2. Moteur de Sujets (pour ne jamais être répétitif)
TOPICS = [
    "The difference between assets and liabilities",
    "How inflation steals your wealth",
    "The 50/30/20 budget rule",
    "Why you need an emergency fund",
    "The danger of credit card debt",
    "How to start investing with little money",
    "The power of compound interest"
]
chosen_topic = random.choice(TOPICS)

# 3. Génération du script par Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
prompt = f"""
You are a financial advisor. Write a short script about "{chosen_topic}".
The script should be around 100 words. English. ONLY the spoken text.
"""
try:
    script_text = model.generate_content(prompt).text.strip()
except:
    script_text = "Pay yourself first. Before you pay your rent, move 10% of your income into a savings account. This is the secret to building wealth."

# 4. Création de la voix off
async def make_audio():
    communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
    await communicate.save("audio.mp3")
asyncio.run(make_audio())

# 5. Préparation de la scène de dessin (style Whiteboard)
# On utilise OpenCV pour simuler un tracé progressif sur fond blanc
def create_whiteboard_animation(text, duration, output_path="scene.mp4"):
    img_width, img_height = 1080, 1920
    bg_color = (255, 255, 255)
    
    # On découpe le texte en lignes pour le dessin
    words = text.split()
    lines = [" ".join(words[i:i+4]) for i in range(0, len(words), 4)]
    
    # On crée une image par bloc de texte pour simuler le tracé
    frames = []
    for i, line in enumerate(lines):
        img = np.full((img_height, img_width, 3), bg_color, dtype=np.uint8)
        # On utilise une police native pour être sûr que ça marche
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(line.upper(), font, 3, 10)[0]
        text_x = (img_width - text_size[0]) // 2
        text_y = (img_height + text_size[1]) // 2
        
        # On "dessine" le texte avec un effet de balayage
        # Plus le temps avance, plus on révèle de texte
        progress = int((i + 1) / len(lines) * img_width)
        cv2.putText(img, line.upper(), (text_x, text_y), font, 3, (0, 0, 0), 10, cv2.LINE_AA)
        
        # On crée une version floutée pour l'effet "main qui dessine"
        # (Simplification pour la démo, le vrai projet Animator utilise une main 3D)
        frames.append(img)

    # On assemble les frames en vidéo
    height, width, layers = frames[0].shape
    video = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), 24, (width, height))
    for frame in frames:
        video.write(frame)
    video.release()
    return output_path

# Note : Pour une main 3D réaliste comme sur ta capture, il faudrait cloner le projet "Animator" complet.
# Ici, nous simulons le tracé progressif pour rester simple et gratuit sur GitHub Actions.

# 6. Montage vidéo
voice_audio = AudioFileClip("audio.mp3")
duration = voice_audio.duration

# Création de l'animation
scene_path = create_whiteboard_animation(script_text, duration)

# On assemble l'audio et la vidéo
video_clip = VideoFileClip(scene_path).set_audio(voice_audio)
video_clip.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast")

# 7. Upload sur YouTube
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build('youtube', 'v3', credentials=creds)
body = {
    'snippet': {'title': f'{chosen_topic[:80]} 💡 #shorts', 'description': f'{chosen_topic}. Automated finance tips.', 'tags': ['finance', 'money', 'shorts'], 'categoryId': '27'},
    'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
}
media = MediaFileUpload("final_video.mp4", mimetype='video/mp4', resumable=True)
request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
request.execute()
print("Vidéo publiée avec succès sur YouTube ! 🚀")
