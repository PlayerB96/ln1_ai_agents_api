#!/usr/bin/env python3
"""
Script de validación para la acción document_modules.
Verifica que toda la integración esté correcta.
"""

import json
import sys
from pathlib import Path

def check_file_exists(path: str, description: str) -> bool:
    """Verifica si un archivo existe."""
    exists = Path(path).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def check_imports() -> bool:
    """Verifica que los imports funcionen."""
    print("\n📦 Validando imports...")
    try:
        from ia_agent.application.actions.document_modules_action import DocumentModulesAction
        print("✅ DocumentModulesAction importa correctamente")
        
        from ia_agent.application.orchestrator.action_loader import ActionFactory
        print("✅ ActionFactory importa correctamente")
        
        handler = ActionFactory.get_handler_class("document_modules")
        if handler:
            print("✅ ActionFactory.get_handler_class('document_modules') retorna la clase")
            return True
        else:
            print("❌ ActionFactory no tiene registrada la acción 'document_modules'")
            return False
            
    except Exception as e:
        print(f"❌ Error en imports: {e}")
        return False

def check_config_json() -> bool:
    """Verifica actions_config.json."""
    print("\n📋 Validando actions_config.json...")
    try:
        with open("actions_config.json", "r") as f:
            config = json.load(f)
        
        # Verificar que document_modules existe
        if "document_modules" not in config:
            print("❌ 'document_modules' no está en actions_config.json")
            return False
        
        doc_mod = config["document_modules"]
        
        # Validar estructura
        required_keys = ["handler", "area", "tags", "description", "parameters"]
        for key in required_keys:
            if key not in doc_mod:
                print(f"❌ Falta clave '{key}' en configuración")
                return False
        
        if doc_mod["handler"] != "document_modules":
            print("❌ handler debe ser 'document_modules'")
            return False
        
        print("✅ actions_config.json está bien formado")
        print(f"   - Handler: {doc_mod['handler']}")
        print(f"   - Área: {doc_mod['area']}")
        print(f"   - Tags: {', '.join(doc_mod['tags'])}")
        print(f"   - Parámetros configurados: {len(doc_mod['parameters']['properties'])}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON inválido: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_action_instantiation() -> bool:
    """Verifica que se pueda instanciar la acción."""
    print("\n⚙️  Validando instantiación...")
    try:
        from ia_agent.application.actions.document_modules_action import DocumentModulesAction
        
        action = DocumentModulesAction()
        print("✅ DocumentModulesAction se instancia correctamente")
        
        # Verificar que tiene el método execute
        if not hasattr(action, "execute"):
            print("❌ DocumentModulesAction no tiene método execute()")
            return False
        
        print("✅ DocumentModulesAction tiene método execute()")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_action_execution() -> bool:
    """Verifica que la acción se ejecute correctamente."""
    print("\n🚀 Validando ejecución...")
    try:
        from ia_agent.application.actions.document_modules_action import DocumentModulesAction
        
        action = DocumentModulesAction()
        
        # Test 1: Sin parámetros requeridos
        result = action.execute({})
        if result["status"] == False:
            print("✅ Validación de parámetros requeridos funciona")
        else:
            print("⚠️  Esperaba error sin parámetros requeridos")
        
        # Test 2: Con parámetros válidos
        result = action.execute({
            "project_name": "TestProject",
            "format": "markdown",
            "modules": ["module1", "module2"]
        })
        
        if result["status"] == True:
            print("✅ Ejecución con parámetros válidos funciona")
            
            # Verificar estructura de respuesta
            if "data" in result and "task_id" in result["data"]:
                print("✅ Respuesta contiene task_id")
            if "data" in result and "trace_id" in result["data"]:
                print("✅ Respuesta contiene trace_id")
            
            return True
        else:
            print(f"❌ Ejecución falló: {result.get('msg', 'Sin mensaje')}")
            return False
            
    except Exception as e:
        print(f"❌ Error en ejecución: {e}")
        return False

def check_factory_integration() -> bool:
    """Verifica que ActionFactory integre correctamente."""
    print("\n🔗 Validando integración con ActionFactory...")
    try:
        from ia_agent.application.orchestrator.action_loader import ActionFactory
        
        # Obtener la clase
        handler_class = ActionFactory.get_handler_class("document_modules")
        if not handler_class:
            print("❌ ActionFactory no retorna clase para 'document_modules'")
            return False
        
        print("✅ ActionFactory.get_handler_class() retorna DocumentModulesAction")
        
        # Crear instancia con factory
        instance = ActionFactory.create("document_modules")
        if not instance:
            print("❌ ActionFactory.create() retorna None")
            return False
        
        print("✅ ActionFactory.create() crea instancia correctamente")
        
        # Verificar que es la clase correcta
        if not hasattr(instance, "execute"):
            print("❌ Instancia no tiene método execute()")
            return False
        
        print("✅ Instancia tiene método execute()")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Ejecuta todas las validaciones."""
    print("=" * 80)
    print("🔍 VALIDACIÓN DE ACCIÓN document_modules")
    print("=" * 80)
    
    checks = [
        ("Archivos necesarios", lambda: all([
            check_file_exists(
                "ia_agent/application/actions/document_modules_action.py",
                "Archivo de acción"
            ),
            check_file_exists(
                "actions_config.json",
                "Configuración de acciones"
            ),
        ])),
        ("Configuración JSON", check_config_json),
        ("Imports", check_imports),
        ("Instantiación", check_action_instantiation),
        ("Ejecución", check_action_execution),
        ("Integración Factory", check_factory_integration),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            results[name] = False
    
    # Resumen final
    print("\n" + "=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} validaciones pasaron")
    
    if passed == total:
        print("\n🎉 ¡Todas las validaciones pasaron!")
        print("\n✨ La acción document_modules está lista para usar.")
        print("\n📝 Próximos pasos:")
        print("   1. Iniciar el servidor: uvicorn app:app --reload")
        print("   2. Enviar prompt al endpoint /ia/agent")
        print("   3. Ver DOCUMENT_MODULES_PROMPTS.py para ejemplos")
        return 0
    else:
        print("\n⚠️  Hay validaciones que fallaron. Revisa los errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
