# app/scrapers/elempleo.py
# ============================================================
# SCRAPER ELEMPLEO.COM — REGLA DE ORO: EXPERIENCIA CERO
# ============================================================
# Portal 100% colombiano. HTML simple, sin protecciones agresivas.
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


class ElempleoScraper(BaseScraper):
    """
    Scraper de elempleo.com.

    ESTRATEGIA (idéntica a Computrabajo):
      1. Los TERMINOS_BUSQUEDA ya apuntan a pasantías/practicantes.
      2. Filtro 1 (INNEGOCIABLE): experiencia numérica ≥1 año → DESCARTE.
      3. Filtro 2 (INNEGOCIABLE): palabras de perfil senior → DESCARTE.
      4. Filtro 3: relevancia para carreras Unipaz → DESCARTE si no aplica.
    """

    BASE_URL = "https://www.elempleo.com"

    # ── Contrato BaseScraper ───────────────────────────────────

    def get_nombre_fuente(self) -> str:
        return 'elempleo'

    def construir_url(self, termino: str, pagina: int) -> str:
        """
        elempleo.com acepta búsqueda por query string:
          https://www.elempleo.com/co/ofertas-empleo/?Search={termino}&PageIndex={pagina}
        """
        q = quote_plus(termino)
        return (
            f"{self.BASE_URL}/co/ofertas-empleo/"
            f"?Search={q}"
            f"&PageIndex={pagina}"
        )

    def extraer_vacantes_de_pagina(self, soup: BeautifulSoup) -> list:
        """Extrae, filtra y retorna solo las vacantes aptas."""

        # elempleo renderiza las ofertas como <a> con clase especial
        # o como <div class="result-item"> dependiendo del layout
        tarjetas = soup.select(
            "div.result-item, "
            "article.result-item, "
            "a.offer-link, "
            "div.js-offer, "
            "div[class*='offer-item'], "
            "li.offer__item"
        )

        # Fallback: buscar contenedores genéricos con enlaces de oferta
        if not tarjetas:
            tarjetas = soup.select("a[href*='/ofertas-trabajo/'], a[href*='/ofertas-empleo/']")

        if not tarjetas:
            self.logger.warning("  ⚠️ Sin tarjetas elempleo — HTML puede haber cambiado")
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
                self.logger.debug(f"  Error parseando tarjeta elempleo: {str(e)[:60]}")

        self.logger.info(f"  📊 Aptas: {len(aptas)} | Rechazadas del filtro: {self.vacantes_rechazadas}")
        return aptas

    # ── PARSEO DE TARJETA ──────────────────────────────────────

    def _parsear_tarjeta(self, tarjeta) -> dict | None:
        """Extrae los datos crudos de una tarjeta de elempleo. Sin filtros aquí."""

        # ── Título + link ──────────────────────────────────────
        # Si la tarjeta misma es un <a>, el título está directo.
        # Si es un <div>, buscar el <a> hijo.
        if tarjeta.name == 'a':
            titulo_elem = tarjeta
            href = tarjeta.get('href', '')
        else:
            titulo_elem = tarjeta.select_one(
                "a.js-offer-title, "
                "a.offer-title, "
                "a.result-title, "
                "h2 a, h3 a, "
                "a[href*='/ofertas-trabajo/']"
            )
            href = titulo_elem.get('href', '') if titulo_elem else ''

        if not titulo_elem:
            return None

        # El título a veces está en un hijo <span> o <h2>
        titulo_inner = titulo_elem.select_one("h2, h3, span.title, span.offer-title")
        titulo = self.limpiar_texto(titulo_inner or titulo_elem)
        if not titulo:
            return None

        link = urljoin(self.BASE_URL, href) if href else None

        # ── Empresa ────────────────────────────────────────────
        empresa_elem = tarjeta.select_one(
            "span.company, "
            "a.company, "
            "p[class*='company'], "
            "span[class*='company'], "
            "div.company-name"
        )
        empresa = self.limpiar_texto(empresa_elem) or 'Empresa confidencial'

        # ── Ubicación ──────────────────────────────────────────
        ubicacion_elem = tarjeta.select_one(
            "span.city, "
            "span.location, "
            "p[class*='location'], "
            "span[class*='location'], "
            "span[class*='city']"
        )
        ubicacion = self.limpiar_texto(ubicacion_elem) or 'Colombia'

        # ── Salario ────────────────────────────────────────────
        salario_elem = tarjeta.select_one(
            "span.salary, "
            "span[class*='salary'], "
            "p[class*='salary']"
        )
        salario = self.limpiar_texto(salario_elem)
        if salario and 'convenir' in salario.lower():
            salario = 'A convenir'

        # ── Modalidad ──────────────────────────────────────────
        texto_html = tarjeta.get_text().lower()
        if any(p in texto_html for p in ['remoto', 'teletrabajo', 'home office', 'trabajo en casa']):
            modalidad = 'remoto'
        elif any(p in texto_html for p in ['híbrido', 'hibrido', 'mixto']):
            modalidad = 'hibrido'
        else:
            modalidad = 'presencial'

        # ── Descripción ────────────────────────────────────────
        desc_elem = tarjeta.select_one(
            "p.description, "
            "div.description, "
            "p[class*='description'], "
            "span[class*='description']"
        )
        descripcion = self.limpiar_texto(desc_elem)

        # ── Requisitos ─────────────────────────────────────────
        req_elem = tarjeta.select_one(
            "span.requirements, "
            "ul.requirements, "
            "div[class*='requirements']"
        )
        requisitos = self.limpiar_texto(req_elem)

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