import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        ssl_keyfile="/home/arpit57/countApp/app/ssl_key.pem",
        ssl_certfile="/home/arpit57/countApp/app/ssl_certificate.pem"
    )
