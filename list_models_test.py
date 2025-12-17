import google.generativeai as genai
from configparser import ConfigParser
import sys

# Leer config
config = ConfigParser()
config.read("config.ini")
api_key = config.get("GEMINI", "api_key", fallback=None)

if not api_key:
    print("❌ No API key found in config.ini")
    sys.exit(1)

genai.configure(api_key=api_key)

print("🔍 Listando modelos disponibles...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"❌ Error listando modelos: {e}")
