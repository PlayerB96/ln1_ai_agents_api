import mysql.connector
from mysql.connector import pooling, Error
import pyodbc
import configparser
import redis

# ============================================================
# 🔹 Configuración general (solo se lee una vez)
# ============================================================
config = configparser.ConfigParser()
config.read("config.ini")

# ============================================================
# 🔹 MySQL Pool (para LN1)
# ============================================================
try:
    mysql_pool_ln1 = pooling.MySQLConnectionPool(
        pool_name="ln1_pool",
        pool_size=5,  # Ajusta según tu carga concurrente
        pool_reset_session=True,
        host=config["MYSQL"]["host"],
        database=config["MYSQL"]["databaseln1"],
        user=config["MYSQL"]["user"],
        password=config["MYSQL"]["password"]
    )
except Error as e:
    print(f"⚠️ Error creando pool MySQL LN1: {e}")
    mysql_pool_ln1 = None

def connect_mysql_ln1():
    """Obtiene una conexión desde el pool MySQL LN1."""
    try:
        if mysql_pool_ln1 is None:
            raise Exception("MySQL LN1 pool no inicializado")
        connection = mysql_pool_ln1.get_connection()
        return connection
    except Error as e:
        print(f"❌ Error al conectar a MySQL LN1: {e}")
        raise


# ============================================================
# 🔹 SQL Server principal (con pooling habilitado)
# ============================================================
pyodbc.pooling = True  # ✅ Importante: activa el pooling global de pyodbc

def connect_sqlserver():
    """Conexión al SQL Server principal (usa pooling automático)."""
    try:
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={config['SQLSERVER']['server']};"
            f"Database={config['SQLSERVER']['database']};"
            f"UID={config['SQLSERVER']['user']};"
            f"PWD={config['SQLSERVER']['password']}"
        )
        conn = pyodbc.connect(connection_string, autocommit=False)
        return conn
    except pyodbc.Error as e:
        print(f"❌ Error al conectar a SQL Server principal: {e}")
        raise


# ============================================================
# 🔹 SQL Server Tracking (otro pool separado)
# ============================================================
def connect_sqlserver_tracking():
    """Conexión al SQL Server de tracking (usa pooling automático)."""
    try:
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={config['SQLSERVER_TRACKING']['server']};"
            f"Database={config['SQLSERVER_TRACKING']['database']};"
            f"UID={config['SQLSERVER_TRACKING']['user']};"
            f"PWD={config['SQLSERVER_TRACKING']['password']}"
        )
        conn = pyodbc.connect(connection_string, autocommit=False)
        return conn
    except pyodbc.Error as e:
        print(f"❌ Error al conectar a SQL Server Tracking: {e}")
        raise


# ============================================================
# 🔹 Redis (para OTP y verification_tokens)
# ============================================================
try:
    redis_client = redis.Redis(
        host=config["REDIS"]["host"],
        port=int(config["REDIS"]["port"]),
        password=config["REDIS"]["password"] or None,
        db=int(config["REDIS"]["db"]),
        decode_responses=True  # para obtener strings en lugar de bytes
    )
    # Verificar conexión
    redis_client.ping()
    print("✅ Conexión a Redis establecida correctamente")
except redis.RedisError as e:
    print(f"❌ Error conectando a Redis: {e}")
    redis_client = None


def get_redis():
    """Devuelve el cliente Redis para usarlo en tus servicios."""
    if redis_client is None:
        raise Exception("Redis no inicializado")
    return redis_client