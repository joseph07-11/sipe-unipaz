# app/scrapers/base_scraper.py
# ============================================================
# CLASE BASE — Motor anti-detección + logging profesional
# ============================================================

import time
import random
import logging
import re
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

class BaseScraper(ABC):

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    ]

    def __init__(self, supabase_client, delay_min=4, delay_max=9):
        self.sb                   = supabase_client
        self.delay_min            = delay_min
        self.delay_max            = delay_max
        self.logger               = logging.getLogger(self.__class__.__name__)
        self.vacantes_encontradas = 0
        self.vacantes_guardadas   = 0
        self.vacantes_rechazadas  = 0
        self.errores              = 0
        self._peticiones          = 0

    @abstractmethod
    def get_nombre_fuente(self) -> str:
        pass

    @abstractmethod
    def construir_url(self, termino_busqueda: str, pagina: int) -> str:
        pass

    @abstractmethod
    def extraer_vacantes_de_pagina(self, soup: BeautifulSoup) -> list:
        pass

    def _get_headers(self) -> dict:
        ua = random.choice(self.USER_AGENTS)
        return {
            'User-Agent':              ua,
            'Accept':                  'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language':         'es-CO,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding':         'gzip, deflate, br',
            'Connection':              'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control':           'max-age=0',
            'Sec-Fetch-Dest':          'document',
            'Sec-Fetch-Mode':          'navigate',
            'Sec-Fetch-Site':          'none',
            'Sec-Fetch-User':          '?1',
        }

    def hacer_peticion(self, url: str, referer: str = None) -> BeautifulSoup | None:
        try:
            try:
                from curl_cffi import requests as cffi_requests
                headers = self._get_headers()
                if referer:
                    headers['Referer'] = referer
                respuesta = cffi_requests.get(
                    url, headers=headers, impersonate="chrome120", timeout=20
                )
            except ImportError:
                import requests
                session = requests.Session()
                headers = self._get_headers()
                if referer:
                    headers['Referer'] = referer
                session.headers.update(headers)
                respuesta = session.get(url, timeout=20)

            self._peticiones += 1
            self.logger.info(f"📡 [{respuesta.status_code}] {url[:70]}...")

            if respuesta.status_code == 403:
                self.logger.warning("🚫 403 — Esperando 45 segundos...")
                time.sleep(45)
                self.errores += 1
                return None

            if respuesta.status_code == 429:
                self.logger.warning("⏱️ 429 — Esperando 2 minutos...")
                time.sleep(120)
                self.errores += 1
                return None

            respuesta.raise_for_status()

            try:
                return BeautifulSoup(respuesta.text, 'lxml')
            except Exception:
                return BeautifulSoup(respuesta.text, 'html.parser')

        except Exception as e:
            self.logger.error(f"💥 Error: {str(e)[:100]}")
            self.errores += 1
            return None

    def esperar(self, larga: bool = False):
        segundos = random.uniform(15, 25) if larga else random.uniform(self.delay_min, self.delay_max)
        self.logger.info(f"⏳ Esperando {segundos:.1f}s...")
        time.sleep(segundos)

    def limpiar_texto(self, elem) -> str | None:
        if elem is None:
            return None
        texto = elem.get_text() if hasattr(elem, 'get_text') else str(elem)
        resultado = ' '.join(texto.strip().split())
        return resultado if resultado else None

    def vacante_ya_existe(self, titulo: str, empresa: str) -> bool:
        try:
            r = (self.sb.table('vacantes')
                 .select('id')
                 .eq('titulo', titulo)
                 .eq('empresa', empresa)
                 .execute())
            return len(r.data) > 0
        except Exception:
            return False

    def guardar_vacante(self, vacante: dict) -> bool:
        titulo  = (vacante.get('titulo') or '').strip()
        empresa = (vacante.get('empresa') or 'No especificada').strip()

        if not titulo:
            return False

        if self.vacante_ya_existe(titulo, empresa):
            self.logger.info(f"⏭️  Duplicada: '{titulo[:45]}'")
            return False

        try:
            vacante['fuente'] = self.get_nombre_fuente()
            vacante['activa'] = True

            # Truncar campos largos
            for campo, limite in [('titulo', 250), ('empresa', 145),
                                   ('ubicacion', 145), ('salario', 95),
                                   ('link_aplicacion', 500)]:
                if vacante.get(campo):
                    vacante[campo] = vacante[campo][:limite]

            self.sb.table('vacantes').insert(vacante).execute()
            self.vacantes_guardadas += 1
            self.logger.info(f"✅ GUARDADA: '{titulo[:45]}' — {empresa[:30]}")
            return True

        except Exception as e:
            self.logger.error(f"💾 Error guardando '{titulo[:40]}': {str(e)}")
            self.errores += 1
            return False

    def ejecutar(self, terminos_busqueda: list, max_paginas: int = 3) -> dict:
        inicio = datetime.now()
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🤖 INICIANDO: {self.get_nombre_fuente().upper()}")
        self.logger.info(f"🔍 Términos: {terminos_busqueda}")
        self.logger.info(f"{'='*60}")

        url_anterior = None

        for i, termino in enumerate(terminos_busqueda):
            self.logger.info(f"\n📌 [{i+1}/{len(terminos_busqueda)}] '{termino}'")

            for pagina in range(1, max_paginas + 1):
                self.logger.info(f"  📄 Página {pagina}/{max_paginas}")

                url  = self.construir_url(termino, pagina)
                soup = self.hacer_peticion(url, referer=url_anterior)
                url_anterior = url

                if soup is None:
                    self.logger.warning("  ⚠️ Sin respuesta, saltando...")
                    break

                vacantes_pagina = self.extraer_vacantes_de_pagina(soup)
                self.vacantes_encontradas += len(vacantes_pagina)

                if not vacantes_pagina:
                    self.logger.info("  📭 Sin resultados, siguiente término.")
                    break

                for v in vacantes_pagina:
                    self.guardar_vacante(v)

                if pagina < max_paginas:
                    self.esperar()

            if i < len(terminos_busqueda) - 1:
                self.esperar(larga=True)

        duracion = (datetime.now() - inicio).seconds
        resumen  = {
            'fuente':               self.get_nombre_fuente(),
            'vacantes_encontradas': self.vacantes_encontradas,
            'vacantes_guardadas':   self.vacantes_guardadas,
            'vacantes_rechazadas':  self.vacantes_rechazadas,
            'errores':              self.errores,
            'duracion_segundos':    duracion,
        }

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🏁 FINALIZADO")
        self.logger.info(f"📊 Encontradas en HTML: {self.vacantes_encontradas}")
        self.logger.info(f"✅ Guardadas en BD:     {self.vacantes_guardadas}")
        self.logger.info(f"🚫 Rechazadas filtro:   {self.vacantes_rechazadas}")
        self.logger.info(f"❌ Errores:             {self.errores}")
        self.logger.info(f"⏱️  Duración:            {duracion}s")

        return resumen