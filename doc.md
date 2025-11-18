# DOCUMENTACIÓN : REST-API-BOTS

## DESCRIPCIÓN:
REST-API que consume informacion desde las bases de datos de INFOSAP e INTRANET para poder hacer validaciones y actualizaciones en rango de fechas especificos.

## DEPLOYMENT:

EJECUTAR SCRIPT CON DOCKER: 

PASO 1 : Generar imagen con :

```docker build -t <nombre> .```

PASO 2 : Crear contenedor con la imagen :

```docker run -dp 8000:8000 <nombre>```



## UBICACIÓN
SERVIDOR: 67.207.87.64

## BASE DE DATOS SQL SERVER
SERVER : 172.16.0.132
BD : DBMSTR
USER: infosap_user
PASS: 

## BASE DE DATOS MYSQL
SERVER : 172.16.0.134
BD : lanumerouno
USER: infosap_user
PASS: 

## GITHUB - REPOSITORIO
repo: https://github.com/PlayerB96/API_LN1_FASTAPI.git
  
## ENDPOINTS POSTMAN
https://documenter.getpostman.com/view/18269677/2sAYkAQ2pe

## FASTAPI-DOCUMENTATION
http://172.16.0.140:8001/docs