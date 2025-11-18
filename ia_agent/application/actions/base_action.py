from http.client import HTTPException


class BaseAction:
    required_params: list = []

    def validate_params(self, params):
        missing = [p for p in self.required_params if p not in params]
        if missing:
            raise HTTPException(status_code=400, detail=f"Faltan parámetros: {missing}")
        return True