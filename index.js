const { createCanvas } = require('canvas');
const fs = require('fs');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const googleTTS = require('google-tts-api');
const { google } = require('googleapis');

ffmpeg.setFfmpegPath(ffmpegPath);

const text = "PAY YOURSELF FIRST. BEFORE YOU PAY YOUR RENT, MOVE 10% OF YOUR INCOME INTO SAVINGS.";
const words = text.split(" ");
const width = 1080;
const height = 1920;
const framesDir = './frames';

if (!fs.existsSync(framesDir)) fs.mkdirSync(framesDir);

// 🎨 FONCTION QUI DESSINE LA MAIN (Zéro lien externe, 100% fiable)
function drawHand(ctx, x, y) {
    // Le stylo (une ligne inclinée)
    ctx.beginPath();
    ctx.moveTo(x + 50, y + 100);
    ctx.lineTo(x - 50, y - 50);
    ctx.lineWidth = 8;
    ctx.strokeStyle = '#333333';
    ctx.stroke();

    // La main (un cercle pour la paume)
    ctx.beginPath();
    ctx.arc(x + 70, y + 120, 60, 0, Math.PI * 2);
    ctx.fillStyle = '#FFE0BD'; // Couleur de peau basique
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#D2A679';
    ctx.stroke();

    // Les doigts (petits rectangles)
    ctx.fillStyle = '#FFE0BD';
    ctx.strokeStyle = '#D2A679';
    ctx.lineWidth = 4;
    
    // Pouce
    ctx.beginPath();
    ctx.ellipse(x + 20, y + 70, 15, 30, Math.PI / 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    
    // Index
    ctx.beginPath();
    ctx.ellipse(x + 70, y + 60, 15, 40, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
}

async function generateAnimation() {
    console.log("1. Génération de la voix off...");
    const audioBase64 = await googleTTS.getAudioBase64(text, { lang: 'en', slow: false, host: 'https://translate.google.com' });
    fs.writeFileSync('audio.mp3', Buffer.from(audioBase64, 'base64'));

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

        let displayText = words.slice(0, i + 1).join(" ");
        const wordsPerLine = 4;
        const lines = displayText.match(new RegExp(`(\\S+\\s?){1,${wordsPerLine}}`, 'g')) || [];
        
        let yStart = height / 2 - (lines.length * 100) / 2;
        
        lines.forEach((line, index) => {
            ctx.fillText(line.trim(), 100, yStart + (index * 100));
        });

        // Position de la main
        let lastLineLength = lines[lines.length - 1].length * 40; 
        let handX = Math.min(100 + lastLineLength, width - 300);
        let handY = yStart + ((lines.length - 1) * 100) - 100; 

        // On appelle notre fonction de dessin de main
        drawHand(ctx, handX, handY);

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

generateAnimation()
    .then(() => uploadToYouTube())
    .catch(err => {
        console.error("Erreur :", err);
        process.exit(1);
    });
