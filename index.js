const { createCanvas, loadImage } = require('canvas');
const fs = require('fs');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const googleTTS = require('google-tts-api');
const { google } = require('googleapis');
const axios = require('axios');

ffmpeg.setFfmpegPath(ffmpegPath);

// Configuration du texte et de la vidéo
const text = "PAY YOURSELF FIRST. BEFORE YOU PAY YOUR RENT, MOVE 10% OF YOUR INCOME INTO SAVINGS.";
const words = text.split(" ");
const width = 1080;
const height = 1920;
const framesDir = './frames';

// Créer le dossier pour les images
if (!fs.existsSync(framesDir)) fs.mkdirSync(framesDir);

async function generateAnimation() {
    console.log("1. Génération de la voix off...");
    const audioBase64 = await googleTTS.getAudioBase64(text, { lang: 'en', slow: false, host: 'https://translate.google.com' });
    fs.writeFileSync('audio.mp3', Buffer.from(audioBase64, 'base64'));

    console.log("2. Téléchargement de l'image de la main...");
    // On utilise une image de main très fiable (Wikipédia)
    const handUrl = 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Hand_holding_a_pen.svg/512px-Hand_holding_a_pen.svg.png';
    
    // 👉 LA CORRECTION EST ICI : On ajoute un User-Agent pour tromper le blocage de Wikipédia
    const handResponse = await axios.get(handUrl, { 
        responseType: 'arraybuffer',
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
    });
    
    fs.writeFileSync('hand.png', handResponse.data);
    const handImg = await loadImage('hand.png');

    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');

    console.log("3. Création des images (frames)...");
    for (let i = 0; i < words.length; i++) {
        // Fond blanc
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, width, height);

        // Configuration du texte
        ctx.font = 'bold 80px Arial';
        ctx.fillStyle = '#000000';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';

        // Affichage du texte mot par mot
        let displayText = words.slice(0, i + 1).join(" ");
        const wordsPerLine = 4;
        const lines = displayText.match(new RegExp(`(\\S+\\s?){1,${wordsPerLine}}`, 'g')) || [];
        
        let yStart = height / 2 - (lines.length * 100) / 2;
        
        lines.forEach((line, index) => {
            ctx.fillText(line.trim(), 100, yStart + (index * 100));
        });

        // Position de la main (suit le dernier mot)
        let lastLineLength = lines[lines.length - 1].length * 40; 
        let handX = Math.min(100 + lastLineLength, width - 200);
        let handY = yStart + ((lines.length - 1) * 100) - 100; 

        // On dessine la main par-dessus
        ctx.drawImage(handImg, handX, handY, 250, 250);

        // Sauvegarde
        const buffer = canvas.toBuffer('image/png');
        fs.writeFileSync(`${framesDir}/frame_${String(i).padStart(4, '0')}.png`, buffer);
    }

    console.log("4. Analyse de la durée de l'audio...");
    const audioDuration = await new Promise((resolve, reject) => {
        ffmpeg.ffprobe('audio.mp3', (err, metadata) => {
            if (err) reject(err);
            else resolve(metadata.format.duration);
        });
    });

    const fps = words.length / audioDuration;
    console.log(`Durée audio : ${audioDuration}s, Images par seconde (FPS) : ${fps}`);

    console.log("5. Assemblage de la vidéo avec FFmpeg...");
    return new Promise((resolve, reject) => {
        ffmpeg()
            .input(`${framesDir}/frame_%04d.png`)
            .inputOptions(['-framerate', fps.toString()])
            .input('audio.mp3')
            .outputOptions([
                '-c:v libx264',
                '-pix_fmt yuv420p',
                '-c:a aac',
                '-shortest'
            ])
            .save('final_video.mp4')
            .on('end', () => {
                console.log('Vidéo générée avec succès !');
                resolve();
            })
            .on('error', (err) => reject(err));
    });
}

async function uploadToYouTube() {
    console.log("6. Envoi sur YouTube...");
    const oauth2Client = new google.auth.OAuth2(
        process.env.YT_CLIENT_ID,
        process.env.YT_CLIENT_SECRET,
        'https://developers.google.com/oauthplayground'
    );
    oauth2Client.setCredentials({ refresh_token: process.env.YT_REFRESH_TOKEN });
    const youtube = google.youtube({ version: 'v3', auth: oauth2Client });

    const res = await youtube.videos.insert({
        part: 'snippet,status',
        requestBody: {
            snippet: {
                title: 'Whiteboard Finance Tips 💡 #shorts',
                description: 'Automated finance tips. #finance #money #shorts',
                tags: ['finance', 'money', 'shorts'],
                categoryId: '27'
            },
            status: {
                privacyStatus: 'public'
            }
        },
        media: {
            body: fs.createReadStream('final_video.mp4')
        }
    });
    console.log("Vidéo publiée avec succès ! ID: " + res.data.id);
}

// Lancement
generateAnimation()
    .then(() => uploadToYouTube())
    .catch(err => {
        console.error("Erreur :", err);
        process.exit(1); // Force l'échec si ça plante
    });
