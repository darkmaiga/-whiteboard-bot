const { createCanvas } = require('canvas');
const fs = require('fs');
const { execSync } = require('child_process');

// 1. Le script (on le génère en dur pour le test)
const text = "PAY YOURSELF FIRST";
const words = text.split(" ");

// 2. Création du Canvas (format vertical 1080x1920)
const width = 1080;
const height = 1920;
const canvas = createCanvas(width, height);
const ctx = canvas.getContext('2d');

// 3. On dessine le tableau blanc et le texte
ctx.fillStyle = '#FDF5E6'; // Fond beige clair
ctx.fillRect(0, 0, width, height);

ctx.font = 'bold 120px Arial';
ctx.fillStyle = '#000000';
ctx.textAlign = 'center';
ctx.textBaseline = 'middle';

// On écrit le texte au centre
let y = height / 2 - (words.length * 80) / 2;
words.forEach(word => {
    ctx.fillText(word, width / 2, y);
    y += 160;
});

// 4. Sauvegarde de l'image
const buffer = canvas.toBuffer('image/png');
fs.writeFileSync('background.png', buffer);

console.log("Image du tableau blanc générée !");
