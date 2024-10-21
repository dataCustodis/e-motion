import sqlite3
import csv
import html
from collections import defaultdict

def crear_base_de_datos():
    conn = sqlite3.connect('guardias.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS guardias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_guardia TEXT,
        abogado_cede TEXT,
        abogado_recibe TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def cargar_datos_desde_csv(archivo_csv):
    conn = sqlite3.connect('guardias.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM guardias')  # Limpiar la tabla antes de cargar nuevos datos
    
    with open(archivo_csv, 'r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Saltar la primera fila si contiene encabezados
        for row in csv_reader:
            cursor.execute('INSERT INTO guardias (tipo_guardia, abogado_cede, abogado_recibe) VALUES (?, ?, ?)', row)
    
    conn.commit()
    conn.close()

def conectar():
    return sqlite3.connect('guardias.db')

def contar_cesiones_por_abogado():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT abogado_cede, COUNT(*) as count FROM guardias GROUP BY abogado_cede ORDER BY count DESC")
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def contar_recepciones_por_abogado():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT abogado_recibe, COUNT(*) as count FROM guardias GROUP BY abogado_recibe ORDER BY count DESC")
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def abogados_ceden_y_reciben():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT abogado, 
           SUM(CASE WHEN tipo = 'cede' THEN count ELSE 0 END) as cesiones,
           SUM(CASE WHEN tipo = 'recibe' THEN count ELSE 0 END) as recepciones
    FROM (
        SELECT abogado_cede as abogado, COUNT(*) as count, 'cede' as tipo
        FROM guardias
        GROUP BY abogado_cede
        UNION ALL
        SELECT abogado_recibe as abogado, COUNT(*) as count, 'recibe' as tipo
        FROM guardias
        GROUP BY abogado_recibe
    )
    GROUP BY abogado
    HAVING cesiones > 0 AND recepciones > 0
    ORDER BY cesiones DESC, recepciones DESC
    """)
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def desglose_por_abogado():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT abogado_cede as abogado, tipo_guardia, abogado_recibe as otro_abogado, COUNT(*) as cantidad, 'cede' as accion
    FROM guardias
    GROUP BY abogado_cede, tipo_guardia, abogado_recibe
    UNION ALL
    SELECT abogado_recibe as abogado, tipo_guardia, abogado_cede as otro_abogado, COUNT(*) as cantidad, 'recibe' as accion
    FROM guardias
    GROUP BY abogado_recibe, tipo_guardia, abogado_cede
    ORDER BY abogado, accion, tipo_guardia, otro_abogado
    """)
    resultados = cursor.fetchall()
    conn.close()

    desglose = defaultdict(lambda: {'cede': defaultdict(list), 'recibe': defaultdict(list)})
    for abogado, tipo_guardia, otro_abogado, cantidad, accion in resultados:
        desglose[abogado][accion][tipo_guardia].append((otro_abogado, cantidad))

    return dict(desglose)

def generar_tabla_html(resultados):
    tabla_html = "<table border='1'>"
    tabla_html += "<tr><th>N°</th><th>Abogado</th><th>Cantidad</th></tr>"
    
    for i, (abogado, count) in enumerate(resultados, 1):
        tabla_html += f"<tr><td>{i}</td><td>{html.escape(abogado)}</td><td>{count}</td></tr>"
    
    tabla_html += "</table>"
    return tabla_html

def generar_desglose_html(desglose):
    html_content = "<h2>Desglose por Abogado</h2>"
    for abogado, datos in desglose.items():
        html_content += f"<h3>{html.escape(abogado)}</h3>"
        
        total_cedidas = sum(cantidad for tipo in datos['cede'].values() for _, cantidad in tipo)
        html_content += f"<h4>Guardias Cedidas: ({total_cedidas})</h4>"
        if datos['cede']:
            html_content += "<ul>"
            for tipo_guardia, cesiones in datos['cede'].items():
                html_content += f"<li>{html.escape(tipo_guardia)}:"
                html_content += "<ul>"
                for otro_abogado, cantidad in cesiones:
                    html_content += f"<li>{cantidad} a {html.escape(otro_abogado)}</li>"
                html_content += "</ul></li>"
            html_content += "</ul>"
        else:
            html_content += "<p>No ha cedido guardias.</p>"

        total_recibidas = sum(cantidad for tipo in datos['recibe'].values() for _, cantidad in tipo)
        html_content += f"<h4>Guardias Recibidas: ({total_recibidas})</h4>"
        if datos['recibe']:
            html_content += "<ul>"
            for tipo_guardia, recepciones in datos['recibe'].items():
                html_content += f"<li>{html.escape(tipo_guardia)}:"
                html_content += "<ul>"
                for otro_abogado, cantidad in recepciones:
                    html_content += f"<li>{cantidad} de {html.escape(otro_abogado)}</li>"
                html_content += "</ul></li>"
            html_content += "</ul>"
        else:
            html_content += "<p>No ha recibido guardias.</p>"

    return html_content

def generar_html():
    cesiones_por_abogado = contar_cesiones_por_abogado()
    recepciones_por_abogado = contar_recepciones_por_abogado()
    ceden_y_reciben = abogados_ceden_y_reciben()
    desglose = desglose_por_abogado()

    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Análisis de Guardias de Abogados</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            h1, h2, h3, h4 { color: #333; }
            ul { padding-left: 20px; }
        </style>
    </head>
    <body>
        <h1>Análisis de Guardias de Abogados</h1>
    """

    html_content += "<h2>Cesiones por Abogado</h2>"
    html_content += generar_tabla_html(cesiones_por_abogado)

    html_content += "<h2>Recepciones por Abogado</h2>"
    html_content += generar_tabla_html(recepciones_por_abogado)

    html_content += "<h2>Abogados que Ceden y Reciben Guardias</h2>"
    html_content += generar_tabla_html(ceden_y_reciben)

    html_content += generar_desglose_html(desglose)

    html_content += """
    </body>
    </html>
    """

    with open('analisis_guardias_abogados.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("Se ha generado el archivo 'analisis_guardias_abogados.html' con los resultados.")

# Uso:
crear_base_de_datos()
cargar_datos_desde_csv('LLISTAT CESSIONS DE GUARDIA modif.csv')
generar_html()
