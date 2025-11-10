from dotenv import load_dotenv
load_dotenv()

from app.main import initialize_application

app = initialize_application()


if __name__ =="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)