import json
from datetime import datetime
from database import connect_mysql_ln1

# Función para guardar el log en la base de datos MySQL
def logErrorJson(error_message, error_type, origin="API_LN1_FASTAPI"):
    try:
        conn = connect_mysql_ln1()  # Conectar a MySQL
        if conn is None:
            print("No se pudo conectar a la base de datos para registrar el error.")
            return

        cursor = conn.cursor()

        # Inserta los campos definidos en la nueva tabla
        insert_query = """
            INSERT INTO tb_logger_api (origin, error_message, error_type)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (origin, error_message, error_type))

        conn.commit()  # Confirma los cambios
        conn.close()   # Cierra la conexión

    except Exception as log_err:
        print(f"Error al escribir el log en la base de datos: {log_err}")
