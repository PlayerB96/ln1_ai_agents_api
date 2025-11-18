from database import connect_mysql_ln1


class ResponseSIS:
    @staticmethod
    def formatDataUsersBiotime(data):
        try:
            conn = connect_mysql_ln1()  # Conectar a MySQL
            if conn is None:
                return
            cursor = conn.cursor()

            # Extraer los ID de usuario, ID de área y centro_labores desde los datos
            id_usuarios = [str(item["Id_Usuario"]) for item in data]
            id_areas = [str(item["Id_Area"]) for item in data]
            centro_labores = [str(item["Centro_Labores"]) for item in data]

            id_usuarios_str = ",".join(["%s"] * len(id_usuarios))
            id_areas_str = ",".join(["%s"] * len(id_areas))
            centro_labores_str = ",".join(["%s"] * len(centro_labores))

            # Consulta para obtener el campo con_descanso de los usuarios con filtros adicionales
            query_turno = f"""
                SELECT ac.id_usuario, 
                    ac.con_descanso
                FROM asistencia_colaborador ac
                LEFT JOIN users us ON ac.id_usuario = us.id_usuario
                LEFT JOIN puesto p ON us.id_puesto = p.id_puesto  
                WHERE ac.id_usuario IN ({id_usuarios_str}) 
                AND p.id_area IN ({id_areas_str})  
                AND ac.centro_labores IN ({centro_labores_str})
            """
            # Ejecutar la consulta
            cursor.execute(query_turno, tuple(id_usuarios + id_areas + centro_labores))
            turnos = cursor.fetchall()

            # Convertir el resultado de la consulta en un diccionario para acceso rápido
            turnos_dict = {str(row[0]): row[1] for row in turnos}

            # Actualizar el array de datos con el campo "con_descanso"
            for item in data:
                id_usuario = str(item["Id_Usuario"])
                if id_usuario in turnos_dict:
                    item["Con_Descanso"] = turnos_dict[
                        id_usuario
                    ]  # Asignar el valor de con_descanso
                else:
                    item["Con_Descanso"] = None  # Si no se encuentra, asignar None

            conn.close()  # Cierra la conexión
            return data  # Devolver el array con los campos actualizados

        except Exception as err:
            print(f"Error: {err}")
            raise
