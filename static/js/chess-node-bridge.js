// Simple bridge module to make chess.js work with Node.js
const fs = require('fs');
const path = require('path');

// Read the chess.js file - make sure to handle absolute path
let chessJsPath;
try {
    chessJsPath = path.join(__dirname, 'chess.js');
    // Test if file exists at this path
    fs.accessSync(chessJsPath, fs.constants.R_OK);
} catch (error) {
    // Fallback: try to find the file relative to the current file
    chessJsPath = path.join(path.dirname(process.argv[1]), 'chess.js');
    // If that fails too, try absolute path from script directory
    if (!fs.existsSync(chessJsPath)) {
        const scriptDir = path.dirname(process.argv[1]);
        chessJsPath = path.resolve(scriptDir, '..', 'static', 'js', 'chess.js');
    }
}
console.log('Loading chess.js from:', chessJsPath);
const chessJsContent = fs.readFileSync(chessJsPath, 'utf8');

// Create a module context and evaluate the chess.js code
const moduleContext = {};
const moduleFunction = new Function('exports', 'module', chessJsContent);
moduleFunction(moduleContext, { exports: moduleContext });

// Export the Chess constructor
module.exports = { Chess: moduleContext.Chess };