"""
Clase base para todas las acciones del sistema.
Proporciona funcionalidad común y estructura para las acciones.
"""
from fastapi import HTTPException
from typing import Dict, Any, List


class BaseAction:
    """
    Clase base abstracta para acciones.
    Define la interfaz y funcionalidad común.
    """
    
    required_params: List[str] = []
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Valida que los parámetros requeridos estén presentes.
        
        Args:
            params: Diccionario de parámetros
            
        Returns:
            True si la validación es exitosa
            
        Raises:
            HTTPException: Si faltan parámetros requeridos
        """
        missing = [p for p in self.required_params if p not in params or not params[p]]
        if missing:
            raise HTTPException(
                status_code=400, 
                detail=f"Faltan parámetros requeridos: {', '.join(missing)}"
            )
        return True
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la acción. Debe ser implementado por las subclases.
        
        Args:
            params: Parámetros de la acción
            
        Returns:
            Dict con el resultado de la acción
        """
        raise NotImplementedError("Las subclases deben implementar execute()")
    
    def format_response(
        self, 
        data: Any, 
        status: bool = True, 
        msg: str = ""
    ) -> Dict[str, Any]:
        """
        Formatea la respuesta de manera consistente.
        
        Args:
            data: Datos de la respuesta
            status: Estado de la operación
            msg: Mensaje descriptivo
            
        Returns:
            Dict con formato estándar de respuesta
        """
        return {
            "status": status, 
            "msg": msg, 
            "data": data
        }
