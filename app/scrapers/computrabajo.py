# app/scrapers/computrabajo.py
# ============================================================
# SCRAPER COMPUTRABAJO — Selectores verificados con HTML real
# Versión 3.0 — Basada en inspección directa del HTML
# ============================================================

import re
import time
import random
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper



class ComputrabajoScraper(BaseScraper):

    BASE_URL = "https://co.computrabajo.com"

    PALABRAS_INCLUIR = [
    'pasantía', 'pasantia', 'práctica', 'practica',
    'junior', 'jr', 'aprendiz', 'sena', 'trainee',
    'recién egresado', 'recien egresado', 'sin experiencia',
    '0 años', '0 a 1 año', 'primer empleo', 'practicante',
    'auxiliar', 'asistente', 'entry level', 'becario',
     ]

# ── Palabras que EXCLUIR (vacantes senior/expertas) ───────────
    PALABRAS_EXCLUIR = [
    'senior', 'sr.', 'experto', 'especialista con experiencia',
    '5 años de experiencia', '6 años', '7 años', '8 años',
    '10 años', 'mínimo 5 años', 'director', 'gerente',
    'jefe de', 'líder de', 'coordinador senior',
       ]

    def get_nombre_fuente(self) -> str:
        return 'computrabajo'

    def construir_url(self, termino_busqueda: str, pagina: int) -> str:
        """
        'ingeniero sistemas' → https://co.computrabajo.com/trabajo-de-ingeniero-sistemas
        """
        termino_url = termino_busqueda.lower().strip().replace(' ', '-')
        termino_url = re.sub(r'[^a-z0-9\-]', '', termino_url)
        url = f"{self.BASE_URL}/trabajo-de-{termino_url}"
        if pagina > 1:
            url += f"?p={pagina}"
        return url

    def extraer_vacantes_de_pagina(self, soup: BeautifulSoup) -> list:
        vacantes  = []
        tarjetas  = soup.find_all('article', class_='box_offer')

        if not tarjetas:
            self.logger.warning("  ⚠️ No se encontraron tarjetas box_offer")
            return []

        self.logger.info(f"  🃏 {len(tarjetas)} tarjetas encontradas")

        aceptadas  = 0
        rechazadas = 0

        for tarjeta in tarjetas:
            try:
                vacante = self._parsear_tarjeta(tarjeta)

                if not vacante or not vacante.get('titulo'):
                    continue

                # ── Aplicar filtro de relevancia ──────────────────
                if self._es_vacante_relevante(vacante):
                    vacantes.append(vacante)
                    aceptadas += 1
                else:
                    rechazadas += 1

            except Exception as e:
                self.logger.debug(f"  Error: {str(e)[:60]}")
                continue

        self.logger.info(f"  ✅ Aceptadas: {aceptadas} | ❌ Descartadas: {rechazadas}")
        return vacantes
    def _es_vacante_relevante(self, vacante: dict) -> bool:
        '''
        Determina si una vacante es relevante para estudiantes Unipaz.

        Lógica:
        1. Si tiene palabras de INCLUIR → aceptar inmediatamente
        2. Si tiene palabras de EXCLUIR → rechazar
        3. Si no tiene ninguna señal → aceptar (puede ser junior implícito)

        Returns:
        True si la vacante es apta para estudiantes, False si no
        '''
    # Construir texto completo para analizar
        texto = ' '.join([
        (vacante.get('titulo')      or ''),
        (vacante.get('descripcion') or ''),
        (vacante.get('requisitos')  or ''),
        (vacante.get('empresa')     or ''),
    ]).lower()

    # Paso 1: ¿Tiene señales positivas de pasantía/junior?
        tiene_incluir = any(p in texto for p in self.PALABRAS_INCLUIR)
        if tiene_incluir:
            self.logger.debug(f"  ✅ ACEPTADA (señal junior): {vacante['titulo'][:40]}")
            return True

    # Paso 2: ¿Tiene señales de experiencia senior?
        tiene_excluir = any(p in texto for p in self.PALABRAS_EXCLUIR)
        if tiene_excluir:
            self.logger.debug(f"  ❌ RECHAZADA (senior): {vacante['titulo'][:40]}")
            return False

    # Paso 3: Sin señales claras → aceptar
    # (muchas vacantes no especifican nivel explícitamente)
        return True

    def _parsear_tarjeta(self, tarjeta) -> dict | None:
        """
        Extrae datos de UNA tarjeta usando los selectores exactos
        verificados con el HTML real de Computrabajo.
        
        Estructura confirmada:
        ┌─ article.box_offer
        │  ├─ h2.fs18 > a.js-o-link.fc_base     → TÍTULO + LINK
        │  ├─ p.dFlex > a.fc_base.t_ellipsis     → EMPRESA
        │  ├─ p.fs16.fc_base.mt5 > span.mr10     → UBICACIÓN
        │  └─ div.fs13.mt15 > span.dIB > i_salary → SALARIO
        """

        # ── 1. TÍTULO Y LINK ──────────────────────────────────
        # <a class="js-o-link fc_base" href="/ofertas-de-trabajo/...">
        titulo     = None
        link       = None
        titulo_elem = tarjeta.find('a', class_='js-o-link')

        if titulo_elem:
            titulo = self.limpiar_texto(titulo_elem.get_text())
            href   = titulo_elem.get('href', '')
            # El href puede ser relativo (/ofertas-de-trabajo/...) o absoluto
            if href.startswith('/'):
                link = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                link = href

        if not titulo:
            return None  # Sin título no guardamos

        # ── 2. EMPRESA ────────────────────────────────────────
        # <p class="dFlex vm_fx fs16 fc_base mt5">
        #   <a class="fc_base t_ellipsis" ...>Alianza Temporal S.A.S</a>
        # La empresa está en el <a> con AMBAS clases: fc_base Y t_ellipsis
        empresa     = 'No especificada'
        empresa_elem = tarjeta.find('a', class_=lambda c: c and 'fc_base' in c and 't_ellipsis' in c)

        if empresa_elem:
            empresa = self.limpiar_texto(empresa_elem.get_text()) or 'No especificada'

        # ── 3. UBICACIÓN ──────────────────────────────────────
        # <p class="fs16 fc_base mt5">        ← párrafo SIN clase dFlex
        #   <span class="mr10">Bogotá, D.C.</span>
        # OJO: hay DOS <p class="fs16 fc_base mt5">
        #      El primero tiene clase "dFlex" (es la empresa)
        #      El segundo NO tiene "dFlex" (es la ubicación) ← el que queremos
        ubicacion  = None
        parrafos   = tarjeta.find_all('p', class_=lambda c: c and 'fs16' in c and 'fc_base' in c and 'mt5' in c)

        for p in parrafos:
            clases = p.get('class', [])
            # Saltamos el párrafo de empresa (tiene clase 'dFlex')
            if 'dFlex' not in clases:
                span = p.find('span', class_='mr10')
                if span:
                    ubicacion = self.limpiar_texto(span.get_text())
                    break

        # ── 4. SALARIO ────────────────────────────────────────
        # <div class="fs13 mt15">
        #   <span class="dIB mr10">
        #     <span class="icon i_salary"></span>
        #     $ 2.749.997,00 (Mensual)        ← texto directo en el span padre
        #   </span>
        salario    = None
        icono_sal  = tarjeta.find('span', class_=lambda c: c and 'i_salary' in c)

        if icono_sal:
            # El texto del salario está en el contenedor del ícono (span.dIB)
            contenedor = icono_sal.parent
            if contenedor:
                # get_text() incluye el texto del ícono vacío + el salario
                # Lo limpiamos eliminando espacios extra
                texto_sal = contenedor.get_text(separator=' ', strip=True)
                # Extraer solo el valor monetario con regex
                patron = re.search(r'\$[\s\d\.,]+(Mensual|Anual|Quincenal|Diario)?', texto_sal)
                if patron:
                    salario = patron.group().strip()
                else:
                    salario = texto_sal if texto_sal else None

        # ── 5. MODALIDAD ──────────────────────────────────────
        # Inferida del texto completo de la tarjeta
        texto_total = tarjeta.get_text().lower()
        palabras_remoto  = ['remoto', 'teletrabajo', 'home office', 'trabajo en casa', 'trabajo remoto']
        palabras_hibrido = ['híbrido', 'hibrido', 'mixto', 'semipresencial']

        if any(p in texto_total for p in palabras_remoto):
            modalidad = 'remoto'
        elif any(p in texto_total for p in palabras_hibrido):
            modalidad = 'hibrido'
        else:
            modalidad = 'presencial'

        # ── 6. DESCRIPCIÓN Y REQUISITOS ───────────────────────
        # ⚠️ NO están en la tarjeta de lista
        # Solo aparecen en la página de detalle de cada vacante
        # Los obtenemos con obtener_detalle_vacante() si se necesita
        descripcion = None
        requisitos  = None

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

    def obtener_detalle_vacante(self, url: str) -> dict:
        """
        Visita la página de DETALLE de una vacante para obtener
        descripción completa y requisitos.

        ⚠️ Hace una petición HTTP extra por vacante.
           Úsalo con delay generoso para no ser bloqueado.

        Estructura del detalle (verificada):
        <div class="fs16 t_word_wrap">
            Descripción completa...
            Perfil requerido
            REQUISITOS:
            ...
        </div>
        """
        resultado = {'descripcion': None, 'requisitos': None}

        soup = self.hacer_peticion(url)
        if not soup:
            return resultado

        # Selector confirmado con el HTML real que compartiste
        desc_elem = soup.find(
            'div',
            class_=lambda c: c and 'fs16' in c and 't_word_wrap' in c
        )

        if desc_elem:
            # Preservar saltos de línea para separar secciones
            texto = desc_elem.get_text(separator='\n', strip=True)

            if texto:
                # Buscar el punto donde empiezan los requisitos
                patron_req = re.search(
                    r'(Perfil requerido|REQUISITOS:|Requerimientos|'
                    r'Te pedimos|Buscamos que|Lo que buscamos)',
                    texto,
                    re.IGNORECASE
                )

                if patron_req:
                    idx = patron_req.start()
                    resultado['descripcion'] = texto[:idx].strip()[:1000]
                    resultado['requisitos']  = texto[idx:].strip()[:1000]
                else:
                    resultado['descripcion'] = texto[:1000]

        # Pausa obligatoria después de cada detalle
        self.esperar()
        return resultado

    def ejecutar_con_detalles(self, terminos_busqueda: list,
                               max_paginas: int = 2,
                               max_detalles: int = 10) -> dict:
        """
        Versión enriquecida: primero extrae la lista y luego
        visita el detalle de las primeras N vacantes nuevas
        para obtener descripción y requisitos completos.

        Args:
            max_detalles: Máximo de páginas de detalle a visitar
                          (para no sobrecargar el servidor)
        """
        # Primero ejecutar el scraper normal de lista
        resumen = self.ejecutar(terminos_busqueda, max_paginas)

        self.logger.info(f"\n🔍 Enriqueciendo {max_detalles} vacantes con detalles...")

        try:
            # Obtener las vacantes recién guardadas sin descripción
            vacantes_sin_desc = (
                self.sb.table('vacantes')
                .select('id, titulo, link_aplicacion')
                .eq('fuente', 'computrabajo')
                .is_('descripcion', 'null')
                .limit(max_detalles)
                .execute()
            )

            for v in vacantes_sin_desc.data:
                if not v.get('link_aplicacion'):
                    continue

                self.logger.info(f"  📄 Detalle: {v['titulo'][:45]}...")

                detalle = self.obtener_detalle_vacante(v['link_aplicacion'])

                if detalle['descripcion'] or detalle['requisitos']:
                    self.sb.table('vacantes').update({
                        'descripcion': detalle['descripcion'],
                        'requisitos':  detalle['requisitos']
                    }).eq('id', v['id']).execute()

                    self.logger.info(f"  ✅ Detalle guardado")

        except Exception as e:
            self.logger.error(f"Error en detalles: {str(e)}")

        return resumen