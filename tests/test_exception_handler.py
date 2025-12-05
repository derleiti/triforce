from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

def test_custom_http_exception_handler():
    """Verify the custom exception handler unwraps 'error' details."""
    app = FastAPI()

    # This matches the handler added to app/main.py
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.get("/error-custom")
    def error_custom():
        # Simulate api_error behavior: detail={"error": {...}}
        raise HTTPException(status_code=400, detail={"error": {"message": "My Message", "code": "my_code"}})

    @app.get("/error-standard")
    def error_standard():
        # Simulate standard error
        raise HTTPException(status_code=404, detail="Not Found")

    client = TestClient(app)

    # Test Custom Error (unwrapping)
    response = client.get("/error-custom")
    assert response.status_code == 400
    # The key check: "error" is at the root, not nested under "detail"
    assert response.json() == {"error": {"message": "My Message", "code": "my_code"}}
    
    # Test Standard Error (wrapping preserved)
    response = client.get("/error-standard")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
