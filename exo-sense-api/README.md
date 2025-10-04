# Exoplanet Detection API

This project is an API for detecting exoplanets using machine learning techniques on light curve data. It is built using FastAPI and provides endpoints for uploading light curve files and receiving predictions.

## Project Structure

- `api/fastapi-backend.py`: Contains the FastAPI application for exoplanet detection, including model loading, data preprocessing, and prediction endpoints.
- `models/.gitkeep`: An empty file to ensure the `models` directory is tracked by Git.
- `requirements.txt`: Lists the Python dependencies required for the project.
- `runtime.txt`: Specifies the Python version for the deployment environment.
- `Procfile`: Defines the commands to run the FastAPI app on the Railway platform.
- `railway.json`: Contains configuration settings for Railway deployment.
- `.env.example`: A template for environment variables required by the application.
- `.gitignore`: Specifies files and directories to be ignored by Git.
- `README.md`: Documentation for the project.

## Setup Instructions

1. **Create a Railway Project**: Sign in to Railway and create a new project.

2. **Connect Your Repository**: Link your GitHub repository containing the project files to Railway.

3. **Configure Environment Variables**: Set up any necessary environment variables in the Railway dashboard, using the `.env.example` file as a reference.

4. **Specify the Runtime**: Ensure that the `runtime.txt` file specifies the correct Python version.

5. **Define the Procfile**: Make sure the `Procfile` contains the command to run your FastAPI app, typically something like:
   ```
   web: uvicorn api.fastapi-backend:app --host 0.0.0.0 --port $PORT
   ```

6. **Deploy**: Click the deploy button in the Railway dashboard to build and deploy your application.

7. **Access Your API**: Once deployed, you will receive a URL to access your FastAPI application.

## Usage

To use the API, send a POST request to the `/predict` endpoint with a light curve file (CSV or TXT format). The API will return a prediction indicating whether an exoplanet is detected, along with confidence levels and transit parameters.

## License

This project is licensed under the MIT License.