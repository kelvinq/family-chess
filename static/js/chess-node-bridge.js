// Simple bridge module to make chess.js work with Node.js
const fs = require('fs');
const path = require('path');

// Read the chess.js file
const chessJsPath = path.join(__dirname, 'chess.js');
const chessJsContent = fs.readFileSync(chessJsPath, 'utf8');

// Create a module context and evaluate the chess.js code
const moduleContext = {};
const moduleFunction = new Function('exports', 'module', chessJsContent);
moduleFunction(moduleContext, { exports: moduleContext });

// Export the Chess constructor
module.exports = { Chess: moduleContext.Chess };