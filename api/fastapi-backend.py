from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import pandas as pd
from typing import Optional
import io
import joblib
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(
    title="Exoplanet Detection API",
    description="AI-powered exoplanet detection using NASA data",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
        "*"  # Remove this in production, specify exact domains
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response Model
class PredictionResponse(BaseModel):
    exoplanetDetected: bool
    confidence: float
    transitDepth: Optional[float] = None
    orbitalPeriod: Optional[float] = None
    fileName: str
    message: Optional[str] = None

# Global variable for model (load at startup)
model = None
MODEL_PATH = Path("models/exoplanet_model.pkl")

@app.on_event("startup")
async def load_model():
    """Load the trained model at startup"""
    global model
    try:
        if MODEL_PATH.exists():
            model = joblib.load(MODEL_PATH)
            print(f"✓ Model loaded successfully from {MODEL_PATH}")
        else:
            print(f"⚠ Warning: Model file not found at {MODEL_PATH}")
            print("  API will run in demo mode with mock predictions")
    except Exception as e:
        print(f"⚠ Error loading model: {e}")
        print("  API will run in demo mode with mock predictions")

def preprocess_light_curve(data: pd.DataFrame) -> np.ndarray:
    """
    Preprocess light curve data for model prediction
    
    Expected columns: 'time', 'flux' or similar
    Adjust based on your actual data format
    """
    try:
        # Common column name variations
        time_cols = ['time', 'TIME', 'Time', 'JD', 'BJD']
        flux_cols = ['flux', 'FLUX', 'Flux', 'SAP_FLUX', 'PDCSAP_FLUX']
        
        # Find the actual column names
        time_col = next((col for col in time_cols if col in data.columns), None)
        flux_col = next((col for col in flux_cols if col in data.columns), None)
        
        if not time_col or not flux_col:
            # If columns not found, use first two columns
            if len(data.columns) >= 2:
                time_col, flux_col = data.columns[0], data.columns[1]
            else:
                raise ValueError("Insufficient columns in data")
        
        # Extract and clean data
        flux = data[flux_col].values
        
        # Remove NaN values
        flux = flux[~np.isnan(flux)]
        
        # Normalize flux
        flux_normalized = (flux - np.median(flux)) / np.std(flux)
        
        # Feature engineering - extract statistical features
        features = [
            np.mean(flux_normalized),
            np.std(flux_normalized),
            np.min(flux_normalized),
            np.max(flux_normalized),
            np.percentile(flux_normalized, 25),
            np.percentile(flux_normalized, 75),
            len(flux_normalized),
            np.sum(flux_normalized < -2),  # Number of significant dips
        ]
        
        return np.array(features).reshape(1, -1)
    
    except Exception as e:
        raise ValueError(f"Error preprocessing data: {str(e)}")

def calculate_transit_params(data: pd.DataFrame) -> tuple:
    """
    Calculate basic transit parameters from light curve
    Returns: (transit_depth, orbital_period_estimate)
    """
    try:
        # Find flux column
        flux_cols = ['flux', 'FLUX', 'Flux', 'SAP_FLUX', 'PDCSAP_FLUX']
        flux_col = next((col for col in flux_cols if col in data.columns), data.columns[1] if len(data.columns) > 1 else None)
        
        if flux_col is None:
            return 0.0, 0.0
        
        flux = data[flux_col].values
        flux = flux[~np.isnan(flux)]
        
        # Calculate transit depth (simplified)
        baseline = np.percentile(flux, 90)
        minimum = np.percentile(flux, 10)
        transit_depth = (baseline - minimum) / baseline
        
        # Estimate orbital period (simplified - detect periodic dips)
        # This is a placeholder - real implementation would use autocorrelation
        orbital_period = np.random.uniform(5, 20)  # Mock value
        
        return float(transit_depth), float(orbital_period)
    
    except Exception as e:
        return 0.0, 0.0

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Exoplanet Detection API is running",
        "status": "healthy",
        "model_loaded": model is not None
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model_status": "loaded" if model is not None else "not_loaded",
        "api_version": "1.0.0"
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict_exoplanet(file: UploadFile = File(...)):
    """
    Predict if uploaded light curve data contains an exoplanet transit
    
    Accepts: CSV, TXT files with time-series flux data
    Returns: Prediction results with confidence and transit parameters
    """
    
    # Validate file type
    if not file.filename.endswith(('.csv', '.txt', '.dat')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload CSV or TXT files."
        )
    
    try:
        # Read file content
        contents = await file.read()
        
        # Parse CSV/TXT data
        try:
            data = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        except:
            # Try space or tab separated
            data = pd.read_csv(
                io.StringIO(contents.decode('utf-8')),
                delim_whitespace=True
            )
        
        # Validate data
        if len(data) < 10:
            raise HTTPException(
                status_code=400,
                detail="Insufficient data points. Please provide more data."
            )
        
        # Preprocess data
        features = preprocess_light_curve(data)
        
        # Make prediction
        if model is not None:
            # Use actual model
            prediction = model.predict(features)[0]
            confidence = float(model.predict_proba(features)[0][prediction] * 100)
        else:
            # Demo mode - mock prediction based on data characteristics
            flux_col = data.columns[1] if len(data.columns) > 1 else data.columns[0]
            flux = data[flux_col].values
            flux_std = np.std(flux[~np.isnan(flux)])
            
            # Simple heuristic: high variance might indicate transits
            prediction = 1 if flux_std > np.median(flux) * 0.01 else 0
            confidence = float(np.random.uniform(70, 95) if prediction else np.random.uniform(60, 85))
        
        # Calculate transit parameters
        transit_depth, orbital_period = calculate_transit_params(data)
        
        # Prepare response
        response = PredictionResponse(
            exoplanetDetected=bool(prediction),
            confidence=round(confidence, 2),
            transitDepth=round(transit_depth, 4) if prediction else None,
            orbitalPeriod=round(orbital_period, 2) if prediction else None,
            fileName=file.filename,
            message="Analysis complete" if model else "Demo mode - train and load a model for accurate predictions"
        )
        
        return response
    
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="Empty or invalid file")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

@app.post("/batch-predict")
async def batch_predict(files: list[UploadFile] = File(...)):
    """
    Process multiple light curve files at once
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files allowed per batch"
        )
    
    results = []
    for file in files:
        try:
            result = await predict_exoplanet(file)
            results.append(result)
        except Exception as e:
            results.append({
                "fileName": file.filename,
                "error": str(e)
            })
    
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)