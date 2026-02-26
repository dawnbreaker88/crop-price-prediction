# AI Builder Instructions — Crop Price Prediction App
### No code. Architecture and pipeline instructions only.

---

## Project Overview

Build a crop price prediction web application with a **FastAPI backend** and **Streamlit frontend**. The backend exposes a prediction API. The frontend collects user inputs and displays the predicted price. Both communicate over HTTP.

There is **one pre-built artifact** already available:
- `pipeline.pkl` — contains both the fitted OrdinalEncoder and the trained LightGBM model packed together as a single object

Do not retrain or refit anything. Load this artifact as-is.

---

## Architecture Overview

```
STREAMLIT FRONTEND
        │
        │  HTTP POST — JSON payload of 8 raw features
        ▼
FASTAPI BACKEND
        │
        ├── Step 1: log1p transform on arrivals_tonnes
        ├── Step 2: OrdinalEncoder transform on crop, season, market, state
        ├── Step 3: assemble final feature array in exact column order
        ├── Step 4: model.predict()
        │
        └── Return predicted price as JSON
        │
        ▼
STREAMLIT FRONTEND
        │
        └── Display predicted price to user
```

---

## Backend — FastAPI

### Startup Behavior
- Load `pipeline.pkl` exactly once when the application starts
- Never reload it on each request — load at startup only
- Store it as global application state
- The pipeline object internally handles both encoding and prediction — call it as a single unit

### Endpoints

**POST /predict**
- Accepts a JSON body containing exactly 8 fields — listed below
- Runs the full preprocessing pipeline internally
- Returns a JSON response containing the predicted modal price in INR per quintal

**GET /health**
- Returns a simple JSON confirming the service is running
- No processing required

### Input Schema — Pydantic Model
Define a strict Pydantic input model with the following fields and types:

| Field | Type | Valid Values |
|---|---|---|
| crop | string | Rice, Wheat, Maize, Onion, Potato |
| season | string | Kharif, Rabi, Zaid/Summer |
| market | string | Any of the 20 APMC market names |
| state | string | Corresponding state name |
| avg_temp_c | float | 14.0 to 43.0 |
| rainfall_mm | float | 0.0 to 380.0 |
| arrivals_tonnes | float | 45.0 to 28000.0 |
| inflation_rate_percent | float | 3.2 to 9.1 |

Reject any request where crop, season, or market contain values not seen during training. Return a clear 422 validation error.

### Preprocessing Pipeline — Single Function
Build one single preprocessing function inside the backend. It must execute in this exact order:

1. Apply `numpy.log1p` to `arrivals_tonnes`
2. Assemble the feature array in this exact column order:
   `crop, season, market, state, avg_temp_c, rainfall_mm, arrivals_tonnes, inflation_rate_percent`
3. Pass the assembled array to `pipeline.predict()` — encoding and prediction happen internally
4. Return the single predicted float value

This function is the entire pipeline. There is no separate encoding step, no scaling, no normalization.

### Response Format
Return JSON with one key: `predicted_price_inr` containing the predicted value rounded to 2 decimal places.

---

## Frontend — Streamlit

### Input Form
All inputs must be collected before making any API call. Use the following input widget types:

| Field | Widget Type | Reason |
|---|---|---|
| crop | Selectbox / Dropdown | Prevents invalid string input |
| season | Selectbox / Dropdown | Prevents invalid string input |
| market | Selectbox / Dropdown | Prevents invalid string input |
| state | Auto-filled based on market selection | State is determined by market — user should not enter it manually |
| avg_temp_c | Slider or Number Input | Range 14 to 43 |
| rainfall_mm | Slider or Number Input | Range 0 to 380 |
| arrivals_tonnes | Number Input | Range 45 to 28000 |
| inflation_rate_percent | Number Input | Range 3.2 to 9.1 |

> **Important:** State must be auto-populated when market is selected. The market-to-state mapping is fixed and must be hardcoded in the frontend. User must never type state manually.

### Prediction Trigger
- Single button labeled **Predict Price**
- On click: assemble all 8 fields into a JSON payload and send HTTP POST to `/predict`
- Show a loading spinner while waiting for the response

### Output Display
- Display the predicted price prominently — large font, clearly labeled as INR per quintal
- Display a price range as: predicted price ± RMSE value (hardcode the RMSE from your training run)
- If the API returns an error, display a clear human-readable error message — do not crash

### No Free Text Inputs
All categorical fields must use dropdowns. This prevents the backend from receiving unknown category values that would break the encoder.

---

## Market to State Mapping (hardcode in frontend)

| Market | State |
|---|---|
| Azadpur (Delhi) | Delhi |
| Pusa (Samastipur) | Bihar |
| Nashik | Maharashtra |
| Indore | Madhya Pradesh |
| Sangli | Maharashtra |
| Sirsa | Haryana |
| Pune | Maharashtra |
| Ahmednagar | Maharashtra |
| Bhawanigarh | Punjab |
| Delhi | Delhi |
| Hyderabad | Telangana |
| Bangalore | Karnataka |
| Chennai | Tamil Nadu |
| Kolkata | West Bengal |
| Mumbai | Maharashtra |
| Jaipur | Rajasthan |
| Lucknow | Uttar Pradesh |
| Patna | Bihar |
| Bhopal | Madhya Pradesh |
| Nagpur | Maharashtra |

---

## File Structure Expected

```
crop-price-prediction/
│
├── artifacts/
│   ├── model.pkl
│   └── encoder.pkl
│
├── backend/
│   └── main.py          ← FastAPI app
│
├── frontend/
│   └── app.py           ← Streamlit app
│
└── requirements.txt
```

---

## Requirements File Must Include

```
fastapi
uvicorn
streamlit
requests
scikit-learn
lightgbm
```

---

## How to Run

Backend must start before frontend.

- Backend: run uvicorn on `main.py`, default port 8000
- Frontend: run streamlit on `app.py`, default port 8501
- Frontend calls backend at `http://localhost:8000/predict`

---

## What NOT to Do

- Do not retrain or refit the model or encoder anywhere in the code
- Do not apply StandardScaler or any normalization — tree model does not need it
- Do not allow free text input for crop, season, market, or state
- Do not apply log1p to any column other than arrivals_tonnes
- Do not load pipeline.pkl inside the predict function — load at startup only
- Do not hardcode any prediction or encoding logic — everything goes through the loaded pipeline
