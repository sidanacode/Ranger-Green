from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ThresholdUpdate(BaseModel):
    threshold: float

latest_sensor_data = {}
moisture_threshold = 50.0  # Default Threshold
pump_status = "OFF"  # Default pump status

@app.get('/')
def home():
    return "ESP FastAPI Server is Running"

@app.get('/moisture_threshold')
def get_moisture_threshold():
    return {"moisture_threshold": moisture_threshold}

# API to Receive Sensor Data From Esp
@app.post("/sensor_data")
def receive_sensor_data(data: Dict[str, Any]):
    global latest_sensor_data, pump_status
    try:
        if not data:
            print("Error: Received empty JSON data")
            raise HTTPException(status_code=400, detail="Empty JSON data")

        print("Received Sensor Data:", data)  # Debugging

        # Store the received sensor data
        latest_sensor_data = data

        # Extract soil moisture and update pump status
        soil_moisture = float(latest_sensor_data.get("soil_moisture", 0))

        # update pump status based on moisture level
        if soil_moisture is not None:
            pump_status = "ON" if soil_moisture < moisture_threshold else "OFF"
        print("Received Sensor Data:", latest_sensor_data)
        return {"message": "Sensor data received", "pump_status": pump_status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API TO GET LATEST SENSOR DATA
@app.get('/sensor_data')
def get_sensor_data():
    return latest_sensor_data or {
        "soil_moisture": None, "temperature": None,
        "humidity": None, "light_intensity": None,
        "pump_status": "UNKNOWN"
    }

@app.get('/update_moisture')
def get_update_moisture():
    global moisture_threshold
    return {"threshold": moisture_threshold}

@app.post('/update_moisture')
def post_update_moisture(update: ThresholdUpdate):
    global moisture_threshold
    moisture_threshold = update.threshold
    return {"message": "Threshold updated", "threshold": moisture_threshold}

if __name__ == '__main__':
    uvicorn.run("esp_server:app", host='0.0.0.0', port=5001, reload=True)
