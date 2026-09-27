"""gwangandaegyo_chocolate_experience.html + cards.js -> index.html (단일 파일, GitHub Pages 배포용)"""
from pathlib import Path

root = Path(__file__).parent
src = (root / 'gwangandaegyo_chocolate_experience.html').read_text(encoding='utf-8')
cards = (root / 'cards.js').read_text(encoding='utf-8').rstrip('\n')
out = src.replace('<script src="cards.js"></script>', '<script>\n' + cards + '\n</script>')
(root / 'index.html').write_text(out, encoding='utf-8', newline='\n')
print('index.html', len(out.encode('utf-8')), 'bytes')
