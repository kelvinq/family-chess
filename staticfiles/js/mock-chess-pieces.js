// Mock setup for chess pieces
// This will allow us to test the interface before downloading all images
document.addEventListener('DOMContentLoaded', function() {
    const pieces = ['wP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bP', 'bR', 'bN', 'bB', 'bQ', 'bK'];
    
    // Create mock pieces
    pieces.forEach(piece => {
        const img = document.createElement('img');
        img.id = `chess-piece-${piece}`;
        img.src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="45" height="45"><circle cx="22.5" cy="22.5" r="20" stroke="black" stroke-width="1" fill="' + (piece[0] === 'w' ? 'white' : 'black') + '" /><text x="50%" y="50%" text-anchor="middle" dy=".3em" font-size="16" fill="' + (piece[0] === 'w' ? 'black' : 'white') + '">' + piece[1] + '</text></svg>';
        img.style.display = 'none';
        document.body.appendChild(img);
    });
});