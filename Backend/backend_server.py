from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ESPIPRequest(BaseModel):
    esp_ip: str

class ComparePlantRequest(BaseModel):
    name: str
    state: str

# Global variable to store ESP IP
ESP_IP = None

# Load the state-wise plant dataset into memory
dataset_path = os.path.join(os.path.dirname(__file__), "..", "state_wise_plant_data.json")
try:
    with open(dataset_path, "r", encoding="utf-8") as file:
        state_wise_plant_data = json.load(file)
    print("State-wise Plant Dataset loaded successfully!")
except Exception as e:
    print(f"Error loading state_wise_plant_data.json: {e}")
    state_wise_plant_data = {}

@app.get('/get_plants')
def get_plants():
    plants = list(state_wise_plant_data.keys())
    return plants

@app.get('/get_states')
def get_states(plant_name: str = None):
    if not plant_name:
        raise HTTPException(status_code=400, detail="Valid plant name is required")
        
    # Find plant name case-insensitively
    plant_key = None
    for key in state_wise_plant_data.keys():
        if key.lower() == plant_name.lower():
            plant_key = key
            break
            
    if not plant_key:
        raise HTTPException(status_code=404, detail="Plant not found")
        
    states = list(state_wise_plant_data[plant_key].keys())
    return states

# New route to set ESP IP
@app.post('/set-esp-ip')
def set_esp_ip(data: ESPIPRequest):
    global ESP_IP
    ESP_IP = data.esp_ip
    if ESP_IP:
        return {"message": "ESP IP set successfully"}
    raise HTTPException(status_code=400, detail="Invalid ESP IP")

@app.get('/')
def home():
    return "Backend Server is Running!!"

@app.get('/fetch_sensor_data')
def fetch_sensor_data():
    global ESP_IP
    if not ESP_IP:
        raise HTTPException(status_code=400, detail="ESP IP not configured")
    
    try:
        sensor_response = requests.get(f"http://{ESP_IP}/sensor_data", timeout=1)
        if sensor_response.status_code == 200:
            sensor_data = sensor_response.json()
            # Add battery percentage to response if not present
            if 'battery_percentage' not in sensor_data:
                sensor_data['battery_percentage'] = 0  # Default value if ESP doesn't send it
            return sensor_data
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch sensor data")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/compare_plant')
def compare_plant(req: ComparePlantRequest):
    global ESP_IP
    if not ESP_IP:
        raise HTTPException(status_code=400, detail="ESP IP not configured")
      
    try:
        requested_plant_name = req.name.lower()
        requested_state_name = req.state.lower()
        
        if not requested_plant_name or not requested_state_name:
            raise HTTPException(status_code=400, detail="Plant name and state are required")
            
        # Find exact case for plant
        plant_name_key = None
        for key in state_wise_plant_data.keys():
            if key.lower() == requested_plant_name:
                plant_name_key = key
                break
                
        if not plant_name_key:
            raise HTTPException(status_code=404, detail="Plant not found")
            
        # Find exact case for state
        state_key = None
        for key in state_wise_plant_data[plant_name_key].keys():
            if key.lower() == requested_state_name:
                state_key = key
                break
                
        if not state_key:
            raise HTTPException(status_code=404, detail=f"State not found for plant {plant_name_key}")
            
        plant_params = state_wise_plant_data[plant_name_key][state_key]
        
        plant = {
            "name": plant_name_key,
            "state": state_key,
            "ideal_temperature": plant_params.get("ideal_temperature_c"),
            "ideal_humidity": plant_params.get("ideal_humidity_percent"),
            "ideal_light": plant_params.get("ideal_light_lux"),
            "ideal_moisture": plant_params.get("ideal_moisture_percent"),
            "climatic_zone": plant_params.get("climatic_zone")
        }

        try:
            sensor_response = requests.get(f"http://{ESP_IP}/sensor_data", timeout=1)
            if sensor_response.status_code == 200:
                sensor_data = sensor_response.json()
            else:
                raise Exception("Failed to fetch real sensor data")
        except Exception as e:
            print(f"Sensor Fetch error: {e}")
            
        #getting Attribuites values
        # Convert sensor data to proper numeric types
        try:
            soil_moisture = float(sensor_data.get("soil_moisture", 0))
            temperature = float(sensor_data.get("temperature", 0))
            humidity = float(sensor_data.get("humidity", 0))  # If humidity should be int, convert later
            light_intensity = float(sensor_data.get("light_intensity", 0))
        except ValueError as e:
            print(f"Error converting sensor data: {e}")
            raise HTTPException(status_code=400, detail="Invalid sensor data format")

# If humidity and light intensity should be integers
        humidity = int(humidity)
        light_intensity = int(light_intensity)
        # if the attribuites values are None then
        if soil_moisture is None:
            soil_moisture=0.0
        if temperature is None:
            temperature = 0.0
        if humidity is None:
            humidity = 0.0
        if light_intensity is None:
            light_intensity = 0.0
        
        #generation of Care Suggestions
        suggestions = []
        pump_status = "OFF"
        if soil_moisture < plant["ideal_moisture"]:
            suggestions.append("Increase watering 🌱💧")
            pump_status = "ON"
        elif soil_moisture > plant["ideal_moisture"]:
            suggestions.append("Reduce watering 🚫💧")
            pump_status = "OFF"

        if temperature < plant["ideal_temperature"]:
            suggestions.append("Increase temperature 🔥")
        elif temperature > plant["ideal_temperature"]:
            suggestions.append("Decrease temperature ❄️")

        if humidity < plant["ideal_humidity"]:
            suggestions.append("Increase humidity 🌫️")
        elif humidity > plant["ideal_humidity"]:
            suggestions.append("Decrease humidity 💨")

        if light_intensity < plant["ideal_light"]:
            suggestions.append("Move plant to more light ☀️")
        elif light_intensity > plant["ideal_light"]:
            suggestions.append("Move plant to shade 🌳")
        
        # Update threshold moisture
        try:
            update_response = requests.post(
                f"http://{ESP_IP}/update_moisture",
                json={"threshold": plant["ideal_moisture"]},
                timeout=2
            )
        except Exception as e:
            print(f"Error sending Threshold value: {e}")

        return {
            "plant": plant,
            "sensor_data": sensor_data,
            "suggestions": suggestions,
            "pump_status": pump_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this new route to clear the ESP IP
@app.post('/clear-esp-ip')
def clear_esp_ip():
    global ESP_IP
    ESP_IP = None
    return {"message": "ESP IP cleared successfully"}

if __name__ == '__main__':
    uvicorn.run("backend_server:app", host="0.0.0.0", port=5000, reload=True)