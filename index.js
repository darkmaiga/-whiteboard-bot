const { createCanvas } = require('canvas');
const fs = require('fs');
const { execSync } = require('child_process');

// 1. Le texte à dessiner
const text = "PAY YOURSELF FIRST";

// 2. Création du Canvas (format vertical 1080x1920)
const width = 1080;
const height = 1920;
const canvas = createCanvas(width, height);
const ctx = canvas.getContext('2d');

// 3. Fond blanc
ctx.fillStyle = '#FFFFFF';
ctx.fillRect(0, 0, width, height);

// 4. Texte noir centré
ctx.font = 'bold 100px Arial';
ctx.fillStyle = '#000000';
ctx.textAlign = 'center';
ctx.textBaseline = 'middle';
ctx.fillText(text, width / 2, height / 2);

// 5. Sauvegarde de l'image
const buffer = canvas.toBuffer('image/png');
fs.writeFileSync('background.png', buffer);
console.log('Image générée avec succès !');

// 6. (Optionnel) Créer une vidéo à partir de l'image avec ffmpeg
// execSync('ffmpeg -loop 1 -i background.png -c:v libx264 -t 5 -pix_fmt yuv420p output.mp4');
