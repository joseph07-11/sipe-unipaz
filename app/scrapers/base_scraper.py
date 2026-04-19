# app/scrapers/base_scraper.py
# ============================================================
# CLASE BASE — Versión 2.0 con Anti-Detección Avanzada
# ============================================================

import time
import random
import logging
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

class BaseScraper(ABC):

    # ── Pool de User-Agents reales de Chrome/Firefox ──────────
    # Rotar entre estos hace que cada petición parezca
    # venir de un usuario diferente con un navegador diferente
    USER_AGENTS = [
        # Chrome en Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        # Firefox en Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        # Chrome en Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # Edge en Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    ]

    def __init__(self, supabase_client, delay_min=4, delay_max=9):
        self.sb                   = supabase_client
        self.delay_min            = delay_min
        self.delay_max            = delay_max
        self.logger               = logging.getLogger(self.__class__.__name__)
        self.vacantes_encontradas = 0
        self.vacantes_guardadas   = 0
        self.errores              = 0
        self._peticiones          = 0   # Contador interno de peticiones

    # ── MÉTODOS ABSTRACTOS ────────────────────────────────────

    @abstractmethod
    def get_nombre_fuente(self) -> str:
        pass

    @abstractmethod
    def construir_url(self, termino_busqueda: str, pagina: int) -> str:
        pass

    @abstractmethod
    def extraer_vacantes_de_pagina(self, soup: BeautifulSoup) -> list:
        pass

    # ── MOTOR ANTI-DETECCIÓN ──────────────────────────────────

    def _get_headers(self) -> dict:
        """
        Genera headers completos que imitan un navegador real.
        
        ¿Por qué tantos headers?
        Un navegador real envía ~15 headers en cada petición.
        Un robot básico con 'requests' envía solo 3-4.
        Esa diferencia es suficiente para ser detectado.
        """
        ua = random.choice(self.USER_AGENTS)

        # Detectar si es Firefox para ajustar headers específicos
        es_firefox = 'Firefox' in ua

        headers = {
            # Identificación del navegador
            'User-Agent': ua,

            # Qué tipos de contenido acepta
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',

            # Idioma (español de Colombia)
            'Accept-Language': 'es-CO,es;q=0.8,en-US;q=0.5,en;q=0.3',

            # Compresión aceptada
            'Accept-Encoding': 'gzip, deflate, br',

            # Mantener conexión abierta (como navegador real)
            'Connection': 'keep-alive',

            # Indica que prefiere versión HTTPS
            'Upgrade-Insecure-Requests': '1',

            # Caché
            'Cache-Control': 'max-age=0',

            # Modo de búsqueda (específico de Chrome)
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }

        # Headers adicionales específicos de Chrome (no Firefox)
        if not es_firefox:
            headers['sec-ch-ua'] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
            headers['sec-ch-ua-mobile'] = '?0'
            headers['sec-ch-ua-platform'] = '"Windows"'

        return headers

    def hacer_peticion(self, url: str, referer: str = None) -> BeautifulSoup | None:
        """
        Hace una petición HTTP con técnicas anti-detección.
        
        Args:
            url: URL a visitar
            referer: URL "de donde venimos" (simula navegación natural)
        """
        try:
            # Intentar primero con curl-cffi (más stealth)
            try:
                from curl_cffi import requests as cffi_requests

                headers = self._get_headers()
                if referer:
                    headers['Referer'] = referer

                # curl-cffi puede impersonar Chrome a nivel TLS
                respuesta = cffi_requests.get(
                    url,
                    headers=headers,
                    impersonate="chrome120",  # Imita Chrome 120 exactamente
                    timeout=20
                )

            except ImportError:
                # Fallback a requests normal si curl-cffi no está disponible
                import requests
                session = requests.Session()
                headers = self._get_headers()
                if referer:
                    headers['Referer'] = referer
                session.headers.update(headers)
                respuesta = session.get(url, timeout=20)

            self.logger.info(f"📡 [{respuesta.status_code}] {url[:70]}...")
            self._peticiones += 1

            # Si nos bloquearon
            if respuesta.status_code == 403:
                self.logger.warning("🚫 403 Forbidden — Aumentando espera...")
                # Espera larga antes de continuar (simula que el "humano" se fue)
                time.sleep(random.uniform(30, 60))
                self.errores += 1
                return None

            if respuesta.status_code == 429:
                self.logger.warning("⏱️ 429 Too Many Requests — Esperando 2 minutos...")
                time.sleep(120)
                self.errores += 1
                return None

            respuesta.raise_for_status()

            # Parsear HTML
            try:
                soup = BeautifulSoup(respuesta.text, 'lxml')
            except Exception:
                soup = BeautifulSoup(respuesta.text, 'html.parser')

            return soup

        except Exception as e:
            self.logger.error(f"💥 Error en petición: {str(e)[:100]}")
            self.errores += 1
            return None

    def esperar(self, es_pausa_larga: bool = False):
        """
        Pausa humanizada entre peticiones.
        
        ¿Por qué aleatorio?
        Un humano real no espera exactamente 3 segundos siempre.
        Varía entre 2 y 8 segundos. Los robots sí son exactos.
        Esa regularidad los delata.
        
        Args:
            es_pausa_larga: Si True, espera más (entre cambios de término)
        """
        if es_pausa_larga:
            # Entre términos de búsqueda: pausa más larga
            segundos = random.uniform(10, 20)
            self.logger.info(f"☕ Pausa larga: {segundos:.1f}s (entre términos)")
        else:
            # Entre páginas normales
            segundos = random.uniform(self.delay_min, self.delay_max)
            self.logger.info(f"⏳ Esperando {segundos:.1f}s...")

        # Micro-variaciones adicionales (más realismo)
        time.sleep(segundos + random.uniform(0, 1.5))

    def pausa_cada_n_peticiones(self, n: int = 10):
        """
        Cada N peticiones, hace una pausa larga.
        Simula que el usuario se fue a hacer otra cosa.
        """
        if self._peticiones > 0 and self._peticiones % n == 0:
            pausa = random.uniform(25, 45)
            self.logger.info(f"😴 Pausa de descanso: {pausa:.0f}s (cada {n} peticiones)")
            time.sleep(pausa)

    # ── GESTIÓN DE DATOS ──────────────────────────────────────

    def limpiar_texto(self, texto) -> str | None:
        if not texto:
            return None
        if hasattr(texto, 'get_text'):
            texto = texto.get_text()
        resultado = ' '.join(str(texto).strip().split())
        return resultado if resultado else None

    def vacante_ya_existe(self, titulo: str, empresa: str) -> bool:
        try:
            resultado = (
                self.sb.table('vacantes')
                .select('id')
                .eq('titulo', titulo)
                .eq('empresa', empresa)
                .execute()
            )
            return len(resultado.data) > 0
        except Exception:
            return False

    def guardar_vacante(self, vacante: dict) -> bool:
        titulo  = vacante.get('titulo', '').strip()
        empresa = vacante.get('empresa', 'No especificada').strip()

        if not titulo:
            return False

        if self.vacante_ya_existe(titulo, empresa):
            self.logger.info(f"⏭️  Duplicada: '{titulo[:40]}'")
            return False

        try:
            vacante['fuente'] = self.get_nombre_fuente()
            vacante['activa'] = True

            # Truncar campos muy largos para evitar errores de BD
            if vacante.get('titulo'):
                vacante['titulo'] = vacante['titulo'][:250]
            if vacante.get('empresa'):
                vacante['empresa'] = vacante['empresa'][:145]
            if vacante.get('ubicacion'):
                vacante['ubicacion'] = vacante['ubicacion'][:145]
            if vacante.get('salario'):
                vacante['salario'] = vacante['salario'][:95]

            self.sb.table('vacantes').insert(vacante).execute()
            self.vacantes_guardadas += 1
            self.logger.info(f"✅ Guardada: '{titulo[:45]}' — {empresa[:30]}")
            return True

        except Exception as e:
            self.logger.error(f"💾 Error guardando: {str(e)[:80]}")
            self.errores += 1
            return False

    # ── MOTOR PRINCIPAL ───────────────────────────────────────

    def ejecutar(self, terminos_busqueda: list, max_paginas: int = 3) -> dict:
        inicio = datetime.now()
        self.logger.info(f"🤖 INICIANDO: {self.get_nombre_fuente().upper()}")

        url_anterior = None  # Para el header Referer

        for i, termino in enumerate(terminos_busqueda):
            self.logger.info(f"\n{'='*55}")
            self.logger.info(f"🔍 [{i+1}/{len(terminos_busqueda)}] Buscando: '{termino}'")

            for pagina in range(1, max_paginas + 1):
                self.logger.info(f"  📄 Página {pagina}/{max_paginas}")

                url = self.construir_url(termino, pagina)

                # Pasar el referer para simular navegación natural
                soup = self.hacer_peticion(url, referer=url_anterior)
                url_anterior = url

                if soup is None:
                    self.logger.warning("  ⚠️ Sin respuesta, saltando página...")
                    break

                vacantes_pagina = self.extraer_vacantes_de_pagina(soup)
                self.vacantes_encontradas += len(vacantes_pagina)
                self.logger.info(f"  📋 Encontradas: {len(vacantes_pagina)}")

                if not vacantes_pagina:
                    self.logger.info("  📭 Sin más resultados.")
                    break

                for vacante in vacantes_pagina:
                    self.guardar_vacante(vacante)

                # Pausa entre páginas
                if pagina < max_paginas:
                    self.esperar()

                # Pausa de descanso cada 10 peticiones
                self.pausa_cada_n_peticiones(10)

            # Pausa larga entre términos de búsqueda
            if i < len(terminos_busqueda) - 1:
                self.esperar(es_pausa_larga=True)

        duracion = (datetime.now() - inicio).seconds
        resumen = {
            'fuente':               self.get_nombre_fuente(),
            'vacantes_encontradas': self.vacantes_encontradas,
            'vacantes_guardadas':   self.vacantes_guardadas,
            'errores':              self.errores,
            'duracion_segundos':    duracion
        }

        self.logger.info(f"\n{'='*55}")
        self.logger.info(f"🏁 FINALIZADO")
        self.logger.info(f"📊 Encontradas: {self.vacantes_encontradas}")
        self.logger.info(f"💾 Guardadas:   {self.vacantes_guardadas}")
        self.logger.info(f"❌ Errores:     {self.errores}")
        self.logger.info(f"⏱️  Duración:    {duracion}s")

        return resumen