# ejecutar_scraper.py — REGLA DE ORO: Experiencia Cero
import os, sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / '.env')
sys.path.insert(0, str(BASE_DIR))

from supabase import create_client
from app.scrapers.computrabajo import ComputrabajoScraper, TERMINOS_BUSQUEDA

def main():
    print("=" * 65)
    print("  🤖 SIPE — Motor de Scraping")
    print("  🎯 REGLA DE ORO: Solo vacantes con Experiencia CERO")
    print("  🏫 Filtrado por carreras Unipaz")
    print(f"  🔍 Total términos a buscar: {len(TERMINOS_BUSQUEDA)}")
    print("=" * 65)

    sb = create_client(
        os.environ.get('SUPABASE_URL'),
        os.environ.get('SUPABASE_SERVICE_KEY')
    )
    print("✅ Conectado a Supabase\n")

    scraper = ComputrabajoScraper(
        supabase_client=sb,
        delay_min=5,
        delay_max=10
    )

    resumen = scraper.ejecutar(
        terminos_busqueda=TERMINOS_BUSQUEDA,
        max_paginas=3
    )

    print("\n" + "=" * 65)
    print("  📊 RESUMEN FINAL")
    print("=" * 65)
    print(f"  🔍 Encontradas en HTML:   {resumen['vacantes_encontradas']}")
    print(f"  🚫 Rechazadas por filtro: {resumen['vacantes_rechazadas']}")
    print(f"  ✅ Guardadas en BD:       {resumen['vacantes_guardadas']}")
    print(f"  ❌ Errores:               {resumen['errores']}")
    print(f"  ⏱️  Duración:              {resumen['duracion_segundos']}s")
    print("=" * 65)
    if resumen['vacantes_rechazadas'] > 0:
        pct = resumen['vacantes_rechazadas'] / max(resumen['vacantes_encontradas'], 1) * 100
        print(f"\n💡 Eficiencia del filtro: {pct:.0f}% de basura eliminada")

if __name__ == '__main__':
    main()