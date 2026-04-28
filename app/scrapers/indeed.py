# app/scrapers/indeed.py
# ============================================================
# SCRAPER INDEED COLOMBIA — REGLA DE ORO: EXPERIENCIA CERO
# ============================================================
# Hereda de BaseScraper (anti-detección, rate-limit, guardado).
# Reutiliza los filtros EXACTOS de computrabajo.py.
# ============================================================

import re
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper
from app.scrapers.computrabajo import (
    PATRONES_EXPERIENCIA_NUMERICA,
    PALABRAS_SENIOR,
    CARRERAS_UNIPAZ,
    TODAS_LAS_KEYWORDS,
    TERMINOS_BUSQUEDA,
)


class IndeedScraper(BaseScraper):
    """
    Scraper de co.indeed.com.

    ESTRATEGIA (idéntica a Computrabajo):
      1. Los TERMINOS_BUSQUEDA ya apuntan a pasantías/practicantes.
      2. Filtro 1 (INNEGOCIABLE): experiencia numérica ≥1 año → DESCARTE.
      3. Filtro 2 (INNEGOCIABLE): palabras de perfil senior → DESCARTE.
      4. Filtro 3: relevancia para carreras Unipaz → DESCARTE si no aplica.
    """

    BASE_URL = "https://co.indeed.com"
    RESULTADOS_POR_PAGINA = 10  # Indeed pagina con offset (start=0, 10, 20...)

    # ── Contrato BaseScraper ───────────────────────────────────

    def get_nombre_fuente(self) -> str:
        return 'indeed'

    def construir_url(self, termino: str, pagina: int) -> str:
        """
        Indeed usa `start` (offset) en vez de número de página:
          página 1 → start=0
          página 2 → start=10
          página 3 → start=20
        `fromage=14` limita a ofertas de los últimos 14 días.
        """
        start = max(0, (pagina - 1) * self.RESULTADOS_POR_PAGINA)
        q = quote_plus(termino)
        return (
            f"{self.BASE_URL}/jobs"
            f"?q={q}"
            f"&l=Colombia"
            f"&fromage=14"
            f"&start={start}"
        )

    def extraer_vacantes_de_pagina(self, soup: BeautifulSoup) -> list:
        """Extrae, filtra y retorna solo las vacantes aptas."""

        # Indeed renderiza tarjetas en varios contenedores posibles
        tarjetas = soup.select(
            "div.job_seen_beacon, "
            "div.tapItem, "
            "li div.cardOutline, "
            "td.resultContent"
        )

        if not tarjetas:
            self.logger.warning("  ⚠️ Sin tarjetas Indeed — HTML puede haber cambiado")
            return []

        self.logger.info(f"  🃏 {len(tarjetas)} tarjetas encontradas")

        aptas = []
        for tarjeta in tarjetas:
            try:
                vacante = self._parsear_tarjeta(tarjeta)
                if not vacante:
                    continue

                motivo = self._filtrar(vacante)

                if motivo:
                    self.vacantes_rechazadas += 1
                    self.logger.debug(f"  🚫 RECHAZADA ({motivo}): {vacante.get('titulo','')[:50]}")
                else:
                    aptas.append(vacante)
                    self.logger.info(f"  ✅ APTA: {vacante.get('titulo','')[:55]}")

            except Exception as e:
                self.logger.debug(f"  Error parseando tarjeta Indeed: {str(e)[:60]}")

        self.logger.info(f"  📊 Aptas: {len(aptas)} | Rechazadas del filtro: {self.vacantes_rechazadas}")
        return aptas

    # ── PARSEO DE TARJETA ──────────────────────────────────────

    def _parsear_tarjeta(self, tarjeta) -> dict | None:
        """Extrae los datos crudos de una tarjeta de Indeed. Sin filtros aquí."""

        # ── Título + link ──────────────────────────────────────
        titulo_elem = tarjeta.select_one(
            "h2.jobTitle a, "
            "a.jcs-JobTitle, "
            "h2 a, "
            "a[data-jk]"
        )
        if not titulo_elem:
            return None

        titulo = self.limpiar_texto(titulo_elem)
        if not titulo:
            return None

        href = titulo_elem.get('href', '')
        link = urljoin(self.BASE_URL, href) if href else None

        # ── Empresa ────────────────────────────────────────────
        empresa_elem = tarjeta.select_one(
            "span[data-testid='company-name'], "
            "span.companyName, "
            "span.company"
        )
        empresa = self.limpiar_texto(empresa_elem) or 'No especificada'

        # ── Ubicación ──────────────────────────────────────────
        ubicacion_elem = tarjeta.select_one(
            "div[data-testid='text-location'], "
            "div.companyLocation"
        )
        ubicacion = self.limpiar_texto(ubicacion_elem) or 'Colombia'

        # ── Salario ────────────────────────────────────────────
        salario_elem = tarjeta.select_one(
            "div.salary-snippet-container, "
            "div[class*='salaryOnly'], "
            "span.salary-snippet"
        )
        salario = self.limpiar_texto(salario_elem)

        # ── Modalidad ──────────────────────────────────────────
        texto_html = tarjeta.get_text().lower()
        if any(p in texto_html for p in ['remoto', 'teletrabajo', 'remote', 'home office']):
            modalidad = 'remoto'
        elif any(p in texto_html for p in ['híbrido', 'hibrido', 'hybrid']):
            modalidad = 'hibrido'
        else:
            modalidad = 'presencial'

        # ── Descripción (snippet de tarjeta) ───────────────────
        desc_elem = tarjeta.select_one(
            "div.job-snippet, "
            "div[class*='jobSnippet'], "
            "table.jobCardShelfContainer"
        )
        descripcion = self.limpiar_texto(desc_elem)

        # ── Requisitos (Indeed los mezcla en el snippet) ───────
        requisitos_items = tarjeta.select("div.job-snippet ul li")
        requisitos = '. '.join(
            self.limpiar_texto(li) for li in requisitos_items
            if self.limpiar_texto(li)
        ) if requisitos_items else None

        return {
            'titulo':          titulo,
            'empresa':         empresa,
            'salario':         salario,
            'ubicacion':       ubicacion,
            'modalidad':       modalidad,
            'descripcion':     descripcion,
            'requisitos':      requisitos,
            'link_aplicacion': link,
        }

    # ── SISTEMA DE FILTROS (idéntico a Computrabajo) ───────────

    def _filtrar(self, vacante: dict) -> str | None:
        """
        Retorna None si APROBADA, o el motivo de rechazo.

        MISMO ORDEN que Computrabajo:
          1. Experiencia numérica ≥1 año  → INNEGOCIABLE
          2. Palabras de perfil senior     → INNEGOCIABLE
          3. Relevancia para Unipaz        → Debe matchear ≥1 carrera
        """
        texto = self._texto_completo(vacante)

        # ── FILTRO 1: Experiencia numérica ─────────────────────
        for patron in PATRONES_EXPERIENCIA_NUMERICA:
            if re.search(patron, texto, re.IGNORECASE):
                return "experiencia numérica ≥1 año detectada"

        # ── FILTRO 2: Perfil senior ────────────────────────────
        for palabra in PALABRAS_SENIOR:
            if palabra in texto:
                return f"perfil senior detectado: '{palabra.strip()}'"

        # ── FILTRO 3: Relevancia Unipaz ────────────────────────
        if not self._es_relevante_unipaz(texto):
            return "no relacionada con ninguna carrera de Unipaz"

        return None

    def _texto_completo(self, vacante: dict) -> str:
        return ' '.join([
            (vacante.get('titulo')      or ''),
            (vacante.get('empresa')     or ''),
            (vacante.get('descripcion') or ''),
            (vacante.get('requisitos')  or ''),
            (vacante.get('ubicacion')   or ''),
        ]).lower()

    def _es_relevante_unipaz(self, texto: str) -> bool:
        return any(kw in texto for kw in TODAS_LAS_KEYWORDS)

    def detectar_carrera(self, vacante: dict) -> str:
        """Determina cuál carrera Unipaz es más relevante para esta vacante."""
        texto = self._texto_completo(vacante)
        puntajes = {}
        for carrera, keywords in CARRERAS_UNIPAZ.items():
            puntaje = sum(1 for kw in keywords if kw in texto)
            if puntaje > 0:
                puntajes[carrera] = puntaje
        return max(puntajes, key=puntajes.get) if puntajes else 'General'