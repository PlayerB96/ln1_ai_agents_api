

class ResponseSIS:
    @staticmethod
    def formatDataUsersBiotime(data):
        try:
            # Función desactivada - referencias a database.py removidas
            # Retorna los datos sin modificaciones
            for item in data:
                item["Con_Descanso"] = None  # Placeholder
            return data

        except Exception as err:
            print(f"Error: {err}")
            raise
