# run.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

from app import create_app

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    print("=" * 50)
    print("  🚀 SIPE - Sistema de Pasantías estudiantiles")
    print("  📍 Servidor: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )