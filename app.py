# Tablero Dash: Observatorio de Accidentalidad Vial en Colombia (avance)
# Uso: pip install dash==3.2.0 dash-bootstrap-components gdown plotly pandas numpy
#      python app.py   ->   http://127.0.0.1:8050

import os
import re
import unicodedata
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Parámetros (los mismos de la entrega 3)
ID_DRIVE = '1scXzoYoH9dImZJhG4sTJjZ6BrST2TvKb'
ARCHIVO = 'base_maestra_accidentalidad_colombia.csv'
ANIO_INI, ANIO_FIN = 2021, 2025
SIN_INFO = 'Sin información'
TASAS = ['ocupacion_segun_sexo', 'desocupacion_segun_sexo',
         'subocupacion_segun_sexo', 'desocupacion_total_anual']

if not os.path.exists(ARCHIVO):
    try:
        import gdown
        gdown.download(id=ID_DRIVE, output=ARCHIVO, quiet=False)
    except Exception as e:
        print('No se pudo descargar automáticamente:', e)
        print('Sube el archivo al panel de archivos de Colab y vuelve a correr esta celda.')

df = pd.read_csv(ARCHIVO, encoding='utf-8-sig', low_memory=False)
df = df.rename(columns={'rango_de_hora_del_hecho_x_3_horas': 'rango_hora'})
df = df[df['año'].between(ANIO_INI, ANIO_FIN)].reset_index(drop=True)
ANIO_INI, ANIO_FIN = int(df['año'].min()), int(df['año'].max())
print('Años en la base:', [int(a) for a in sorted(df['año'].unique())], '| filas:', len(df))

# --- 2. Unificar cómo está escrita cada categoría ---
def sin_tildes(texto):
    t = unicodedata.normalize('NFKD', str(texto).lower())
    return ''.join(c for c in t if not unicodedata.combining(c))


def clave(valor):
    s = sin_tildes(valor).strip()
    s = s.replace('(', '').replace(')', '')
    return re.sub(r'\s+', '', s)


COLS_CAT = ['sexo', 'grupo_edad', 'escolaridad', 'estado_civil', 'mes_del_hecho', 'dia_del_hecho',
            'rango_hora', 'municipio', 'departamento', 'circunstancia', 'medio_desplazamiento',
            'gravedad_del_hecho']
COLS_CAT = [c for c in COLS_CAT if c in df.columns]

for c in COLS_CAT:
    conteo = df[c].dropna().astype(str).value_counts()
    representante = {}
    for valor in conteo.index:
        k = clave(valor)
        if k not in representante:
            representante[k] = valor
    df[c] = df[c].map(lambda v: v if pd.isna(v) else representante[clave(v)])

# --- 4. Faltantes ---
TOKENS = {'', 'sin información', 'sin informacion', 'sin dato', 'sin datos', 'no informa', 'no informado',
          'no reportado', 'no aplica', 'sin especificar', 'desconocido'}


def a_nan(serie):
    es_token = serie.astype(str).str.strip().str.lower().isin(TOKENS)
    return serie.mask(es_token)


def imputar_tasas(d):
    d['desocupacion_segun_sexo'] = d['desocupacion_segun_sexo'].fillna(d['desocupacion_total_anual'])
    for c in ['ocupacion_segun_sexo', 'subocupacion_segun_sexo']:
        promedio = d.groupby(['departamento', 'año'])[c].transform('mean')
        d[c] = d[c].fillna(promedio)
    return d


cols_texto = df.select_dtypes(exclude=['number', 'bool']).columns
for c in cols_texto:
    df[c] = a_nan(df[c])
df = df.dropna(subset=['departamento', 'año']).reset_index(drop=True)
df = imputar_tasas(df)
df[list(cols_texto)] = df[list(cols_texto)].fillna(SIN_INFO)

# --- 5. Tasas fuera de 0-100 son errores: NaN y se vuelven a imputar ---
for c in TASAS:
    fuera = (df[c] < 0) | (df[c] > 100)
    df.loc[fuera, c] = np.nan
df = imputar_tasas(df)

# --- 6. Categorización ---
NIVELES = [('sin escol', 0), ('ning', 0), ('analfab', 0), ('preesc', 1), ('primaria', 2),
           ('media', 4), ('secundaria', 3), ('tecnic', 5), ('tecnolog', 5), ('normalista', 5),
           ('universit', 6), ('profesional', 6), ('pregrado', 6),
           ('especializ', 7), ('maestr', 7), ('posgrado', 7), ('postgrado', 7), ('doctor', 8),
           ('superior', 6)]
DIAS = {'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3, 'viernes': 4, 'sabado': 5, 'domingo': 6}
NOMBRES_DIA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
NOMBRES_NIVEL = {0: 'Sin escolaridad', 1: 'Preescolar', 2: 'Básica primaria', 3: 'Básica secundaria', 4: 'Media',
                 5: 'Técnica o tecnológica', 6: 'Universitaria', 7: 'Especialización o maestría', 8: 'Doctorado'}


def nivel_escolaridad(texto):
    t = sin_tildes(texto)
    for palabra, nivel in NIVELES:
        if palabra in t:
            return nivel
    return np.nan


def numero_inicial(serie):
    return serie.str.extract(r'(\d+)')[0].astype(float)


df['grupo_edad_cod'] = numero_inicial(df['grupo_edad'])
df['hora_inicio'] = numero_inicial(df['rango_hora'])
df['dia_cod'] = df['dia_del_hecho'].map(lambda v: DIAS.get(sin_tildes(v), np.nan)).astype(float)
niveles = {v: nivel_escolaridad(v) for v in df['escolaridad'].unique()}
df['escolaridad_cod'] = df['escolaridad'].map(niveles)
df['escolaridad_nivel'] = df['escolaridad_cod'].map(NOMBRES_NIVEL).fillna(SIN_INFO)

df['es_muerte'] = df['gravedad_del_hecho'].str.lower().str.startswith('muerte').astype(int)
df['es_hombre'] = (df['sexo'].str.lower() == 'hombre').astype(int)
df['es_mujer'] = (df['sexo'].str.lower() == 'mujer').astype(int)
df['medio_conocido'] = (df['medio_desplazamiento'] != SIN_INFO).astype(int)
df['es_motociclista'] = df['medio_desplazamiento'].str.contains('moto', case=False).astype(int)
df['hora_conocida'] = df['hora_inicio'].notna().astype(int)
df['es_nocturno'] = df['hora_inicio'].isin([18, 21, 0, 3]).astype(int)

print('Base lista:', df.shape)

def kpi_letalidad(base, por):
    g = base.groupby(por, dropna=False).agg(victimas=('es_muerte', 'size'), muertes=('es_muerte', 'sum')).reset_index()
    g['letalidad_pct'] = g['muertes'] / g['victimas'] * 100
    return g


def kpi_concentracion(base, n=5):
    v = base.groupby(['año', 'departamento']).size().rename('victimas').reset_index()
    top = v.sort_values('victimas', ascending=False).groupby('año').head(n)
    out = top.groupby('año')['victimas'].sum().rename('victimas_top').to_frame()
    out['victimas_total'] = v.groupby('año')['victimas'].sum()
    out['concentracion_pct'] = out['victimas_top'] / out['victimas_total'] * 100
    out['departamentos'] = top.groupby('año')['departamento'].agg(', '.join)
    return out.reset_index()


def kpi_moto(base, por):
    g = base.groupby(por).agg(motociclistas=('es_motociclista', 'sum'), medio_conocido=('medio_conocido', 'sum')).reset_index()
    g['participacion_moto_pct'] = g['motociclistas'] / g['medio_conocido'] * 100
    return g


def kpi_razon_hm(base, por):
    g = base.groupby(por, dropna=False).agg(hombres=('es_hombre', 'sum'), mujeres=('es_mujer', 'sum')).reset_index()
    g['razon_hombre_mujer'] = g['hombres'] / g['mujeres'].replace(0, np.nan)
    return g


def kpi_nocturno(base, por):
    g = base.groupby(por).agg(nocturnas=('es_nocturno', 'sum'), hora_conocida=('hora_conocida', 'sum')).reset_index()
    g['nocturno_pct'] = g['nocturnas'] / g['hora_conocida'] * 100
    return g


def tabla_depto_anio(base):
    t = base.groupby(['departamento', 'año']).agg(
        victimas=('es_muerte', 'size'), muertes=('es_muerte', 'sum'),
        motociclistas=('es_motociclista', 'sum'), medio_conocido=('medio_conocido', 'sum'),
        desocupacion=('desocupacion_total_anual', 'first')).reset_index()
    por_sexo = base[base['sexo'].str.lower().isin(['hombre', 'mujer'])].drop_duplicates(['departamento', 'año', 'sexo'])
    laboral = por_sexo.groupby(['departamento', 'año']).agg(
        ocupacion=('ocupacion_segun_sexo', 'mean'),
        subocupacion=('subocupacion_segun_sexo', 'mean')).reset_index()
    return t.merge(laboral, on=['departamento', 'año'], how='left')


# Panel con los cinco KPI por año
panel = (kpi_letalidad(df, ['año'])[['año', 'victimas', 'letalidad_pct']]
         .merge(kpi_concentracion(df)[['año', 'concentracion_pct']], on='año')
         .merge(kpi_moto(df, ['año'])[['año', 'participacion_moto_pct']], on='año')
         .merge(kpi_razon_hm(df, ['año'])[['año', 'razon_hombre_mujer']], on='año')
         .merge(kpi_nocturno(df, ['año'])[['año', 'nocturno_pct']], on='año'))
panel.round(2)

VERDE, VERDE_CLARO, TURQUESA, AZUL, GRIS = '#056938', '#8EC044', '#46B8A9', '#157699', '#BFBFBF'
PLANTILLA = 'plotly_white'
TODOS = 'Todos los departamentos'
TODO_PERIODO = 'Todo el período'


def filtrar(base, anio=None, departamento=None):
    d = base
    if anio not in (None, TODO_PERIODO):
        d = d[d['año'] == anio]
    if departamento not in (None, TODOS):
        d = d[d['departamento'] == departamento]
    return d


def figura_vacia(mensaje):
    fig = go.Figure()
    fig.add_annotation(text=mensaje, showarrow=False, font=dict(size=16))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(template=PLANTILLA)
    return fig

def grafico_top_departamentos(base, anio, n=10):
    d = filtrar(base, anio)
    k = kpi_letalidad(d, ['departamento']).sort_values('victimas', ascending=False).head(n)
    fig = px.bar(k, x='victimas', y='departamento', color='letalidad_pct', orientation='h',
                 color_continuous_scale='Reds', hover_data={'muertes': True},
                 labels={'victimas': 'Víctimas', 'departamento': '', 'letalidad_pct': 'Letalidad (%)'},
                 title=f'Los {n} departamentos con más víctimas ({anio})')
    fig.update_traces(texttemplate='%{x:,.0f}', textposition='outside')
    fig.update_yaxes(categoryorder='total ascending')
    fig.update_layout(template=PLANTILLA, title_x=0.5)
    return fig

# Coordenadas (lat, lon) de la capital de cada departamento de la base
COORDENADAS = {
    'Antioquia': (6.25, -75.57), 'Atlántico': (10.96, -74.80), 'Bolívar': (10.39, -75.48),
    'Boyacá': (5.54, -73.36), 'Caldas': (5.07, -75.52), 'Caquetá': (1.61, -75.61),
    'Cauca': (2.44, -76.61), 'Cesar': (10.46, -73.25), 'Córdoba': (8.75, -75.88),
    'Cundinamarca': (5.00, -74.10), 'Chocó': (5.69, -76.65), 'Huila': (2.93, -75.28),
    'La Guajira': (11.54, -72.91), 'Magdalena': (11.24, -74.20), 'Meta': (4.14, -73.63),
    'Nariño': (1.21, -77.28), 'Norte de Santander': (7.89, -72.50), 'Quindío': (4.53, -75.68),
    'Risaralda': (4.81, -75.69), 'Santander': (7.12, -73.12), 'Sucre': (9.30, -75.40),
    'Tolima': (4.44, -75.23), 'Valle del Cauca': (3.45, -76.53)}
COORD = {clave(k): v for k, v in COORDENADAS.items()}
COORD['valle'] = COORD['valledelcauca']       # por si la fuente escribe "Valle"
COORD['guajira'] = COORD['laguajira']


def departamentos_sin_coordenadas(base):
    return sorted(d for d in base['departamento'].unique() if clave(d) not in COORD)


def grafico_mapa(base, anio):
    k = kpi_letalidad(filtrar(base, anio), ['departamento'])
    k['lat'] = k['departamento'].map(lambda d: COORD.get(clave(d), (np.nan, np.nan))[0])
    k['lon'] = k['departamento'].map(lambda d: COORD.get(clave(d), (np.nan, np.nan))[1])
    k = k.dropna(subset=['lat'])
    textos = [f'{r.departamento}<br>Víctimas: {r.victimas:,.0f}<br>Letalidad: {r.letalidad_pct:.1f}%'
              for r in k.itertuples()]
    fig = go.Figure(go.Scattermap(
        lat=k['lat'], lon=k['lon'], mode='markers', text=textos, hoverinfo='text',
        marker=dict(size=k['victimas'], sizemode='area', sizemin=6,
                    sizeref=2 * k['victimas'].max() / (45 ** 2),
                    color=k['letalidad_pct'], colorscale='Reds', showscale=True,
                    colorbar=dict(title='Letalidad (%)'))))
    fig.update_layout(map=dict(style='open-street-map', center=dict(lat=6.5, lon=-74.5), zoom=4.3),
                      margin=dict(l=0, r=0, t=40, b=0), title=f'Víctimas y letalidad por departamento ({anio})',
                      title_x=0.5)
    return fig


print('Departamentos sin coordenadas (debe ser []):', departamentos_sin_coordenadas(df))

def grafico_franja(base, departamento=TODOS, anio=TODO_PERIODO):
    d = filtrar(base, anio, departamento)
    d = d[d['hora_conocida'] == 1]
    if d.empty:
        return figura_vacia('No hay datos de hora para esta selección')
    f = (d.groupby(['hora_inicio', 'rango_hora']).size().rename('victimas').reset_index()
         .sort_values('hora_inicio'))
    f['pct'] = f['victimas'] / f['victimas'].sum() * 100
    f['momento'] = np.where(f['hora_inicio'].isin([18, 21, 0, 3]), 'Noche (18:00 a 05:59)', 'Día (06:00 a 17:59)')
    pct_noche = d['es_nocturno'].mean() * 100
    fig = px.bar(f, x='rango_hora', y='pct', color='momento', hover_data={'victimas': True},
                 color_discrete_map={'Noche (18:00 a 05:59)': AZUL, 'Día (06:00 a 17:59)': GRIS},
                 labels={'rango_hora': 'Franja horaria', 'pct': '% de las víctimas', 'momento': ''},
                 title=f'Víctimas por franja horaria: {pct_noche:.1f}% ocurre de noche (K5)')
    fig.update_xaxes(categoryorder='array', categoryarray=list(f['rango_hora']))
    fig.update_layout(template=PLANTILLA, title_x=0.5, legend=dict(orientation='h', y=-0.25))
    return fig


def grafico_dia(base, departamento=TODOS, anio=TODO_PERIODO):
    d = filtrar(base, anio, departamento)
    d = d[d['dia_cod'].notna()]
    if d.empty:
        return figura_vacia('No hay datos de día para esta selección')
    g = kpi_letalidad(d, ['dia_cod']).sort_values('dia_cod')
    g['dia'] = g['dia_cod'].map(lambda c: NOMBRES_DIA[int(c)])
    g['tipo'] = np.where(g['dia_cod'] >= 5, 'Fin de semana', 'Entre semana')
    fig = px.bar(g, x='dia', y='victimas', color='tipo', hover_data={'letalidad_pct': ':.1f'},
                 color_discrete_map={'Fin de semana': AZUL, 'Entre semana': GRIS},
                 labels={'dia': '', 'victimas': 'Víctimas', 'tipo': ''},
                 title='Víctimas por día de la semana')
    fig.update_xaxes(categoryorder='array', categoryarray=NOMBRES_DIA)
    fig.update_layout(template=PLANTILLA, title_x=0.5, legend=dict(orientation='h', y=-0.25))
    return fig

def medios_principales(base, departamento=TODOS, n=4):
    d = filtrar(base, departamento=departamento)
    d = d[d['medio_conocido'] == 1]
    return list(d['medio_desplazamiento'].value_counts().head(n).index)


def grafico_circunstancias(base, departamento, medio, n=5):
    d = filtrar(base, departamento=departamento)
    d = d[(d['medio_desplazamiento'] == medio) & (d['circunstancia'] != SIN_INFO)]
    if d.empty:
        return figura_vacia('No hay circunstancias registradas para esta selección')
    c = (d['circunstancia'].value_counts(normalize=True).head(n) * 100).rename('pct').rename_axis('circunstancia').reset_index()
    fig = px.bar(c, x='pct', y='circunstancia', orientation='h',
                 labels={'pct': f'% de las víctimas en {medio.lower()}', 'circunstancia': ''},
                 title=f'Circunstancias más frecuentes: {medio} ({departamento})')
    fig.update_traces(marker_color=VERDE, texttemplate='%{x:.1f}%', textposition='outside')
    fig.update_yaxes(categoryorder='total ascending')
    fig.update_layout(template=PLANTILLA, title_x=0.5)
    return fig

VARIABLES_Q2 = {'Grupo de edad': ('grupo_edad_cod', 'grupo_edad'),
                'Escolaridad': ('escolaridad_cod', 'escolaridad_nivel')}


def grafico_variable(base, variable, metrica, anio=TODO_PERIODO):
    cod, etiqueta = VARIABLES_Q2[variable]
    d = filtrar(base, anio)
    g = kpi_letalidad(d, [cod, etiqueta]).sort_values(cod)
    orden = list(g[etiqueta])
    if metrica == 'Letalidad (%)':
        g['tipo'] = np.where(g[etiqueta] == SIN_INFO, SIN_INFO, 'Con dato')
        fig = px.bar(g, x=etiqueta, y='letalidad_pct', color='tipo',
                     color_discrete_map={'Con dato': VERDE, SIN_INFO: GRIS},
                     hover_data={'victimas': ':,.0f', 'muertes': ':,.0f'},
                     labels={etiqueta: variable, 'letalidad_pct': 'Letalidad (%)'},
                     title=f'Letalidad por {variable.lower()} ({anio})')
        general = d['es_muerte'].mean() * 100
        fig.add_hline(y=general, line_dash='dash', line_color=AZUL,
                      annotation_text=f'Letalidad general: {general:.1f}%')
        fig.update_layout(showlegend=False)
    else:
        fig = px.bar(g, x=etiqueta, y='victimas', color='letalidad_pct', color_continuous_scale='Reds',
                     hover_data={'muertes': ':,.0f'},
                     labels={etiqueta: variable, 'victimas': 'Víctimas', 'letalidad_pct': 'Letalidad (%)'},
                     title=f'Víctimas por {variable.lower()} ({anio}); el color indica la letalidad')
    fig.update_xaxes(categoryorder='array', categoryarray=orden)
    fig.update_layout(template=PLANTILLA, title_x=0.5)
    return fig

def grafico_razon_edad(base, anio=TODO_PERIODO):
    d = filtrar(base, anio)
    r = kpi_razon_hm(d, ['grupo_edad_cod', 'grupo_edad']).sort_values('grupo_edad_cod')
    r = r[r['grupo_edad_cod'].notna()]
    fig = px.bar(r, x='grupo_edad', y='razon_hombre_mujer', hover_data={'hombres': ':,.0f', 'mujeres': ':,.0f'},
                 labels={'grupo_edad': 'Grupo de edad', 'razon_hombre_mujer': 'Hombres por cada mujer'},
                 title=f'Hombres por cada mujer víctima, según grupo de edad ({anio})')
    fig.update_traces(marker_color=VERDE)
    fig.add_hline(y=1, line_dash='dash', line_color=AZUL, annotation_text='Paridad')
    fig.update_xaxes(categoryorder='array', categoryarray=list(r['grupo_edad']))
    fig.update_layout(template=PLANTILLA, title_x=0.5)
    return fig


def grafico_sexo_anio(base):
    hm = (base.groupby('año')[['es_hombre', 'es_mujer']].sum()
          .rename(columns={'es_hombre': 'Hombres', 'es_mujer': 'Mujeres'}).reset_index())
    largo = hm.melt(id_vars='año', value_vars=['Hombres', 'Mujeres'], var_name='sexo', value_name='victimas')
    fig = px.line(largo, x='año', y='victimas', color='sexo', markers=True,
                  color_discrete_map={'Hombres': AZUL, 'Mujeres': VERDE_CLARO},
                  labels={'año': '', 'victimas': 'Víctimas', 'sexo': ''},
                  title='Víctimas hombres y mujeres por año')
    fig.update_xaxes(dtick=1)
    fig.update_layout(template=PLANTILLA, title_x=0.5)
    return fig

TABLA_DA = tabla_depto_anio(df)
TABLA_DA['participacion'] = TABLA_DA['motociclistas'] / TABLA_DA['medio_conocido'] * 100

EJES_X = {'Desocupación (%)': 'desocupacion', 'Ocupación (%)': 'ocupacion'}
EJES_Y = {'Víctimas en moto': 'motociclistas', 'Participación de motos, K3 (%)': 'participacion'}


def tabla_q3(anio):
    cols = ['desocupacion', 'ocupacion', 'motociclistas', 'participacion']
    if anio == TODO_PERIODO:
        return TABLA_DA.groupby('departamento')[cols].mean().dropna().reset_index()
    return TABLA_DA[TABLA_DA['año'] == anio][['departamento'] + cols].dropna().reset_index(drop=True)


def grafico_dispersion(tabla, x_nombre, y_nombre, anio=TODO_PERIODO):
    x, y = EJES_X[x_nombre], EJES_Y[y_nombre]
    t = tabla.copy()
    rotulos = set(t.nlargest(3, y)['departamento']) | set(t.nlargest(3, x)['departamento'])
    t['etiqueta'] = t['departamento'].where(t['departamento'].isin(rotulos), '')
    fig = px.scatter(t, x=x, y=y, text='etiqueta', hover_name='departamento',
                     labels={x: x_nombre, y: y_nombre},
                     title=f'{y_nombre} frente a {x_nombre.lower()} por departamento ({anio})')
    fig.update_traces(marker=dict(size=10, color=VERDE), textposition='top center')
    fig.update_layout(template=PLANTILLA, title_x=0.5)
    return fig


def lectura_correlacion(tabla, x_nombre, y_nombre):
    x, y = EJES_X[x_nombre], EJES_Y[y_nombre]
    rho = tabla[x].corr(tabla[y], method='spearman')
    a = abs(rho)
    fuerza = 'muy débil o nula' if a < 0.2 else 'débil' if a < 0.4 else 'moderada' if a < 0.6 else 'fuerte'
    if rho >= 0.4:
        concl = 'Los departamentos con valores más altos en el eje X tienden a tener valores más altos en el eje Y.'
    elif rho <= -0.4:
        concl = 'Los departamentos con valores más altos en el eje X tienden a tener valores más bajos en el eje Y.'
    else:
        concl = 'La relación no se sostiene al comparar el conjunto de departamentos.'
    return (f'Correlación de Spearman: {rho:.2f} (relación {fuerza}, {len(tabla)} departamentos). {concl} '
            'Es una comparación entre territorios, no entre personas.')

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output

# nombre, formato, y si un aumento es una señal de alerta (se pinta en rojo)
KPIS = {
    'letalidad_pct':          ('K1 Letalidad vial', '{:.1f}%', True),
    'concentracion_pct':      ('K2 Concentración Top-5 departamentos', '{:.1f}%', False),
    'participacion_moto_pct': ('K3 Participación de motociclistas', '{:.1f}%', True),
    'razon_hombre_mujer':     ('K4 Hombres por cada mujer', '{:.1f}', False),
    'nocturno_pct':           ('K5 Participación nocturna', '{:.1f}%', True),
}


def calcular_kpis(base, anio):
    d = base[base['año'] == anio]
    return {'letalidad_pct': kpi_letalidad(d, ['año'])['letalidad_pct'].iloc[0],
            'concentracion_pct': kpi_concentracion(d)['concentracion_pct'].iloc[0],
            'participacion_moto_pct': kpi_moto(d, ['año'])['participacion_moto_pct'].iloc[0],
            'razon_hombre_mujer': kpi_razon_hm(d, ['año'])['razon_hombre_mujer'].iloc[0],
            'nocturno_pct': kpi_nocturno(d, ['año'])['nocturno_pct'].iloc[0]}


def tarjeta_kpi(clave_kpi, valor, previo=None):
    nombre, formato, alerta = KPIS[clave_kpi]
    if previo is None:
        delta = html.P('Primer año de la base', className='card-text text-muted')
    else:
        cambio = (valor / previo - 1) * 100
        flecha = '▲' if cambio >= 0 else '▼'
        color = ('text-danger' if cambio >= 0 else 'text-success') if alerta else 'text-secondary'
        delta = html.P(f'{flecha} {abs(cambio):.1f}% respecto al año anterior', className=f'card-text {color}')
    return dbc.Card(dbc.CardBody([html.H6(nombre, className='card-title'),
                                  html.P(formato.format(valor), className='card-text', style={'fontSize': 30}),
                                  delta]),
                    style={'margin': '8px'})


def tarjetas_resumen(base, anio):
    actual = calcular_kpis(base, anio)
    anios = sorted(base['año'].unique())
    previo = calcular_kpis(base, anio - 1) if (anio - 1) in anios else {}
    return [tarjeta_kpi(k, actual[k], previo.get(k)) for k in KPIS]


def grafico_serie_kpi(panel, clave_kpi):
    nombre, formato, _ = KPIS[clave_kpi]
    fig = px.line(panel, x='año', y=clave_kpi, markers=True,
                  labels={'año': '', clave_kpi: nombre}, title=f'{nombre} por año')
    fig.update_traces(line_color=VERDE)
    fig.update_xaxes(dtick=1)
    fig.update_layout(template=PLANTILLA, title_x=0.5)
    return fig

SIDEBAR_STYLE = {"position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "20rem",
                 "padding": "2rem 1rem", "background-color": "#f8f9fa", "overflow": "auto"}
CONTENT_STYLE = {"margin-left": "21rem", "margin-right": "2rem", "padding": "2rem 1rem"}

anios = sorted(int(a) for a in df['año'].unique())
ANIO_MAX = anios[-1]
opciones_anio = [{'label': str(a), 'value': a} for a in anios]
opciones_anio_todo = [{'label': TODO_PERIODO, 'value': TODO_PERIODO}] + opciones_anio
departamentos = sorted(df['departamento'].unique())
opciones_depto = [{'label': TODOS, 'value': TODOS}] + [{'label': d, 'value': d} for d in departamentos]


def selector(etiqueta, id_, opciones, valor):
    return [html.Label(etiqueta, style={'fontWeight': 'bold'}),
            dcc.Dropdown(id=id_, options=opciones, value=valor, clearable=False)]


sidebar = html.Div([
    html.H4("Observatorio de accidentalidad vial", className="display-6"),
    html.Hr(),
    html.P("Víctimas de siniestros viales en 23 departamentos de Colombia y su contexto laboral.", className="lead"),
    dbc.Nav([
        dbc.NavLink("Resumen: los 5 KPI", href="/", active="exact"),
        dbc.NavLink("Q1. Territorio y horario", href="/q1", active="exact"),
        dbc.NavLink("Q2. Edad, escolaridad y género", href="/q2", active="exact"),
        dbc.NavLink("Q3. Desocupación y motos", href="/q3", active="exact"),
    ], vertical=True, pills=True),
], style=SIDEBAR_STYLE)

content = html.Div(id="page-content", style=CONTENT_STYLE)


def pagina_resumen():
    return html.Div([
        html.H2("Resumen: los cinco indicadores"),
        html.P("Un vistazo a los KPI definidos en la entrega 3. Escoge un año para ver su valor y cómo cambió frente al año anterior."),
        dbc.Row([dbc.Col(selector('Año', 'dd-anio-resumen', opciones_anio, ANIO_MAX), width=3)]),
        html.Br(),
        dbc.Row([dbc.Col(html.Div(id=f'kpi-{i}'), md=6, lg=4) for i in range(len(KPIS))]),
        html.Hr(),
        dbc.Row([dbc.Col(selector('Evolución del indicador', 'dd-kpi-serie',
                                  [{'label': v[0], 'value': k} for k, v in KPIS.items()], 'letalidad_pct'), width=6)]),
        dcc.Graph(id='graf-serie-kpi'),
    ])


def pagina_q1():
    return html.Div([
        html.H2("Q1. ¿Dónde, cuándo y por qué?"),
        html.P("Frecuencia (tamaño o longitud) y gravedad (color) por departamento, y los patrones de horario y de causalidad."),
        dbc.Row([dbc.Col(selector('Año', 'dd-anio-q1', opciones_anio, ANIO_MAX), width=3)]),
        dbc.Row([dbc.Col(dcc.Graph(id='graf-top'), lg=6), dbc.Col(dcc.Graph(id='graf-mapa'), lg=6)]),
        html.Hr(),
        dbc.Row([dbc.Col(selector('Departamento', 'dd-depto-q1', opciones_depto, TODOS), width=4)]),
        dbc.Row([dbc.Col(dcc.Graph(id='graf-franja'), lg=6), dbc.Col(dcc.Graph(id='graf-dia'), lg=6)]),
        html.Hr(),
        dbc.Row([dbc.Col([html.Label('Medio de transporte', style={'fontWeight': 'bold'}),
                          dcc.Dropdown(id='dd-medio-q1', clearable=False)], width=4)]),
        dcc.Graph(id='graf-circ'),
    ])


def pagina_q2():
    return html.Div([
        html.H2("Q2. Edad, escolaridad y género"),
        html.P("¿Quiénes son las víctimas y qué tan graves son sus siniestros?"),
        dbc.Row([
            dbc.Col(selector('Variable', 'dd-var-q2', [{'label': v, 'value': v} for v in VARIABLES_Q2], 'Grupo de edad'), width=3),
            dbc.Col(selector('Métrica', 'dd-metrica-q2', [{'label': m, 'value': m} for m in ['Víctimas', 'Letalidad (%)']], 'Víctimas'), width=3),
            dbc.Col(selector('Año', 'dd-anio-q2', opciones_anio_todo, TODO_PERIODO), width=3),
        ]),
        dcc.Graph(id='graf-var-q2'),
        html.Hr(),
        dbc.Row([dbc.Col(dcc.Graph(id='graf-razon-q2'), lg=6),
                 dbc.Col(dcc.Graph(id='graf-sexo-anio', figure=grafico_sexo_anio(df)), lg=6)]),
    ])


def pagina_q3():
    return html.Div([
        html.H2("Q3. ¿Más desocupación, más siniestros de motociclistas?"),
        html.P("Cada punto es un departamento. Se mide con la correlación de Spearman."),
        dbc.Row([
            dbc.Col(selector('Eje X (contexto laboral)', 'dd-x-q3', [{'label': k, 'value': k} for k in EJES_X], 'Desocupación (%)'), width=3),
            dbc.Col(selector('Eje Y (motociclistas)', 'dd-y-q3', [{'label': k, 'value': k} for k in EJES_Y], 'Víctimas en moto'), width=4),
            dbc.Col(selector('Año', 'dd-anio-q3', opciones_anio_todo, TODO_PERIODO), width=3),
        ]),
        dcc.Graph(id='graf-disp-q3'),
        dbc.Alert(id='texto-q3', color='light'),
    ])

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server  # necesario para publicarlo con gunicorn
app.layout = html.Div([dcc.Location(id="url"), sidebar, content])


# ---- Navegación entre páginas ----
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def mostrar_pagina(pathname):
    if pathname == "/":
        return pagina_resumen()
    elif pathname == "/q1":
        return pagina_q1()
    elif pathname == "/q2":
        return pagina_q2()
    elif pathname == "/q3":
        return pagina_q3()
    return html.Div([html.H1("404: Not found", className="text-danger"), html.Hr(),
                     html.P(f"La ruta {pathname} no existe.")], className="p-3 bg-light rounded-3")


# ---- Resumen: un Input, múltiples Output ----
@app.callback([Output(f'kpi-{i}', 'children') for i in range(len(KPIS))],
              Input('dd-anio-resumen', 'value'))
def actualizar_tarjetas(anio):
    return tarjetas_resumen(df, anio)


@app.callback(Output('graf-serie-kpi', 'figure'), Input('dd-kpi-serie', 'value'))
def actualizar_serie(clave_kpi):
    return grafico_serie_kpi(panel, clave_kpi)


# ---- Q1 ----
@app.callback(Output('graf-top', 'figure'), Output('graf-mapa', 'figure'), Input('dd-anio-q1', 'value'))
def actualizar_q1_anio(anio):
    return grafico_top_departamentos(df, anio), grafico_mapa(df, anio)


@app.callback(Output('graf-franja', 'figure'), Output('graf-dia', 'figure'), Input('dd-depto-q1', 'value'))
def actualizar_q1_horario(departamento):
    return grafico_franja(df, departamento), grafico_dia(df, departamento)


# Callbacks encadenados: departamento -> opciones de medio -> valor del medio -> gráfico
@app.callback(Output('dd-medio-q1', 'options'), Input('dd-depto-q1', 'value'))
def opciones_medio(departamento):
    return medios_principales(df, departamento)


@app.callback(Output('dd-medio-q1', 'value'), Input('dd-medio-q1', 'options'))
def valor_medio(opciones):
    return opciones[0] if opciones else None


@app.callback(Output('graf-circ', 'figure'), Input('dd-depto-q1', 'value'), Input('dd-medio-q1', 'value'))
def actualizar_circunstancias(departamento, medio):
    return grafico_circunstancias(df, departamento, medio)


# ---- Q2 ----
@app.callback(Output('graf-var-q2', 'figure'), Output('graf-razon-q2', 'figure'),
              Input('dd-var-q2', 'value'), Input('dd-metrica-q2', 'value'), Input('dd-anio-q2', 'value'))
def actualizar_q2(variable, metrica, anio):
    return grafico_variable(df, variable, metrica, anio), grafico_razon_edad(df, anio)


# ---- Q3 ----
@app.callback(Output('graf-disp-q3', 'figure'), Output('texto-q3', 'children'),
              Input('dd-x-q3', 'value'), Input('dd-y-q3', 'value'), Input('dd-anio-q3', 'value'))
def actualizar_q3(x_nombre, y_nombre, anio):
    tabla = tabla_q3(anio)
    return grafico_dispersion(tabla, x_nombre, y_nombre, anio), lectura_correlacion(tabla, x_nombre, y_nombre)

if __name__ == '__main__':
    app.run(debug=False, port=8050)