from fastapi.responses import JSONResponse
# Basic custom error handler for validation errors
async def validation_exception_handler(req, exc):
    errors = {}
    for error in exc.errors():
        print(f" this is error {error}")
        errors[error['loc'][-1]] = error['msg']
    return JSONResponse({ "message": "Validation failed", "errors": errors },status_code=422)
# -------------------------------------------------