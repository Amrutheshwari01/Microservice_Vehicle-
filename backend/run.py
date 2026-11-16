import uvicorn
import os
import sys

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting AgriLink Commercial Fleet & Logistics Platform on http://localhost:{port}", flush=True)
    print(f"Interactive Swagger Documentation available at http://localhost:{port}/docs", flush=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
