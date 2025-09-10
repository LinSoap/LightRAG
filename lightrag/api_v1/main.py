from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lightrag.api_v1.routers.documents import create_document_routers
from lightrag.api_v1.routers.common import router as common_router

app = FastAPI()

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the common router
app.include_router(common_router)
app.include_router(create_document_routers())


def main():
    import uvicorn

    # Disable uvicorn's own access log and prevent it from reconfiguring logging
    # so our custom API logger and middleware control output and avoid duplicates.
    uvicorn.run(
        "lightrag.api_v1.main:app",
        host="0.0.0.0",
        port=8002,
        access_log=True,
    )


if __name__ == "__main__":
    main()
