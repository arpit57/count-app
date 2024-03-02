import os
import uvicorn
#testchange
# Get the directory where the script is running
base_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the paths to your SSL files
ssl_keyfile_path = os.path.join(base_dir, "ssl_key.pem")
ssl_certfile_path = os.path.join(base_dir, "ssl_certificate.pem")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
        # ,
        # ssl_keyfile=ssl_keyfile_path,
        # ssl_certfile=ssl_certfile_path
    )
