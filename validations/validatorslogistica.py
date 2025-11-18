from fastapi.responses import JSONResponse


def parsedRespondLogistica(status, data, message):
    if status == True:
        status_code = 200
    else:
        status_code = 200
    return JSONResponse(
        status_code=status_code,
        content={"data": data, "status": status, "message": message},
    )
