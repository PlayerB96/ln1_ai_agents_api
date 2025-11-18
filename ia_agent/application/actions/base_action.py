from fastapi import HTTPException

class BaseAction:
    required_params: list = []
    desc: str = "Sin descripción"

    def validate_params(self, params):
        missing = [p for p in self.required_params if p not in params]
        if missing:
            raise HTTPException(status_code=400, detail=f"Faltan parámetros: {missing}")
        return True

    def safe_execute(self, params):
        try:
            self.validate_params(params)
            return self.execute(params)
        except HTTPException as e:
            raise e
        except Exception as e:
            return {"status": False, "msg": str(e)}

    def log(self, msg):
        print(f"[{self.__class__.__name__}] {msg}")

    def format_response(self, data, status=True, msg=None):
        return {"status": status, "msg": msg or "", "data": data}

    def description(self):
        return {
            "name": self.__class__.__name__,
            "params": self.required_params,
            "description": self.desc
        }
