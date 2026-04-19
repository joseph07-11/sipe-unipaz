# ejecutar_scraper.py — Versión 3.0
import os, sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / '.env')
sys.path.insert(0, str(BASE_DIR))

from supabase import create_client
from app.scrapers.computrabajo import ComputrabajoScraper

def main():
    print("=" * 60)
    print("  🤖 SIPE — Motor de Scraping v3.0")
    print("  🛡️  Selectores verificados con HTML real")
    print("=" * 60)

    sb = create_client(
        os.environ.get('SUPABASE_URL'),
        os.environ.get('SUPABASE_KEY')
    )
    print("✅ Conectado a Supabase\n")

    TERMINOS = [
        'Programador',
        'Veterinario',
        'Zootecnista',
        'Agronomía',
        'Proyectista Civil',
    ]

    scraper = ComputrabajoScraper(
        supabase_client=sb,
        delay_min=4,
        delay_max=8
    )

    print("Elige modo de ejecución:")
    print("  1 → Solo lista (rápido, sin descripción)")
    print("  2 → Lista + detalles (lento, descripción completa)")
    modo = input("Opción (1/2): ").strip()

    if modo == '2':
        print("\n⚠️  Modo enriquecido: visitará el detalle de cada vacante.")
        print("    Esto es más lento pero obtiene descripción y requisitos.\n")
        resumen = scraper.ejecutar_con_detalles(
            terminos_busqueda=TERMINOS,
            max_paginas=2,
            max_detalles=15  # Máximo 15 páginas de detalle
        )
    else:
        resumen = scraper.ejecutar(
            terminos_busqueda=TERMINOS,
            max_paginas=2
        )

    print("\n" + "=" * 60)
    print("  📊 RESUMEN FINAL")
    print("=" * 60)
    print(f"  Encontradas: {resumen['vacantes_encontradas']}")
    print(f"  ✅ Guardadas:  {resumen['vacantes_guardadas']} nuevas")
    print(f"  ⏭️  Duplicadas: {resumen['vacantes_encontradas'] - resumen['vacantes_guardadas']}")
    print(f"  ❌ Errores:    {resumen['errores']}")
    print(f"  ⏱️  Duración:   {resumen['duracion_segundos']}s")
    print("=" * 60)

if __name__ == '__main__':
    main()