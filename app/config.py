# app/config.py
# ============================================================
# FUENTE ÚNICA DE VERDAD — Carreras Unipaz + Keywords
# Importar desde aquí en: scrapers, rutas, templates
# ============================================================

CARRERAS_KEYWORDS = {

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