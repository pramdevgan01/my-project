# Python - FastAPI with Pydantic

This is a simple Python - FastAPI application with Pydantic validation. This application serves as a basic template for building REST APIs using Python, FastAPI framework, and Pydantic for data validation.

## What does this application do?

This application serves a REST API that listens on defined port, default: `8000`.

# How to run?

You can run the application in one of the following ways:

1. Press `F5`. This will start the application with auto-reload enabled.

2. Open a terminal by going to 'View' -> 'Terminal'. Then, run following command:
   > `fastapi dev main.py --host 0.0.0.0 --port 8000`

This will start the application in development mode with auto-reload.

## Via curl command:

1. Open a terminal.
2. Type the following command:
   > `curl http://localhost:8000`
3. Press 'Enter' to make the request.

## Interactive API Documentation:

FastAPI automatically generates interactive API documentation:

- Swagger UI: `http://localhost:8000/docs` or `https://<STUDIO_HOST_ID>-8000.<STUDIO_DOMAIN>/docs`
- ReDoc: `http://localhost:8000/redoc` or `https://<STUDIO_HOST_ID>-8000.<STUDIO_DOMAIN>/redoc`

Visit [FastAPI Documentation](https://fastapi.tiangolo.com/) for more information.

## FAQs & Debugging

### 1. I do not see browser in my workspace

Studio will automatically open the app in a new browser tab. If not, you can use the following steps to open the simple browser:

1. From VS Code command palette (`Ctrl/Cmd + Shift + P`), run **Studio Manager: SimpleBrowser Default URL** command. This will open the app in a new browser tab.

2. Your app runs on a hosted environment which can be accessed using the host id and port provided in the file **.vscode/.studio/studio-env.json**. Use these values to create the URL as follows:
   `https://<STUDIO_HOST_ID>-8000.<STUDIO_DOMAIN>`


Happy coding!
