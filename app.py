from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
import random


app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta'

# Configurar la conexión a la base de datos MySQL
app.config['DB_USERNAME'] = 'root'  # Reemplaza con tu nombre de usuario de MySQL
app.config['DB_PASSWORD'] = ''  # Reemplaza con tu contraseña de MySQL
app.config['DB_HOST'] = 'localhost'
app.config['DB_NAME'] = 'examen_ingles'


# Función para establecer la conexión a la base de datos
def get_db():
    return pymysql.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USERNAME'],
        password=app.config['DB_PASSWORD'],
        db=app.config['DB_NAME'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def index():
    # Obtener el ID del usuario desde la sesión
    usuario_id = session.get('usuario_id')
    
    # Definir intentos_registrados_prueba
    intentos_registrados_prueba_var = obtener_numero_intentos(usuario_id)
    
    return render_template('index.html', intentos_registrados_prueba=intentos_registrados_prueba_var)


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        
        # Verificar si el correo electrónico ya está en uso
        with get_db().cursor() as cursor:
            sql = "SELECT * FROM usuarios WHERE CorreoElectronico = %s"
            cursor.execute(sql, (correo,))
            usuario_existente = cursor.fetchone()
        
        if usuario_existente:
            # El correo electrónico ya está en uso, redirigir a la página de registro con un mensaje de error
            flash('El correo electrónico ya está registrado. Por favor, utiliza otro correo electrónico.', 'error')
            return redirect(url_for('registro'))
        else:
            # Insertar el nuevo usuario en la base de datos
            with get_db().cursor() as cursor:
                sql = "INSERT INTO usuarios (Nombre, CorreoElectronico) VALUES (%s, %s)"
                cursor.execute(sql, (nombre, correo))
            
            # Obtener el usuario recién registrado
            with get_db().cursor() as cursor:
                sql = "SELECT * FROM usuarios WHERE CorreoElectronico = %s"
                cursor.execute(sql, (correo,))
                usuario = cursor.fetchone()
                
            # Iniciar sesión y guardar información del usuario en la sesión
            session['usuario_id'] = usuario['UsuarioID']
            session['nombre'] = usuario['Nombre']
            session['correo'] = usuario['CorreoElectronico']
            
            # Redirigir al usuario a la página de inicio
            return redirect(url_for('iniciar'))
            
    return render_template('registro.html')



@app.route('/resultados_total')
def resultados_total():
    # Obtener el correo electrónico del usuario desde la sesión
    correo = session.get('correo')
    print("Correo electrónico:", correo)  # Para depuración
    
    # Obtener el UsuarioID correspondiente al correo electrónico
    with get_db().cursor() as cursor:
        sql = "SELECT UsuarioID FROM usuarios WHERE CorreoElectronico = %s"
        cursor.execute(sql, (correo,))
        usuario = cursor.fetchone()
    
    if usuario:
        usuario_id = usuario['UsuarioID']
        
        # Obtener todos los simuladores asociados con el UsuarioID
        with get_db().cursor() as cursor:
            sql = "SELECT * FROM simuladores WHERE UsuarioID = %s"
            cursor.execute(sql, (usuario_id,))
            resultados = cursor.fetchall()
        
        print("Resultados:", resultados)  # Para depuración
        
        if resultados:
            return render_template('resultados_total.html', resultados=resultados)
        else:
            return render_template('no_resultados.html')  # Renderizar la plantilla no_resultados.html si no hay resultados
    else:
        # El usuario no fue encontrado, renderizar o manejar el error apropiadamente
        flash('No se encontró el usuario.', 'error')
        return render_template('no_resultados.html')  # Renderizar la plantilla no_resultados.html si no se encuentra el usuario




@app.route('/iniciar')
def iniciar():
    # Obtener el ID del usuario desde la sesión
    usuario_id = session.get('usuario_id')
    
    # Definir intentos_registrados_prueba
    intentos_registrados_prueba_var = obtener_numero_intentos(usuario_id)
    intentos_registrados_simulador_final_var=obtener_numero_intentos_simulador_final(usuario_id)
    return render_template('iniciar.html', intentos_registrados_prueba=intentos_registrados_prueba_var,intentos_registrados_simulador_final=intentos_registrados_simulador_final_var)

@app.route('/return_resultados')
def return_resultados():
    puntaje = request.args.get('puntaje')
    nivel_habilidad = request.args.get('nivel_habilidad')
    resultado = request.args.get('resultado')
    calificacion = request.args.get('calificacion') 
    nivel = request.args.get('nivel')
    # Aquí puedes calcular el número de intentos registrados por el usuario
    usuario_id = session.get('usuario_id')
    intentos_registrados_prueba_var = obtener_numero_intentos(usuario_id)
    intentos_registrados_simulador_final_var = obtener_numero_intentos_simulador_final(usuario_id)  # Calcula los intentos del simulador final
    
    return render_template('return_resultados.html', puntaje=puntaje, nivel_habilidad=nivel_habilidad, resultado=resultado,
                           nombre=session.get('nombre'), correo=session.get('correo'), intentos_registrados_prueba=intentos_registrados_prueba_var,
                           intentos_registrados_simulador_final=intentos_registrados_simulador_final_var, calificacion=calificacion,nivel=nivel)  # Incluye la calificación en la renderización de la plantilla


def generar_opciones(respuesta_correcta, respuestas_incorrectas):
    opciones = [respuesta_correcta] + respuestas_incorrectas
    random.shuffle(opciones)
    return opciones

def obtener_preguntas():
    with get_db().cursor() as cursor:
        sql = "SELECT PreguntaID, Texto, RespuestaCorrecta FROM preguntas ORDER BY RAND() LIMIT 20"
        cursor.execute(sql)
        preguntas_raw = cursor.fetchall()
    
    preguntas = []
    for pregunta in preguntas_raw:
        opciones = generar_opciones(pregunta['RespuestaCorrecta'], obtener_respuestas_incorrectas(pregunta['RespuestaCorrecta']))
        preguntas.append({
            'PreguntaID': pregunta['PreguntaID'],
            'PreguntaTexto': pregunta['Texto'],
            'opciones': opciones
        })
    
    return preguntas

def obtener_preguntas_simulador_final():
    with get_db().cursor() as cursor:
        # Selecciona preguntas únicas aleatorias
        sql = "SELECT PreguntaID, Texto, RespuestaCorrecta FROM preguntas ORDER BY RAND() LIMIT 40"
        cursor.execute(sql)
        preguntas_raw = cursor.fetchall()

    preguntas = []
    for pregunta in preguntas_raw:
        opciones = generar_opciones(pregunta['RespuestaCorrecta'], obtener_respuestas_incorrectas(pregunta['RespuestaCorrecta']))
        preguntas.append({
            'PreguntaID': pregunta['PreguntaID'],
            'PreguntaTexto': pregunta['Texto'],
            'RespuestaCorrecta': pregunta['RespuestaCorrecta'],  # Conservar la respuesta correcta para verificación
            'opciones': opciones
        })

    return preguntas


def obtener_respuestas_incorrectas(respuesta_correcta):
    # Aquí deberías implementar la lógica para obtener respuestas incorrectas diferentes de la respuesta correcta
    with get_db().cursor() as cursor:
        cursor.execute("SELECT RespuestaCorrecta FROM preguntas WHERE RespuestaCorrecta != %s ORDER BY RAND() LIMIT 3", (respuesta_correcta,))
        resultados = cursor.fetchall()
    return [res['RespuestaCorrecta'] for res in resultados if res['RespuestaCorrecta'] != respuesta_correcta]



def obtener_numero_intentos(usuario_id):
    with get_db().cursor() as cursor:
        sql = "SELECT COUNT(*) AS num_intentos FROM simuladores WHERE UsuarioID = %s AND TipoSimulador='practica'"
        cursor.execute(sql, (usuario_id,))
        resultado = cursor.fetchone()
        num_intentos = resultado['num_intentos']
    return num_intentos


@app.route('/test_prueba', methods=['GET', 'POST'])
def test_prueba():
    usuario_id = session.get('usuario_id')
    preguntas = obtener_preguntas()

    if request.method == 'POST':
        print("Datos del formulario recibidos:", request.form)
        puntos = 0
        errores = []

        for pregunta_id, respuesta_usuario in request.form.items():
            pregunta_id = int(pregunta_id)
            with get_db().cursor() as cursor:
                cursor.execute("SELECT RespuestaCorrecta FROM preguntas WHERE PreguntaID = %s", (pregunta_id,))
                respuesta = cursor.fetchone()

            if respuesta:
                respuesta_correcta = respuesta['RespuestaCorrecta']
                if respuesta_usuario == respuesta_correcta:
                    puntos += 1
                else:
                    errores.append((pregunta_id, respuesta_usuario, respuesta_correcta))
            else:
                errores.append((pregunta_id, respuesta_usuario, "No se encontró respuesta en la base de datos"))

        calificacion = (puntos / len(preguntas)) * 100 if preguntas else 0
        resultado = 'Aprobado' if calificacion >= 70 else 'Reprobado'
        nivel = calcular_nivel(calificacion)

        with get_db().cursor() as cursor:
            cursor.execute(
                "INSERT INTO simuladores (UsuarioID, TipoSimulador, Calificacion, Resultado, Nivel) VALUES (%s, 'practica', %s, %s, %s)",
                (usuario_id, calificacion, resultado, nivel)
            )

        return redirect(url_for('return_resultados', puntaje=puntos, nivel_habilidad=calificacion, resultado=resultado, calificacion=calificacion, nivel=nivel))

    return render_template('test_prueba.html', preguntas=preguntas, nombre=session.get('nombre'), correo=session.get('correo'))

@app.route('/test_final', methods=['GET', 'POST'])
def test_final():
    usuario_id = session.get('usuario_id')
    preguntas = obtener_preguntas_simulador_final()

    if request.method == 'POST':
        print("Datos del formulario recibidos:", request.form)
        puntos = 0
        errores = []

        for pregunta_id, respuesta_usuario in request.form.items():
            pregunta_id = int(pregunta_id)
            with get_db().cursor() as cursor:
                cursor.execute("SELECT RespuestaCorrecta FROM preguntas WHERE PreguntaID = %s", (pregunta_id,))
                respuesta = cursor.fetchone()

            if respuesta:
                respuesta_correcta = respuesta['RespuestaCorrecta']
                if respuesta_usuario == respuesta_correcta:
                    puntos += 1
                else:
                    errores.append((pregunta_id, respuesta_usuario, respuesta_correcta))
            else:
                errores.append((pregunta_id, respuesta_usuario, "No se encontró respuesta en la base de datos"))

        calificacion = (puntos / len(preguntas)) * 100 if preguntas else 0
        resultado = 'Aprobado' if calificacion >= 70 else 'Reprobado'
        nivel = calcular_nivel(calificacion)

        with get_db().cursor() as cursor:
            cursor.execute(
                "INSERT INTO simuladores (UsuarioID, TipoSimulador, Calificacion, Resultado, Nivel) VALUES (%s, 'final', %s, %s, %s)",
                (usuario_id, calificacion, resultado, nivel)
            )

        return redirect(url_for('return_resultados', puntaje=puntos, nivel_habilidad=calificacion, resultado=resultado, calificacion=calificacion, nivel=nivel))

    return render_template('test_final.html', preguntas=preguntas)



def calcular_nivel_habilidad(calificacion):
    # Ajustar la calificación al rango del 1 al 100
    calificacion_ajustada = min(max(calificacion, 0), 100)
    return calificacion_ajustada

def calcular_nivel(calificacion):
    if 70 <= calificacion < 81:
        return 'Básico'
    elif 81 <= calificacion < 91:
        return 'Intermedio'
    elif 91 <= calificacion <= 100:
        return 'Avanzado'
    return 'No Aprobado'


# Función para registrar los intentos del usuario en la base de datos para el simulador final
def obtener_numero_intentos_simulador_final(usuario_id):
    # Aquí interactúas con la base de datos para obtener el número de intentos registrados por el usuario en el simulador final
    with get_db().cursor() as cursor:
        sql = "SELECT COUNT(*) AS num_intentos FROM simuladores WHERE UsuarioID = %s AND TipoSimulador = 'final'"
        cursor.execute(sql, (usuario_id,))
        resultado = cursor.fetchone()
        num_intentos = resultado['num_intentos']
    return num_intentos



if __name__ == '__main__':
    app.run(debug=True)