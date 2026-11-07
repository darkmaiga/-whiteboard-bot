const { createCanvas, loadImage } = require('canvas');
const fs = require('fs');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const googleTTS = require('google-tts-api');
const { google } = require('googleapis');
const axios = require('axios');

ffmpeg.setFfmpegPath(ffmpegPath);

// Configuration
const text = "PAY YOURSELF FIRST. BEFORE YOU PAY YOUR RENT, MOVE 10% OF YOUR INCOME INTO SAVINGS.";
const words = text.split(" ");
const width = 1080;
const height = 1920;
const fps = 24;
const framesDir = './frames';

// Créer le dossier pour les images
if (!fs.existsSync(framesDir)) fs.mkdirSync(framesDir);

async function generateAnimation() {
    console.log("1. Génération de la voix off...");
    // Génération de la voix (gratuit via Google Translate TTS)
    const audioBase64 = await googleTTS.getAudioBase64(text, { lang: 'en', slow: false, host: 'https://translate.google.com' });
    fs.writeFileSync('audio.mp3', Buffer.from(audioBase64, 'base64'));

    console.log("2. Préparation des éléments visuels...");
    // Téléchargement d'une image de main avec un stylo (fond transparent)
    const handUrl = 'https://png.pngtree.com/png-vector/20230817/ourmid/pngtree-hand-holding-pen-writing-png-image_9186431.png';
    const handResponse = await axios.get(handUrl, { responseType: 'arraybuffer' });
    fs.writeFileSync('hand.png', handResponse.data);
    const handImg = await loadImage('hand.png');

    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');

    console.log("3. Création des images (frames)...");
    // On crée une frame par mot
    for (let i = 0; i < words.length; i++) {
        // Fond blanc
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, width, height);

        // Configuration du texte
        ctx.font = 'bold 90px Arial';
        ctx.fillStyle = '#000000';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';

        // Affichage du texte mot par mot
        let displayText = words.slice(0, i + 1).join(" ");
        
        // Découpage en lignes pour ne pas dépasser de l'écran
        const wordsPerLine = 4;
        const lines = displayText.match(new RegExp(`(\\S+\\s?){1,${wordsPerLine}}`, 'g')) || [];
        
        let yStart = height / 2 - (lines.length * 100) / 2;
        
        lines.forEach((line, index) => {
            ctx.fillText(line.trim(), 100, yStart + (index * 110));
        });

        // Position de la main (elle suit le dernier mot)
        let lastLineLength = lines[lines.length - 1].length * 45; // Estimation de la largeur
        let handX = Math.min(100 + lastLineLength, width - 200);
        let handY = yStart + ((lines.length - 1) * 110) - 150; // Au-dessus du texte

        // On redimensionne la main pour qu'elle soit proportionnée
        ctx.drawImage(handImg, handX, handY, 300, 300);

        // Sauvegarde de l'image
        const buffer = canvas.toBuffer('image/png');
        fs.writeFileSync(`${framesDir}/frame_${String(i).padStart(4, '0')}.png`, buffer);
    }

    console.log("4. Assemblage de la vidéo avec FFmpeg...");
    // On calcule la durée d'affichage de chaque mot (basée sur une durée totale estimée)
    const totalDuration = 30; // environ 30 secondes
    const durationPerFrame = totalDuration / words.length;

    return new Promise((resolve, reject) => {
        ffmpeg()
            .input(`${framesDir}/frame_%04d.png`)
            .inputFPS(1 / durationPerFrame) // Ralentit les frames pour correspondre à la voix
            .input('audio.mp3')
            .outputOptions([
                '-c:v libx264',
                '-pix_fmt yuv420p',
                '-c:a aac',
                '-shortest' // La vidéo s'arrête quand l'audio s'arrête
            ])
            .save('final_video.mp4')
            .on('end', () => {
                console.log('Vidéo générée avec succès !');
                resolve();
            })
            .on('error', (err) => reject(err));
    });
}

// --- Upload sur YouTube ---
async function uploadToYouTube() {
    console.log("5. Envoi sur YouTube...");
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

// Lancement du processus
generateAnimation()
    .then(() => uploadToYouTube())
    .catch(err => console.error("Erreur :", err));
