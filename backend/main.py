import os
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Literal

app = FastAPI(title="Crop Price Prediction API")

# --- SKLEARN COMPATIBILITY PATCH ---
# This patch is required because the model was trained with scikit-learn 1.6.1,
# but the current environment uses 1.8.0, where '_RemainderColsList' was moved/removed.
try:
    import sklearn.compose._column_transformer
    import sys
    if not hasattr(sklearn.compose._column_transformer, '_RemainderColsList'):
        class _RemainderColsList(list):
            def __setstate__(self, state):
                self.extend(state)
        sklearn.compose._column_transformer._RemainderColsList = _RemainderColsList
except Exception as e:
    print(f"Warning: Failed to apply compatibility patch: {e}")
# ------------------------------------

# Path to the artifact
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "artifacts", "model_pipeline.pkl")

# Global state for the model
model_pipeline = None

@app.on_event("startup")
def load_model():
    global model_pipeline
    import traceback
    try:
        print(f"Attempting to load model from: {MODEL_PATH}")
        model_pipeline = joblib.load(MODEL_PATH)
        print("Model loaded successfully!")
    except Exception as e:
        print("CRITICAL: Failed to load model!")
        traceback.print_exc()
        # Instead of crashing, we'll keep the server running so we can see the error logs
        # but mark the model as None
        model_pipeline = None

class PredictionInput(BaseModel):
    crop: Literal["Rice", "Wheat", "Maize", "Onion", "Potato"]
    season: Literal["Kharif", "Rabi", "Zaid/Summer"]
    market: str
    state: str
    avg_temp_c: float = Field(..., ge=14.0, le=43.0)
    rainfall_mm: float = Field(..., ge=0.0, le=380.0)
    arrivals_tonnes: float = Field(..., ge=45.0, le=28000.0)
    inflation_rate_percent: float = Field(..., ge=3.2, le=9.1)

    @validator("market")
    def validate_market(cls, v):
        valid_markets = [
            "Azadpur (Delhi)", "Pusa (Samastipur)", "Nashik", "Indore", "Sangli", 
            "Sirsa", "Pune", "Ahmednagar", "Bhawanigarh", "Delhi", "Hyderabad", 
            "Bangalore", "Kolkata", "Jaipur", "Lucknow", "Patna", "Bhopal", "Nagpur",
            "Mumbai", "Chennai" # Added based on the instructions list
        ]
        if v not in valid_markets:
            raise ValueError(f"Market '{v}' not recognized.")
        return v

@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": model_pipeline is not None}

@app.post("/predict")
def predict(data: PredictionInput):
    if model_pipeline is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    # Step 1: Assemble features in exact order
    # Preprocessing (log1p and encoding) happens internally in the pipeline
    features = pd.DataFrame([{
        "crop": data.crop,
        "season": data.season,
        "market": data.market,
        "state": data.state,
        "avg_temp_c": data.avg_temp_c,
        "rainfall_mm": data.rainfall_mm,
        "arrivals_tonnes": data.arrivals_tonnes,
        "inflation_rate_percent": data.inflation_rate_percent
    }])

    try:
        # Step 4: model.predict()
        prediction = model_pipeline.predict(features)
        
        # Return predicted price rounded to 2 decimal places
        predicted_price = float(prediction[0])
        return {"predicted_price_inr": round(predicted_price, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
