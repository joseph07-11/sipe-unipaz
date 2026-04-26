# app/scrapers/computrabajo.py
# ============================================================
# SCRAPER COMPUTRABAJO — REGLA DE ORO: EXPERIENCIA CERO
# ============================================================
# FILOSOFÍA:
#   • Los TÉRMINOS DE BÚSQUEDA ya apuntan a pasantías/trainee.
#   • Filtro 1 (INNEGOCIABLE): cualquier mención de ≥1 año → descarte.
#   • Filtro 2: debe ser relevante para alguna carrera de Unipaz.
#   • Resultado: solo vacantes reales para recién egresados.
# ============================================================

import re
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper
from app.config import CARRERAS_KEYWORDS


# ══════════════════════════════════════════════════════════════
# TÉRMINOS DE BÚSQUEDA — Directamente orientados a sin experiencia
# Estas palabras se ENVÍAN a Computrabajo como query.
# Buscar por cargo genérico trae basura senior → NUNCA hacer eso.
# ══════════════════════════════════════════════════════════════

TERMINOS_BUSQUEDA = [
    # ── Pasantías / prácticas directas ───────────────────────
    'pasantia ingenieria',
    'pasantia sistemas',
    'pasantia ambiental',
    'pasantia agroindustrial',
    'pasantia veterinaria',
    'pasantia trabajo social',
    'pasantia comunicacion social',
    'pasantia derecho',
    'pasantia quimica',
    'pasantia turismo',
    'pasantia agronomo',
    'pasantia produccion',

    # ── Practicantes ──────────────────────────────────────────
    'practicante ingenieria',
    'practicante sistemas',
    'practicante administrativo',
    'practicante ambiental',
    'practicante hse',
    'practicante sst',
    'practicante veterinaria',
    'practicante juridico',
    'practicante comunicaciones',
    'practicante trabajo social',
    'practicante agroindustrial',

    # ── Aprendiz SENA ─────────────────────────────────────────
    'aprendiz sena sistemas',
    'aprendiz sena administrativo',
    'aprendiz sena ambiental',
    'aprendiz sena produccion',

    # ── Trainee / primer empleo ───────────────────────────────
    'trainee ingenieria colombia',
    'trainee sistemas colombia',
    'junior sin experiencia sistemas',
    'junior sin experiencia ingenieria',
    'primer empleo ingenieria',
    'primer empleo administracion',
    'recien egresado ingenieria',
    'recien egresado sistemas',
]


# ══════════════════════════════════════════════════════════════
# PATRONES DE RECHAZO — Experiencia numérica (INNEGOCIABLE)
# Si se detecta CUALQUIERA → vacante descartada sin excepción.
# ══════════════════════════════════════════════════════════════

PATRONES_EXPERIENCIA_NUMERICA = [
    # "1 año de experiencia", "2 años", "3+ años", etc.
    r'\b([1-9]|1[0-9]|20)\s*a[ñn]os?\s*(de\s*)?(experiencia|exp\.?)',
    r'experiencia\s*(de\s*|mínima?\s*de\s*|minima?\s*de\s*)?([1-9]|1[0-9])\s*a[ñn]os?',
    r'mínimo\s*([1-9]|1[0-9])\s*a[ñn]os?',
    r'minimo\s*([1-9]|1[0-9])\s*a[ñn]os?',
    r'([1-9]|1[0-9])\+?\s*years?\s*of\s*experience',
    r'\b([1-9]|1[0-9])\s*a[ñn]os?\s*de\s*exp\b',
    # "experiencia: 2 años" o "exp. mínima 3 años"
    r'exp\.?\s*:?\s*([1-9]|1[0-9])\s*a[ñn]os?',
    # Rangos como "1 a 3 años", "2 - 5 años"
    r'\b[1-9]\s*[-–a]\s*[0-9]+\s*a[ñn]os?\s*(de\s*)?exp',
]

# Palabras que confirman perfil SENIOR → descarte inmediato
PALABRAS_SENIOR = [
    ' senior ', ' sr. ', ' sr ', 'líder técnico', 'lider tecnico',
    'arquitecto de software', 'director de ', 'gerente de ', 'jefe de ',
    'coordinador senior', 'consultor senior', '5+ años', '5 o más años',
    'experto con', 'especialista con experiencia',
]
TERMINOS_BUSQUEDA = [
    'pasantia ingenieria',
    'practicante sistemas',
    'aprendiz sena',
    'practicante administrativo',
    'trainee colombia',
    'practicante ambiental',
    'auxiliar juridico sin experiencia',
    'desarrollador junior sin experiencia',
    'practicante veterinaria',
    'practicante agroindustrial',
]


# ══════════════════════════════════════════════════════════════
# PALABRAS QUE CONFIRMAN "SIN EXPERIENCIA"
# Si alguna aparece → vacante pre-aprobada (sigue al filtro Unipaz)
# ══════════════════════════════════════════════════════════════

PALABRAS_SIN_EXPERIENCIA = [
    'sin experiencia', 'sin exp', '0 años', 'no requiere experiencia',
    'no se requiere experiencia', 'primer empleo', 'primera experiencia',
    'recién egresado', 'recien egresado', 'recién graduado', 'recien graduado',
    'pasantía', 'pasantia', 'práctica empresarial', 'practica empresarial',
    'practicante', 'aprendiz', 'sena', 'trainee', 'becario',
    'entry level', 'nivel inicial', 'estudiante universitario',
    'estudiantes de últimos semestres', 'últimos semestres',
    'trabajo de grado', 'tesis de grado', 'auxiliar junior',
    'asistente junior', 'recién egresado', 'junior recién',
]


# ══════════════════════════════════════════════════════════════
# CARRERAS UNIPAZ — Keywords por programa académico (Fuente: web oficial)
# ══════════════════════════════════════════════════════════════

CARRERAS_UNIPAZ = {

    # ── Escuela de Ciencias ───────────────────────────────────
    'Administración de Negocios Internacionales': [
        'negocios internacionales', 'comercio exterior', 'comercio internacional',
        'importaciones', 'exportaciones', 'aduanas', 'logística internacional',
        'administración', 'administrativo', 'gestión empresarial',
        'relaciones comerciales', 'mercadeo', 'marketing',
        'finanzas', 'contabilidad', 'asistente administrativo',
        'auxiliar administrativo', 'auxiliar contable',
    ],
    'Ingeniería Informática': [
        'informática', 'sistemas', 'software', 'programador', 'desarrollador',
        'python', 'java', 'javascript', 'typescript', 'react', 'angular',
        'node', 'php', 'web', 'base de datos', 'sql', 'mysql', 'postgresql',
        'redes', 'soporte técnico', 'soporte ti', 'tecnología', 'ti',
        'ciberseguridad', 'cloud', 'devops', 'frontend', 'backend',
        'fullstack', 'análisis de datos', 'inteligencia artificial',
        'machine learning', 'data science', 'automatización', 'erp',
        'helpdesk', 'mesa de ayuda', 'soporte de sistemas',
    ],
    'Licenciatura en Artes': [
        'artes', 'arte', 'diseño', 'diseñador', 'ilustración',
        'fotografía', 'video', 'producción audiovisual', 'animación',
        'docente de artes', 'educación artística', 'patrimonio cultural',
        'museología', 'curaduría', 'gestión cultural', 'diseño gráfico',
    ],
    'Química': [
        'química', 'laboratorio', 'análisis químico', 'control de calidad',
        'fisicoquímica', 'bromatología', 'microbiología', 'bioquímica',
        'industria química', 'petroquímica', 'farmacéutica',
        'metrología', 'normas iso', 'buenas prácticas de manufactura',
        'auxiliar de laboratorio', 'técnico de laboratorio',
    ],

    # ── Escuela de Ciencias Sociales ─────────────────────────
    'Comunicación Social': [
        'comunicación', 'comunicador', 'periodismo', 'periodista',
        'community manager', 'redes sociales', 'contenido digital',
        'relaciones públicas', 'prensa', 'medios de comunicación',
        'redactor', 'editor', 'locutor', 'producción de contenido',
        'marketing digital', 'copywriting', 'comunicación organizacional',
        'creación de contenido', 'social media',
    ],
    'Trabajo Social': [
        'trabajo social', 'trabajador social', 'bienestar social',
        'gestión social', 'desarrollo comunitario', 'intervención social',
        'psicosocial', 'atención a víctimas', 'fundación', 'ong',
        'inclusión social', 'políticas sociales', 'asistencia social',
        'promotor social', 'gestor comunitario',
    ],
    'Derecho': [
        'derecho', 'abogado', 'jurídico', 'legal', 'litigio',
        'contratos', 'consultor legal', 'asesor jurídico', 'notaría',
        'juzgado', 'fiscalía', 'procuraduría', 'defensoría',
        'legislación', 'normatividad', 'compliance', 'auxiliar jurídico',
    ],

    # ── Escuela Ingeniería Agroindustrial ─────────────────────
    'Ingeniería Agroindustrial': [
        'agroindustrial', 'agroindustria', 'alimentos', 'procesamiento de alimentos',
        'inocuidad', 'buenas prácticas', 'bpm', 'haccp', 'invima',
        'planta de alimentos', 'control de calidad alimentos',
        'tecnología de alimentos', 'industria alimentaria',
        'bromatólogo', 'inspector de alimentos',
    ],
    'Tecnología en Procesamiento de Alimentos': [
        'procesamiento de alimentos', 'tecnólogo alimentos', 'planta de producción',
        'producción alimentos', 'control calidad alimentos',
        'operario de planta', 'manufactura alimentos', 'operario alimentos',
    ],
    'Profesional en Turismo': [
        'turismo', 'turista', 'hotelería', 'hotel', 'agencia de viajes',
        'guía turístico', 'ecoturismo', 'operador turístico',
        'recepcionista', 'hospitalidad', 'gestión hotelera',
        'asistente de viajes', 'reservas',
    ],

    # ── Escuela Ingeniería Agronómica ─────────────────────────
    'Ingeniería Agronómica': [
        'agronomía', 'agronómica', 'agrónomo', 'cultivos', 'cosecha',
        'suelos', 'fertilizantes', 'agroquímicos', 'agricultura',
        'producción agrícola', 'campo', 'finca', 'extensión agrícola',
        'sanidad vegetal', 'fitosanitario', 'semillas', 'viveros',
        'asistente agronómico', 'auxiliar agronómico',
    ],

    # ── Escuela Ingeniería Ambiental y de Saneamiento ─────────
    'Ingeniería Ambiental y de Saneamiento': [
        'ambiental', 'medio ambiente', 'saneamiento', 'agua potable',
        'residuos', 'vertimientos', 'emisiones', 'iso 14001',
        'gestión ambiental', 'impacto ambiental', 'corporación ambiental',
        'corpoboyacá', 'corpamag', 'cdmb', 'car', 'anla',
        'tratamiento de aguas', 'reciclaje', 'sostenibilidad',
        'asistente ambiental', 'auxiliar ambiental',
    ],
    'Ingeniería Civil': [
        'civil', 'construcción', 'obras', 'estructuras', 'diseño civil',
        'topografía', 'interventoría', 'pavimentos', 'geotecnia',
        'hidráulica', 'vías', 'infraestructura', 'autocad', 'revit',
        'residente de obra', 'inspector de obras', 'auxiliar de obras',
    ],
    'Tecnología en Obras Civiles': [
        'obras civiles', 'tecnólogo civil', 'inspector de obra',
        'residente de obra', 'maestro de obra', 'auxiliar de obra',
        'construcción', 'infraestructura civil',
    ],

    # ── Escuela Ingeniería de Producción ─────────────────────
    'Ingeniería de Producción': [
        'producción', 'manufactura', 'planta de producción', 'operaciones',
        'lean manufacturing', 'six sigma', 'mejora continua', 'kaizen',
        'logística', 'cadena de suministro', 'supply chain', 'inventarios',
        'planificación de producción', 'mantenimiento industrial',
        'auxiliar de producción', 'operario industrial',
    ],
    'Ingeniería en Seguridad y Salud en el Trabajo': [
        'seguridad y salud', 'sst', 'hse', 'salud ocupacional',
        'seguridad industrial', 'riesgos laborales', 'sg-sst',
        'copasst', 'arl', 'inspector hse', 'técnico sst',
        'prevención de riesgos', 'higiene industrial', 'ergonomía',
        'auxiliar sst', 'asistente hse',
    ],
    'Tecnología en Seguridad y Salud en el Trabajo': [
        'sst', 'hse', 'salud ocupacional', 'seguridad industrial',
        'tecnólogo sst', 'riesgos laborales', 'sg-sst',
        'inspector sst', 'auxiliar sst',
    ],
    'Tecnología en Operación de Sistemas Electromécanicos': [
        'electromecánico', 'electromecánica', 'mantenimiento eléctrico',
        'mantenimiento mecánico', 'automatización', 'plc',
        'instrumentación', 'electricista', 'mecatrónica',
        'sistemas electromécanicos', 'plantas industriales',
        'técnico electromecánico', 'auxiliar de mantenimiento',
    ],

    # ── Escuela de Medicina Veterinaria ──────────────────────
    'Medicina Veterinaria y Zootecnia': [
        'veterinaria', 'veterinario', 'zootecnia', 'zootecnista',
        'medicina veterinaria', 'animales', 'ganado', 'bovinos',
        'porcinos', 'avicultura', 'clínica veterinaria', 'sanidad animal',
        'producción animal', 'finca ganadera', 'inocuidad pecuaria',
        'auxiliar veterinario', 'asistente veterinario',
    ],
}

# Lista plana de todas las keywords para búsqueda rápida
TODAS_LAS_KEYWORDS = [kw for kws in CARRERAS_UNIPAZ.values() for kw in kws]


class ComputrabajoScraper(BaseScraper):
    """
    Scraper de Computrabajo — REGLA DE ORO: Solo Experiencia Cero.

    ESTRATEGIA:
      1. Los términos de búsqueda YA SON sobre pasantías/practicantes
         (en vez de cargos genéricos que mezclan todos los niveles).
      2. Filtro 1 (innegociable): Detección de experiencia numérica ≥1 año → DESCARTE.
      3. Filtro 2 (innegociable): Palabras senior → DESCARTE.
      4. Filtro 3: Relevancia para carreras Unipaz → DESCARTE si no aplica.
      5. Solo se guarda lo que pase los 3 filtros.
    """

    BASE_URL = "https://co.computrabajo.com"

    def get_nombre_fuente(self) -> str:
        return 'computrabajo'

    def construir_url(self, termino: str, pagina: int) -> str:
        slug = re.sub(r'[^a-z0-9\-]', '', termino.lower().strip().replace(' ', '-'))
        url = f"{self.BASE_URL}/trabajo-de-{slug}"
        if pagina > 1:
            url += f"?p={pagina}"
        return url

    # ── EXTRACCIÓN ────────────────────────────────────────────

    def extraer_vacantes_de_pagina(self, soup: BeautifulSoup) -> list:
        tarjetas = soup.find_all('article', class_='box_offer')

        if not tarjetas:
            self.logger.warning("  ⚠️ Sin tarjetas — HTML puede haber cambiado")
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
                self.logger.debug(f"  Error parseando tarjeta: {str(e)[:60]}")

        self.logger.info(f"  📊 Aptas: {len(aptas)} | Rechazadas del filtro: {self.vacantes_rechazadas}")
        return aptas

    def _parsear_tarjeta(self, tarjeta) -> dict | None:
        """Extrae los datos crudos de una tarjeta de Computrabajo. Sin filtros aquí."""

        # ── Título ────────────────────────────────────────────
        titulo_elem = tarjeta.find('a', class_='js-o-link')
        titulo = self.limpiar_texto(titulo_elem)
        if not titulo:
            return None

        # ── Link ──────────────────────────────────────────────
        link = None
        if titulo_elem and titulo_elem.get('href'):
            href = titulo_elem['href']
            link = f"{self.BASE_URL}{href}" if href.startswith('/') else href

        # ── Empresa ───────────────────────────────────────────
        empresa_elem = tarjeta.find('a', class_=lambda c: c and 'fc_base' in c and 't_ellipsis' in c)
        empresa = self.limpiar_texto(empresa_elem) or 'No especificada'

        # ── Ubicación ─────────────────────────────────────────
        ubicacion = None
        for p in tarjeta.find_all('p', class_=lambda c: c and 'fs16' in c and 'fc_base' in c and 'mt5' in c):
            if 'dFlex' not in (p.get('class') or []):
                span = p.find('span', class_='mr10')
                if span:
                    ubicacion = self.limpiar_texto(span)
                    break

        # ── Salario ───────────────────────────────────────────
        salario = None
        icono = tarjeta.find('span', class_=lambda c: c and 'i_salary' in c)
        if icono and icono.parent:
            texto_sal = icono.parent.get_text(separator=' ', strip=True)
            patron = re.search(r'\$[\s\d\.,]+(Mensual|Anual|Quincenal|Diario)?', texto_sal)
            salario = patron.group().strip() if patron else None

        # ── Modalidad ─────────────────────────────────────────
        texto_html = tarjeta.get_text().lower()
        if any(p in texto_html for p in ['remoto', 'teletrabajo', 'home office', 'trabajo en casa']):
            modalidad = 'remoto'
        elif any(p in texto_html for p in ['híbrido', 'hibrido', 'mixto']):
            modalidad = 'hibrido'
        else:
            modalidad = 'presencial'

        return {
            'titulo':          titulo,
            'empresa':         empresa,
            'salario':         salario,
            'ubicacion':       ubicacion,
            'modalidad':       modalidad,
            'descripcion':     None,
            'requisitos':      None,
            'link_aplicacion': link,
        }

    # ── SISTEMA DE FILTROS ────────────────────────────────────

    def _filtrar(self, vacante: dict) -> str | None:
        """
        Sistema de filtros en cascada. Retorna None si APROBADA, o el motivo si RECHAZADA.

        ORDEN (de mayor a menor prioridad):
          1. Experiencia numérica ≥1 año  → INNEGOCIABLE
          2. Palabras de perfil senior     → INNEGOCIABLE
          3. Relevancia para Unipaz        → Debe matchear al menos 1 carrera
        """
        texto = self._texto_completo(vacante)

        # ── FILTRO 1: Experiencia numérica — SIN EXCEPCIÓN ────
        for patron in PATRONES_EXPERIENCIA_NUMERICA:
            if re.search(patron, texto, re.IGNORECASE):
                return "experiencia numérica ≥1 año detectada"

        # ── FILTRO 2: Palabras de perfil SENIOR ───────────────
        for palabra in PALABRAS_SENIOR:
            if palabra in texto:
                return f"perfil senior detectado: '{palabra.strip()}'"

        # ── FILTRO 3: Relevancia para carreras Unipaz ─────────
        if not self._es_relevante_unipaz(texto):
            return "no relacionada con ninguna carrera de Unipaz"

        # ── APROBADA ──────────────────────────────────────────
        return None

    def _texto_completo(self, vacante: dict) -> str:
        """Concatena todos los campos textuales en minúsculas para análisis."""
        return ' '.join([
            (vacante.get('titulo')      or ''),
            (vacante.get('empresa')     or ''),
            (vacante.get('descripcion') or ''),
            (vacante.get('requisitos')  or ''),
            (vacante.get('ubicacion')   or ''),
        ]).lower()

    def _es_relevante_unipaz(self, texto: str) -> bool:
        """Retorna True si el texto contiene al menos 1 keyword de alguna carrera Unipaz."""
        return any(kw in texto for kw in TODAS_LAS_KEYWORDS)

    def detectar_carrera(self, vacante: dict) -> str:
        """
        Determina cuál carrera Unipaz es más relevante para esta vacante.
        Útil para mostrar en la UI o para estadísticas.
        """
        texto = self._texto_completo(vacante)
        puntajes = {}

        for carrera, keywords in CARRERAS_UNIPAZ.items():
            puntaje = sum(1 for kw in keywords if kw in texto)
            if puntaje > 0:
                puntajes[carrera] = puntaje

        if not puntajes:
            return 'General'

        return max(puntajes, key=puntajes.get)