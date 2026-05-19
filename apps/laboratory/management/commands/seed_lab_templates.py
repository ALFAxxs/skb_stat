# apps/laboratory/management/commands/seed_lab_templates.py
# PDF shablonlaridan barcha laboratoriya shablonlarini avtomatik yaratish

from django.core.management.base import BaseCommand
from apps.laboratory.models import LabTemplate, LabParameterGroup, LabParameter


TEMPLATES = [

    # ================================================================
    # 1. QONNING UMUMIY TAHLILI (BC-5000 Plus MINDRAY)
    # ================================================================
    {
        'name': "Qonning umumiy tahlili (BC-5000 Plus)",
        'category': 'general_blood',
        'description': 'Gematologik analizator BC-5000 Plus MINDRAY',
        'params': [
            {'name': 'WBS — Leykotsitlar',         'unit': '10⁹/l',   'min': 4.0,  'max': 9.0,   'sort': 1},
            {'name': 'Neu — Neytrofillar',          'unit': '%',       'min': 42,   'max': 72,    'sort': 2},
            {'name': 'Lymph — Limphotsitlar',       'unit': '%',       'min': 10,   'max': 37,    'sort': 3},
            {'name': 'Mon — Monotsitlar',           'unit': '%',       'min': 3,    'max': 11,    'sort': 4},
            {'name': 'Eos — Eozinofillar',          'unit': '%',       'min': 0.5,  'max': 5,     'sort': 5},
            {'name': 'Bas — Bazofillar',            'unit': '%',       'min': 0,    'max': 1,     'sort': 6},
            {'name': 'HGB — Gemoglobin',            'unit': 'g/l',     'min_m': 130, 'max_m': 160, 'min_f': 120, 'max_f': 140, 'sort': 7},
            {'name': 'RBC — Eritrotsitlar',         'unit': '10¹²/l',  'min_m': 4.0, 'max_m': 5.0, 'min_f': 3.9, 'max_f': 4.7, 'sort': 8},
            {'name': 'HCT — Gemotokrit',            'unit': '%',       'min_m': 42, 'max_m': 48,  'min_f': 36,  'max_f': 44,  'sort': 9},
            {'name': 'MCV — Eritrotsitlar o\'rtacha hajmi', 'unit': 'f/l', 'min': 85.0, 'max': 95.0, 'sort': 10},
            {'name': 'MCH — Gemoglobin o\'rtacha miqdori',  'unit': 'p/g', 'min': 27.0, 'max': 32.0, 'sort': 11},
            {'name': 'MCHC — Gemoglobin kontsentratsiyasi', 'unit': 'g/l', 'min': 320, 'max': 360,  'sort': 12},
            {'name': 'RDW-CV — Eritrotsitlar anizatsiyasi (Variatsiya)', 'unit': '%', 'min': 11.5, 'max': 14.5, 'sort': 13},
            {'name': 'RDW-SD — Eritrotsitlar anizatsiyasi (Standart)',   'unit': 'f/l', 'min': 35.0, 'max': 56.0, 'sort': 14},
            {'name': 'PLT — Trombotsitlar',         'unit': '10⁹/l',  'min': 120,  'max': 320,   'sort': 15},
            {'name': 'MPV — Trombotsitlar o\'rtacha hajmi', 'unit': 'f/l', 'min': 7, 'max': 11,   'sort': 16},
            {'name': 'PDW — Trombotsitlar anizatsiyasi',    'unit': '',   'min': 15,  'max': 17,   'sort': 17},
            {'name': 'PCT — Trombokrit',             'unit': '%',      'min': 0.109,'max': 0.282, 'sort': 18},
            {'name': 'COЭ (EChT) — Eritrotsitning cho\'kish tezligi', 'unit': 'mm/soat', 'min_m': 0, 'max_m': 15, 'min_f': 0, 'max_f': 20, 'sort': 19},
        ]
    },

    # ================================================================
    # 2. QONNING UMUMIY TAHLILI (BC-3000 Plus MINDRAY)
    # ================================================================
    {
        'name': "Qonning umumiy tahlili (BC-3000 Plus)",
        'category': 'general_blood',
        'description': 'Gematologik analizator BC-3000 PLUS MINDRAY',
        'params': [
            {'name': 'WBS — Leykotsitlar',         'unit': '10⁹/l',  'min': 4.0,  'max': 9.0,   'sort': 1},
            {'name': 'Lymph# — Limphotsitlar',     'unit': '10⁹/l',  'min': 0.8,  'max': 4.0,   'sort': 2},
            {'name': 'Mid# — O\'rta hajmdagi hujayralar', 'unit': '10⁹/l', 'min': 0.1, 'max': 0.9, 'sort': 3},
            {'name': 'Gran# — Granulotsitlar',     'unit': '10⁹/l',  'min': 2.0,  'max': 7.0,   'sort': 4},
            {'name': 'Lymph% — Limphotsitlar ulushi','unit': '%',     'min': 19,   'max': 39,    'sort': 5},
            {'name': 'Mid% — O\'rta hajmdagi hujayralar ulushi','unit': '%', 'min': 3.0, 'max': 11.0, 'sort': 6},
            {'name': 'Gran% — Granulotsitlar ulushi','unit': '%',     'min': 50,   'max': 70,    'sort': 7},
            {'name': 'HGB — Gemoglobin',           'unit': 'g/l',    'min_m': 130,'max_m': 160, 'min_f': 120,'max_f': 140, 'sort': 8},
            {'name': 'RBC — Eritrotsitlar',        'unit': '10¹²/l', 'min_m': 4.0,'max_m': 5.0, 'min_f': 3.9,'max_f': 4.7, 'sort': 9},
            {'name': 'HCT — Gemotokrit',           'unit': '%',      'min_m': 42, 'max_m': 48,  'min_f': 36, 'max_f': 44,  'sort': 10},
            {'name': 'MCV — Eritrotsitlar o\'rtacha hajmi','unit': 'f/l', 'min': 85.0,'max': 95.0,'sort': 11},
            {'name': 'MCH — Gemoglobin o\'rtacha miqdori','unit': 'p/g', 'min': 27.0,'max': 32.0,'sort': 12},
            {'name': 'MCHC — Gemoglobin kontsentratsiyasi','unit': 'g/l','min': 320,'max': 360,  'sort': 13},
            {'name': 'RDW-CV — Eritrotsitlar anizatsiyasi','unit': '%',  'min': 11.5,'max': 14.5,'sort': 14},
            {'name': 'RDW-SD — Eritrotsitlar anizatsiyasi (Standart)','unit': 'f/l','min': 35.0,'max': 56.0,'sort': 15},
            {'name': 'PLT — Trombotsitlar',        'unit': '10⁹/l', 'min': 120,  'max': 320,   'sort': 16},
            {'name': 'MPV — Trombotsitlar o\'rtacha hajmi','unit': 'f/l','min': 7,'max': 11,    'sort': 17},
            {'name': 'PDW — Trombotsitlar anizatsiyasi','unit': '',   'min': 15,   'max': 17,    'sort': 18},
            {'name': 'PCT — Trombokrit',            'unit': '%',     'min': 0.109,'max': 0.282, 'sort': 19},
            {'name': 'COЭ (EChT) — Eritrotsitning cho\'kish tezligi','unit': 'Mm/soat','min_m': 0,'max_m': 15,'min_f': 0,'max_f': 20,'sort': 20},
        ]
    },

    # ================================================================
    # 3. QONNING UMUMIY TAHLILI (to'liq formula)
    # ================================================================
    {
        'name': "Qonning umumiy tahlili (to'liq formula)",
        'category': 'general_blood',
        'description': 'Buyruq № 363 asosida 052-raqamli tibbiy hujjat shakli',
        'params': [
            {'name': 'Gemoglobin (HB)',             'unit': 'g/l',    'min_m': 130,'max_m': 160, 'min_f': 120,'max_f': 140, 'sort': 1},
            {'name': 'Eritrotsitlar (RBC)',         'unit': '10¹²/l', 'min_m': 4.0,'max_m': 5.0, 'min_f': 3.9,'max_f': 4.7, 'sort': 2},
            {'name': 'Rang ko\'rsatkichi',          'unit': '',       'min': 0.85, 'max': 1.05,  'sort': 3},
            {'name': 'MCV — Eritrotsitlarni o\'rtacha hajmi','unit': 'mkm³','min': 80,'max': 100,'sort': 4},
            {'name': 'MCH — 1 dona eritrotsitdagi gemoglobin','unit': 'pg','min': 30,'max': 35,  'sort': 5},
            {'name': 'MCHC — Eritrotsitdagi gemoglobin kontsentratsiyasi','unit': 'g/l','min': 320,'max': 360,'sort': 6},
            {'name': 'RDW-CV — Eritrotsitlar anizatsiyasi','unit': '%','min': 11.5,'max': 14.5,  'sort': 7},
            {'name': 'Gematokrit (HCT)',            'unit': '%',      'min_m': 35, 'max_m': 49,  'min_f': 32, 'max_f': 45,  'sort': 8},
            {'name': 'Trombotsitlar (PLT)',         'unit': '10⁹/l', 'min': 180,  'max': 320,   'sort': 9},
            {'name': 'MPV — Trombotsitlar o\'rtacha hajmi','unit': 'mkm³','min': 3.6,'max': 9.4,'sort': 10},
            {'name': 'PDW — Trombotsitlar anizatsiyasi','unit': '%',  'min': 1,    'max': 20,    'sort': 11},
            {'name': 'PCT — Trombokrit',            'unit': '%',      'min': 0.15, 'max': 0.45,  'sort': 12},
            {'name': 'Leykotsitlar (WBC)',          'unit': '10⁹/l', 'min': 4.0,  'max': 9.0,   'sort': 13},
            {'name': 'Mielotsitlar',                'unit': '%',      'min': 0,    'max': 0,     'sort': 14},
            {'name': 'Tayoqcha yadroli neytrofil',  'unit': '%',      'min': 1,    'max': 6,     'sort': 15},
            {'name': 'Segment yadroli neytrofil',   'unit': '%',      'min': 47,   'max': 72,    'sort': 16},
            {'name': 'Eozinofillar',                'unit': '%',      'min': 0.5,  'max': 5,     'sort': 17},
            {'name': 'Bazofillar',                  'unit': '%',      'min': 0,    'max': 1,     'sort': 18},
            {'name': 'Monotsitlar',                 'unit': '%',      'min': 3,    'max': 11,    'sort': 19},
            {'name': 'Limphotsitlar',               'unit': '%',      'min': 19,   'max': 37,    'sort': 20},
            {'name': 'Plazmatik xujayralar',        'unit': '%',      'sort': 21,  'type': 'text'},
            {'name': 'EChT — Eritrotsitning cho\'kish tezligi','unit': 'mm/soat','min_m': 2,'max_m': 10,'min_f': 2,'max_f': 15,'sort': 22},
        ]
    },

    # ================================================================
    # 4. QONNING BIOKIMYOVIY TAHLILI
    # ================================================================
    {
        'name': "Qonning biokimyoviy tahlili",
        'category': 'biochemistry',
        'description': 'Buyruq № 363 asosida 055-raqamli tibbiy hujjat shakli',
        'params': [
            {'name': 'Umumiy oqsil',               'unit': 'g/l',    'min': 65,   'max': 85,    'sort': 1},
            {'name': 'Albumin',                     'unit': 'g/l',    'min': 38,   'max': 51,    'sort': 2},
            {'name': 'Xolesterin (umumiy)',         'unit': 'g/l',    'min': 3.8,  'max': 6.5,   'sort': 3},
            {'name': 'Triglitseridlar',             'unit': 'mmol/l', 'min': 0.4,  'max': 1.8,   'sort': 4},
            {'name': 'B-lipoproteidlar',            'unit': '%',      'min': 31,   'max': 65,    'sort': 5},
            {'name': 'LKZ Lipoproteid kichik zichlik (ЛПНП)','unit': 'mmol/l','min': 1.55,'max': 4.26,'sort': 6},
            {'name': 'LBZ Lipoproteid baland zichlik (ЛПВП)','unit': 'mmol/l','min': 0.9,'max': 1.8,'sort': 7},
            {'name': 'Glukoza',                    'unit': 'mmol/l', 'min': 4.2,  'max': 6.4,   'sort': 8},
            {'name': 'Glikirlangan gemoglobin (HbA1C)','unit': 'nmol/sl','min': 4.5,'max': 7.0, 'sort': 9},
            {'name': 'Mochevina',                  'unit': 'mmol/l', 'min': 2.5,  'max': 8.3,   'sort': 10},
            {'name': 'Kreatinin',                  'unit': 'mkmol/l','min_m': 44, 'max_m': 115, 'min_f': 44,'max_f': 97, 'sort': 11},
            {'name': 'Siydik kislotasi',           'unit': 'mmol/l', 'min': 200,  'max': 420,   'sort': 12},
            {'name': 'Bilirubin umumiy',           'unit': 'mkmol/l','min': 3.4,  'max': 20.5,  'sort': 13},
            {'name': 'Bilirubin bog\'langan',      'unit': 'mkmol/l','min': 6.8,  'max': 15.4,  'sort': 14},
            {'name': 'Bilirubin erkin',            'unit': 'mkmol/l','min': 1.7,  'max': 17.1,  'sort': 15},
            {'name': 'ALT (Alaninaminotransferaza)','unit': 'Ed/l',  'max': 40,               'sort': 16},
            {'name': 'AST (Aspartataminotransferaza)','unit': 'Ed/l','max': 35,               'sort': 17},
            {'name': 'α-amilaza',                  'unit': 'Ed/l',   'min': 0,    'max': 220,   'sort': 18},
            {'name': 'Siydik amilazasi',           'unit': 'Ed/l',   'min': 120,  'max': 480,   'sort': 19},
            {'name': 'GGT (Gammaglutamiltransferaza)','unit': 'Ed/l','min_m': 11,'max_m': 61,  'min_f': 9,'max_f': 56,'sort': 20},
            {'name': 'IF (Ishqoriy fosfataza)',    'unit': 'Ed/l',   'min': 64,   'max': 306,   'sort': 21},
            {'name': 'Kaliy',                      'unit': 'mmol/l', 'min': 3.6,  'max': 6.3,   'sort': 22},
            {'name': 'Natriy',                     'unit': 'mmol/l', 'min': 135,  'max': 150,   'sort': 23},
            {'name': 'Xlor',                       'unit': 'mmol/l', 'min': 98,   'max': 110,   'sort': 24},
            {'name': 'Kaltsiy',                    'unit': 'mmol/l', 'min': 2.0,  'max': 2.6,   'sort': 25},
            {'name': 'Magniy',                     'unit': 'mmol/l', 'min': 0.8,  'max': 1.0,   'sort': 26},
        ]
    },

    # ================================================================
    # 5. QON ZARDOB IDA LIPOPROTEINDLAR TAHLILI
    # ================================================================
    {
        'name': "Qon zardob ida lipoproteindlar tahlili",
        'category': 'biochemistry',
        'description': 'Lipoproteindlar fraksiyasi (%)',
        'params': [
            {'name': 'Xilomikron',                 'unit': '%',      'sort': 1, 'type': 'text'},
            {'name': 'Xolesterin',                 'unit': 'g/l',    'min': 3.8, 'max': 6.5,   'sort': 2},
            {'name': 'Triglitseridlar',            'unit': 'mmol/l', 'min': 0.4, 'max': 1.8,   'sort': 3},
            {'name': 'B-lipoproteidlar',           'unit': '%',      'min': 31,  'max': 65,    'sort': 4},
            {'name': 'ЛПНП (LKZ)',                 'unit': 'mmol/l', 'min': 1.55,'max': 4.26,  'sort': 5},
            {'name': 'ЛПВП (LBZ)',                 'unit': 'mmol/l', 'min': 0.9, 'max': 1.8,   'sort': 6},
        ]
    },

    # ================================================================
    # 6. ELEKTROLITLAR
    # ================================================================
    {
        'name': "Qon biokimyoviy tahlili — Elektrolitlar",
        'category': 'biochemistry',
        'description': 'Kaliy, Natriy, Xlor, Kalsiy',
        'params': [
            {'name': 'Kaliy',   'unit': 'Mmol/l', 'min': 3.6, 'max': 6.3,  'sort': 1},
            {'name': 'Natriy',  'unit': 'Mmol/l', 'min': 130, 'max': 150,  'sort': 2},
            {'name': 'Xlor',    'unit': 'Mmol/l', 'min': 98,  'max': 110,  'sort': 3},
            {'name': 'Kalsiy',  'unit': 'Mmol/l', 'min': 2.0, 'max': 2.7,  'sort': 4},
        ]
    },

    # ================================================================
    # 7. AMILAZA ANIQLASH
    # ================================================================
    {
        'name': "Amilazani aniqlash",
        'category': 'biochemistry',
        'description': 'α-amilaza (qon) va siydik amilazasi',
        'params': [
            {'name': 'α-amilaza (qon)',   'unit': 'Ed/l', 'min': 0,   'max': 220,  'sort': 1},
            {'name': 'Siydik amilazasi',  'unit': 'Ed/l', 'min': 120, 'max': 480,  'sort': 2},
        ]
    },

    # ================================================================
    # 8. GLUKOZA BO'YICHA QON TAHLILI
    # ================================================================
    {
        'name': "Glukoza bo'yicha qon tahlili",
        'category': 'biochemistry',
        'description': 'Glukoza borligini aniqlash bo\'yicha qon tahlili (mmol/l)',
        'params': [
            {'name': 'Glukoza (och qoringa)',      'unit': 'mmol/l', 'min': 3.9, 'max': 6.1, 'sort': 1},
            {'name': 'Glukoza (1 soatdan keyin)',  'unit': 'mmol/l', 'sort': 2},
            {'name': 'Glukoza (2 soatdan keyin)',  'unit': 'mmol/l', 'max': 7.8, 'sort': 3},
        ]
    },

    # ================================================================
    # 9. INSULIN BORLIGINI ANIQLASH
    # ================================================================
    {
        'name': "Insulin borligini aniqlash bo'yicha qon tahlili",
        'category': 'hormones',
        'description': 'Insulin tahlili — μIU/ml',
        'params': [
            {'name': 'Insulin',  'unit': 'μIU/ml',
             'sort': 1,
             'name_ru': 'Инсулин',
             'normal_display': 'Bolalar<12 yosh: <10 | Kattalar: 0,7-24,9 | Diabet(1 turi): 9,0->25',
             'type': 'numeric', 'min': 0.7, 'max': 24.9},
        ]
    },

    # ================================================================
    # 10. IMMUNOXEMILUMINISTSENT QON TAHLILI
    # ================================================================
    {
        'name': "Immunoxemiluministsent qon tahlili",
        'category': 'immunology',
        'description': 'IFA — Ferritin, D-Dimer, CRP, Vitaminlar va boshqalar',
        'params': [
            {'name': 'Ferritin',          'unit': 'ng/ml',  'min_m': 30,  'max_m': 400, 'min_f': 13, 'max_f': 150, 'sort': 1},
            {'name': 'D-Dimer',           'unit': 'ng/ml',  'min': 50,    'max': 250,   'sort': 2},
            {'name': 'Prokaltsitonin',    'unit': 'pg/ml',  'min': 0.1,   'max': 0.5,   'sort': 3},
            {'name': 'C-reaktiv oqsili',  'unit': 'mg/l',   'min': 0.5,   'max': 5.0,   'sort': 4},
            {'name': 'Interleykin-6',     'unit': 'pg/ml',  'min': 0.1,   'max': 7.0,   'sort': 5},
            {'name': 'Vitamin D',         'unit': 'ng/ml',  'min': 30,    'max': 100,   'sort': 6},
            {'name': 'Troponin (cTnI)',   'unit': 'ng/ml',  'min': 0.0,   'max': 0.3,   'sort': 7},
            {'name': 'Vitamin B12',       'unit': 'pg/ml',  'min': 246,   'max': 668,   'sort': 8},
            {'name': 'CEA',               'unit': 'ng/ml',  'max': 5,     'sort': 9, 'name_ru': 'Карциноэмбриональный антиген'},
            {'name': 'AFP',               'unit': 'ng/ml',  'min': 0,     'max': 5.0,   'sort': 10},
            {'name': 'C-Peptid',          'unit': 'ng/ml',  'min': 0.3,   'max': 4.5,   'sort': 11},
            {'name': 'Insulin',           'unit': 'mkU/ml', 'min': 0.7,   'max': 9.0,   'sort': 12},
        ]
    },

    # ================================================================
    # 11. IMMUNOFERMENT QON TAHLILI (Gormonlar)
    # ================================================================
    {
        'name': "Immunoferment qon tahlili (gormonlar)",
        'category': 'hormones',
        'description': 'Buyruq № 363 asosida 056-raqamli tibbiy hujjat shakli',
        'params': [
            {'name': 'Erkin T3 (fT3)',    'unit': 'Ng/ml',  'min': 2.2, 'max': 4.8,   'sort': 1},
            {'name': 'Erkin T4 (fT4)',    'unit': 'Ng/ml',  'min': 0.8, 'max': 2.2,   'sort': 2},
            {'name': 'TTG',               'unit': 'mUl/l',  'min': 0.3, 'max': 4.0,   'sort': 3},
            {'name': 'Anti-TPO',          'unit': 'ME/ml',  'max': 30,  'sort': 4},
            {'name': 'Anti-TG',           'unit': 'ME/ml',  'min': 0,   'max': 115,   'sort': 5},
            {'name': 'Prolaktin',         'unit': 'mME/l',  'min_m': 50,'max_m': 552, 'min_f': 74,'max_f': 745,'sort': 6},
            {'name': 'Testosteron',       'unit': 'Nmol/l', 'min_m': 6.4,'max_m': 31.6,'min_f': 0.2,'max_f': 4.4,'sort': 7},
            {'name': 'PSA',               'unit': 'Ng/ml',  'max': 4,   'sort': 8, 'name_ru': 'ПСА'},
            {'name': 'Helycobacter Pylori uchun antitana (IFT)', 'unit': '', 'min': 0, 'max': 0.260, 'sort': 9},
        ]
    },

    # ================================================================
    # 12. GEPATIT B/C TAHLILI
    # ================================================================
    {
        'name': "Gepatit B va C tahlili (HBSAg, anti-HCV)",
        'category': 'serology',
        'description': 'HbsAg, Anti-HCV, Helycobacter Pylori',
        'params': [
            {'name': 'HbsAg (gepatit B virusiga antigeni)',    'unit': '', 'type': 'select', 'options': ['Manfiy', 'Musbat'], 'sort': 1},
            {'name': 'Anti-HCV (gepatit C virusiga antitana)', 'unit': '', 'type': 'select', 'options': ['Manfiy', 'Musbat'], 'sort': 2},
            {'name': 'Helycobacter Pylori uchun antitana (IFT)', 'unit': '', 'min': 0, 'max': 0.260, 'sort': 3},
        ]
    },

    # ================================================================
    # 13. GEPATIT A/B/C TAHLILI
    # ================================================================
    {
        'name': "Gepatit A, B va C tahlili",
        'category': 'serology',
        'description': 'HbsAg, Anti-HCV, IgM HAV',
        'params': [
            {'name': 'HbsAg (gepatit B virusiga antigeni)',    'unit': '', 'type': 'select', 'options': ['Manfiy', 'Musbat'], 'sort': 1},
            {'name': 'Anti-HCV (gepatit C virusiga antitana)', 'unit': '', 'type': 'select', 'options': ['Manfiy', 'Musbat'], 'sort': 2},
            {'name': 'IgM HAV (gepatit A virusiga antitana)',  'unit': '', 'type': 'select', 'options': ['Manfiy', 'Musbat'], 'sort': 3},
        ]
    },

    # ================================================================
    # 14. TORCH INFEKTSIYASI TEKSHIRUVI
    # ================================================================
    {
        'name': "TORCH infektsiyasi tekshiruvi",
        'category': 'serology',
        'description': 'Buyruq № 363 asosida 047-raqamli tibbiy hujjat shakli',
        'params': [
            {'name': 'Xlamidiya JqG',     'unit': '', 'max': 1,  'sort': 1},
            {'name': 'VPG 1,2 JqG',       'unit': '', 'max': 1,  'sort': 2},
            {'name': 'ЦМВ JqG',           'unit': '', 'max': 1,  'sort': 3},
            {'name': 'Toksoplazmoz JqG',  'unit': '', 'min': 1,  'max': 10, 'sort': 4},
            {'name': 'Mikroplazma JqG',   'unit': '', 'max': 1,  'sort': 5},
            {'name': 'Ureplazma JqG',     'unit': '', 'max': 1,  'sort': 6},
        ]
    },

    # ================================================================
    # 15. KOAGULOGRAMMA
    # ================================================================
    {
        'name': "Koagulogramma",
        'category': 'coagulation',
        'description': 'Koagulometr HUMACLOT JUNIOR NUMAN GmbH. Buyruq 057-shakli',
        'params': [
            {'name': 'PV — Protrombin vaqti',              'unit': 'sek',  'min': 12,  'max': 17,   'sort': 1},
            {'name': 'PN — Protrombin nisbati',            'unit': '',     'min': 0.9, 'max': 1.3,  'sort': 2},
            {'name': 'Protrombin Kvik bo\'yicha',          'unit': '%',    'min': 75,  'max': 110,  'sort': 3},
            {'name': 'XMM — Xalqaro me\'yerlashtirilgan',  'unit': '',     'min': 0.9, 'max': 1.1,  'sort': 4},
            {'name': 'F — Fibrinogen',                     'unit': 'g/l',  'min': 2.0, 'max': 4.0,  'sort': 5},
        ]
    },

    # ================================================================
    # 16. SIYDIK TAHLILI (umumiy)
    # ================================================================
    {
        'name': "Siydik tahlili (umumiy)",
        'category': 'urine',
        'description': 'Buyruq № 363 asosida 040-raqamli tibbiy hujjat shakli',
        'params': [
            {'name': 'Miqdori',               'unit': 'ml',    'type': 'text', 'sort': 1},
            {'name': 'Rangi',                 'unit': '',      'type': 'text', 'sort': 2},
            {'name': 'Tiniqligi',             'unit': '',      'type': 'text', 'sort': 3},
            {'name': 'Nisbiy zichligi',       'unit': '',      'min': 1.010, 'max': 1.025, 'sort': 4},
            {'name': 'Reaksiya (pH)',         'unit': '',      'min': 5.0,   'max': 8.0,   'sort': 5},
            {'name': 'Oqsil',                 'unit': 'g/l',   'max': 0.033, 'sort': 6},
            {'name': 'Glyukoza',             'unit': 'mmol/l','max': 0.8,   'sort': 7},
            {'name': 'Keton tanachalari',     'unit': '',      'type': 'select', 'options': ['Yo\'q', 'Iz', 'Az', 'O\'rtacha', 'Ko\'p'], 'sort': 8},
            {'name': 'Qon birligini aniqlash reaktsiyasi', 'unit': '', 'type': 'text', 'sort': 9},
            {'name': 'Bilirubin',             'unit': '',      'type': 'select', 'options': ['Manfiy', 'Musbat'], 'sort': 10},
            {'name': 'Urobiloindlar',         'unit': '',      'type': 'text', 'sort': 11},
            {'name': 'O\'t kislotasi',        'unit': '',      'type': 'text', 'sort': 12},
        ]
    },

    # ================================================================
    # 17. SIYDIK CHO'KMASI MIKROSKOPIYASI
    # ================================================================
    {
        'name': "Siydik cho'kmasi mikroskopiyasi",
        'category': 'urine',
        'description': '',
        'params': [
            {'name': 'Epiteliy (yassi)',           'unit': 'k/d',   'type': 'text', 'sort': 1},
            {'name': 'Epiteliy (o\'tuvchi)',       'unit': 'k/d',   'type': 'text', 'sort': 2},
            {'name': 'Epiteliy (buyrak)',           'unit': 'k/d',   'type': 'text', 'sort': 3},
            {'name': 'Leykotsitlar',               'unit': 'k/d',   'max': 5,       'sort': 4},
            {'name': 'Eritrotsitlar (o\'zgargan)', 'unit': 'k/d',   'max': 3,       'sort': 5},
            {'name': 'Eritrotsitlar (o\'zgarmagan)','unit': 'k/d',  'max': 3,       'sort': 6},
            {'name': 'Silindrlar (gialinli)',       'unit': 'k/k',   'type': 'text', 'sort': 7},
            {'name': 'Silindrlar (mumsimon)',       'unit': 'k/k',   'type': 'text', 'sort': 8},
            {'name': 'Silindrlar (donador)',        'unit': 'k/k',   'type': 'text', 'sort': 9},
            {'name': 'Shilliq',                    'unit': '',       'type': 'text', 'sort': 10},
            {'name': 'Tuzlar',                     'unit': '',       'type': 'text', 'sort': 11},
            {'name': 'Bakteriyalar',               'unit': '',       'type': 'text', 'sort': 12},
        ]
    },

    # ================================================================
    # 18. SIYDIKDA SHAKLLI ELEMENTLAR SONINI ANIQLASH
    # ================================================================
    {
        'name': "Siydikda shaklli elementlar sonini aniqlash",
        'category': 'urine',
        'description': '',
        'params': [
            {'name': 'Leykotsitlar',   'unit': '', 'type': 'text', 'sort': 1},
            {'name': 'Eritrotsitlar',  'unit': '', 'type': 'text', 'sort': 2},
            {'name': 'Tsilindirlar',   'unit': '', 'type': 'text', 'sort': 3},
        ]
    },

    # ================================================================
    # 19. GLUKOZA VA KETON TANACHASIGA SIYDIK TAHLILI
    # ================================================================
    {
        'name': "Glukoza va keton tanachasiga siydik tahlili",
        'category': 'urine',
        'description': '',
        'params': [
            {'name': 'Glukoza',                     'unit': 'Mmol/l', 'sort': 1},
            {'name': 'Keton tanachalariga reaktsiya','unit': 'Abs',    'type': 'text', 'sort': 2},
        ]
    },

    # ================================================================
    # 20. SPERMOGRAMMA
    # ================================================================
    {
        'name': "Spermogramma",
        'category': 'other',
        'description': 'Buyruq № 363 asosida 042-raqamli tibbiy hujjat shakli',
        'params': [
            {'name': 'Xajmi',                      'unit': 'ml',   'min': 2,    'type': 'numeric', 'sort': 1},
            {'name': 'Rangi',                      'unit': '',     'type': 'text', 'sort': 2},
            {'name': 'Xidi',                       'unit': '',     'type': 'text', 'sort': 3},
            {'name': 'Suyulish vaqti',             'unit': 'dak',  'min': 15,   'max': 30,  'sort': 4},
            {'name': 'pH',                         'unit': '',     'min': 7.2,  'max': 8.0, 'sort': 5},
            {'name': 'Ilashuvchanliq',             'unit': 'sm',   'min': 0,    'max': 2,   'sort': 6},
            {'name': 'Spermatozondlar miqdori (1 mlda)',     'unit': 'mln', 'min': 20, 'sort': 7},
            {'name': 'Spermatozondlar miqdori (umumiy)',     'unit': 'mln', 'min': 40, 'sort': 8},
            {'name': 'Xarakati — faol',            'unit': '%',    'min': 40,   'max': 85,  'sort': 9},
            {'name': 'Xarakati — sust',            'unit': '%',    'min': 4,    'max': 30,  'sort': 10},
            {'name': 'Xarakati — xarakatsiz',      'unit': '%',    'min': 0,    'max': 14,  'sort': 11},
            {'name': 'Tirik spermatozondlar',      'unit': '%',    'min': 50,   'sort': 12},
            {'name': 'Patologik shakllar',         'unit': '%',    'min': 15,   'max': 25,  'sort': 13},
            {'name': 'Spermatogen epiteliy',       'unit': 'k/k',  'min': 2,    'max': 10,  'sort': 14},
            {'name': 'Leykotsitlar',               'unit': 'k/k',  'min': 1,    'max': 8,   'sort': 15},
            {'name': 'Letsitsin donachalar',       'unit': '',     'type': 'text', 'sort': 16},
            {'name': 'Aglyutinatsiya',             'unit': '',     'type': 'select', 'options': ["Yo'q", 'Bor'], 'sort': 17},
            {'name': 'Fruktoza',                   'unit': 'mkmol/eyak', 'min': 1.3, 'sort': 18},
            {'name': 'Limon kislotasi',            'unit': 'mkmol/eyak', 'min': 52, 'sort': 19},
        ]
    },

    # ================================================================
    # 21. BALG'AM TAHLILI
    # ================================================================
    {
        'name': "Balg'am tahlili",
        'category': 'microbiology',
        'description': 'Buyruq № 363 asosida 048-raqamli tibbiy hujjat shakli',
        'params': [
            {'name': 'Miqdori',                     'unit': 'ml',  'type': 'text', 'sort': 1},
            {'name': 'Hidi',                        'unit': '',    'type': 'text', 'sort': 2},
            {'name': 'Rangi',                       'unit': '',    'type': 'text', 'sort': 3},
            {'name': 'Tavsifi',                     'unit': '',    'type': 'text', 'sort': 4},
            {'name': 'Qo\'shilmalari',              'unit': '',    'type': 'text', 'sort': 5},
            {'name': 'Konsistentsiyasi',            'unit': '',    'type': 'text', 'sort': 6},
            {'name': 'Epiteliy',                    'unit': 'k/k', 'type': 'text', 'sort': 7},
            {'name': 'Alveolyar makrofaglar',       'unit': 'k/k', 'type': 'text', 'sort': 8},
            {'name': 'Leykotsitlar',                'unit': 'k/k', 'type': 'text', 'sort': 9},
            {'name': 'Eritrotsitlar',               'unit': 'k/k', 'type': 'text', 'sort': 10},
            {'name': 'Eozinofillar',                'unit': 'k/k', 'type': 'text', 'sort': 11},
            {'name': 'Tolalar (elastik)',           'unit': '',    'type': 'text', 'sort': 12},
            {'name': 'Ko\'rinishli',                'unit': '',    'type': 'text', 'sort': 13},
            {'name': 'Ohaklangan',                  'unit': '',    'type': 'text', 'sort': 14},
            {'name': 'Sil mikrobakteriyalari',      'unit': '',    'type': 'text', 'sort': 15},
            {'name': 'Boshqa flora',                'unit': '',    'type': 'text', 'sort': 16},
            {'name': 'Kurshman spirallari',         'unit': '',    'type': 'text', 'sort': 17},
            {'name': 'Sharko-Leyden kristallari',   'unit': '',    'type': 'text', 'sort': 18},
            {'name': 'Atipik belgilari bor hujayralar', 'unit': '','type': 'text', 'sort': 19},
        ]
    },

    # ================================================================
    # 22. KLINIK TAHLILNOMA (AJRALMA)
    # ================================================================
    {
        'name': "Klinik tahlilnoma — Ajralma tahlili",
        'category': 'microbiology',
        'description': 'U (uretra), C (servis), V (vagina) bo\'yicha',
        'params': [
            {'name': 'Epiteliy',     'unit': '', 'type': 'text', 'sort': 1},
            {'name': 'Leykotsitlar', 'unit': '', 'type': 'text', 'sort': 2},
            {'name': 'Mikroflora',   'unit': '', 'type': 'text', 'sort': 3},
            {'name': 'Zamburug\'lar','unit': '', 'type': 'text', 'sort': 4},
            {'name': 'Trihomoadalar','unit': '', 'type': 'text', 'sort': 5},
            {'name': 'Gonokokklar',  'unit': '', 'type': 'text', 'sort': 6},
        ]
    },
]


class Command(BaseCommand):
    help = "PDF shablonlaridan barcha laboratoriya shablonlarini yaratish"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Mavjud shablonlarni ham qayta yaratish'
        )

    def handle(self, *args, **options):
        force = options['force']
        created_templates = 0
        skipped_templates = 0
        created_params = 0

        self.stdout.write("=" * 60)
        self.stdout.write("Laboratoriya shablonlarini yaratish boshlandi...")
        self.stdout.write("=" * 60)

        for tmpl_data in TEMPLATES:
            name = tmpl_data['name']

            existing = LabTemplate.objects.filter(name=name).first()
            if existing and not force:
                skipped_templates += 1
                self.stdout.write(f"  [skip]  Mavjud: {name}")
                continue

            if existing and force:
                existing.parameters.all().delete()
                template = existing
                template.category = tmpl_data['category']
                template.description = tmpl_data.get('description', '')
                template.is_active = True
                template.save()
                self.stdout.write(f"  [update] Yangilandi: {name}")
            else:
                template = LabTemplate.objects.create(
                    name=name,
                    category=tmpl_data['category'],
                    description=tmpl_data.get('description', ''),
                    is_active=True,
                )
                created_templates += 1
                self.stdout.write(f"  [OK] Yaratildi: {name}")

            for p in tmpl_data.get('params', []):
                ptype = p.get('type', 'numeric')
                options_list = p.get('options', [])

                LabParameter.objects.create(
                    template=template,
                    group=None,
                    name=p['name'],
                    name_ru=p.get('name_ru', ''),
                    unit=p.get('unit', ''),
                    param_type=ptype,
                    normal_min=p.get('min'),
                    normal_max=p.get('max'),
                    critical_min=p.get('crit_min'),
                    critical_max=p.get('crit_max'),
                    normal_min_m=p.get('min_m'),
                    normal_max_m=p.get('max_m'),
                    normal_min_f=p.get('min_f'),
                    normal_max_f=p.get('max_f'),
                    select_options=options_list,
                    sort_order=p.get('sort', 0),
                )
                created_params += 1

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS(f"Yaratildi:    {created_templates} ta shablon"))
        self.stdout.write(self.style.WARNING(f"O'tkazildi:  {skipped_templates} ta (--force bilan qayta yarating)"))
        self.stdout.write(self.style.SUCCESS(f"Parametrlar: {created_params} ta"))
        self.stdout.write("=" * 60)
