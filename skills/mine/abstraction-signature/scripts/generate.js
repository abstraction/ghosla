#!/usr/bin/env node

const figlet = require('figlet');
const fs = require('fs');
const { program } = require('commander');

const charmap = {
    ' ': [0,0,0,0],
    '▀': [1,1,0,0],
    '▄': [0,0,1,1],
    '█': [1,1,1,1],
    '▌': [1,0,1,0],
    '▐': [0,1,0,1],
    '▖': [0,0,1,0],
    '▗': [0,0,0,1],
    '▘': [1,0,0,0],
    '▝': [0,1,0,0],
    '▞': [0,1,1,0],
    '▚': [1,0,0,1],
    '▛': [1,1,1,0],
    '▜': [1,1,0,1],
    '▙': [1,0,1,1],
    '▟': [0,1,1,1]
};

function generateSvgFile(grid, pixelW, pixelH, width, height, color, outPath) {
    const svg = [];
    svg.push(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" shape-rendering="crispEdges">`);
    svg.push(`  <style> .pixel { fill: ${color}; } </style>`);
    
    for (let y = 0; y < grid.length; y++) {
        const row = grid[y];
        for (let x = 0; x < row.length; x++) {
            if (row[x]) {
                svg.push(`  <rect class="pixel" x="${x * pixelW}" y="${y * pixelH}" width="${pixelW + 0.2}" height="${pixelH + 0.2}" />`);
            }
        }
    }
    
    svg.push('</svg>');
    
    fs.writeFileSync(outPath, svg.join('\n'));
    console.log(`Generated ${outPath} successfully.`);
}

function generateSvg(art, pixelW, pixelH, outPrefix) {
    const lines = art.split('\n');
    const grid = [];
    
    for (const line of lines) {
        if (!line.trim()) continue; // Skip empty trailing lines
        const row1 = [];
        const row2 = [];
        for (const char of line) {
            const [tl, tr, bl, br] = charmap[char] || [0,0,0,0];
            row1.push(tl, tr);
            row2.push(bl, br);
        }
        grid.push(row1);
        grid.push(row2);
    }
    
    const height = grid.length * pixelH;
    let maxLen = 0;
    for (const r of grid) {
        if (r.length > maxLen) maxLen = r.length;
    }
    const width = maxLen * pixelW;
    
    const prefix = outPrefix.endsWith('.svg') ? outPrefix.slice(0, -4) : outPrefix;
    generateSvgFile(grid, pixelW, pixelH, width, height, '#1F2328', `${prefix}-light.svg`);
    generateSvgFile(grid, pixelW, pixelH, width, height, '#e6edf3', `${prefix}-dark.svg`);
}

program
  .option('-t, --text <string>', 'Text to generate', 'abstraction')
  .option('-v, --variant <string>', 'Variant (default, compact, legible)', 'default')
  .option('-o, --out <string>', 'Output file prefix', 'logo')
  .parse(process.argv);

const options = program.opts();
const text = options.text;

let fontName = 'miniwi';
let pixelW = 10;
let pixelH = 10;

if (options.variant === 'compact') {
    fontName = 'miniwi';
    pixelW = 6;
    pixelH = 12;
} else if (options.variant === 'legible') {
    fontName = 'Small Block';
    pixelW = 8;
    pixelH = 8;
}

figlet.text(text, { font: fontName }, function(err, data) {
    if (err) {
        console.error('Something went wrong...');
        console.dir(err);
        return;
    }
    generateSvg(data, pixelW, pixelH, options.out);
});
