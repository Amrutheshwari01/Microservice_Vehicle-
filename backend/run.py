import uvicorn
import os
import sys

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == "__main__":
    import socket

    port = int(os.getenv("PORT", 8000))
    # Test if port can be bound on Windows; if restricted or in-use, fallback gracefully to 8080
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
            test_sock.bind(("0.0.0.0", port))
    except OSError:
        for candidate in [8080, 8001, 8050, 5000]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
                    test_sock.bind(("0.0.0.0", candidate))
                    port = candidate
                    break
            except OSError:
                continue

    print(f"Starting AgriLink Commercial Fleet & Logistics Platform on http://localhost:{port}", flush=True)
    print(f"Interactive Swagger Documentation available at http://localhost:{port}/docs", flush=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
