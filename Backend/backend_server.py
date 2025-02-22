from flask_cors import CORS
from flask import Flask, request, jsonify
from pymongo import MongoClient
import requests
import json

app = Flask(__name__)
CORS(app)

# Setting up Connection to MongoDb Database for the Plant dataset
MONGO_URL = "mongodb://localhost:27017"
client = MongoClient(MONGO_URL)
db = client["plant_database"]
plants_collection = db["plants"]


#Setting up the API URL to ESP SERVER AND THRESHOLD MOISTURE UPDATE
ESP_SERVER_URL = "http://192.168.0.18.5001/sensor_data"
UPDATE_THRESHOLD_MOISTURE_URL = "http://192.168.0.18:5001/update_moisture"

#Loads JSON data from the json file as file
with open("plants_data2.json","r",encoding="utf-8")as file:
    plants_data = json.load(file)

# Adding dataset to the MongoDb Databse Here: plant_databse
def add_plant_data():
    if plants_collection.count_documents({})==0:
        plants_collection.insert_many(plants_data)
        print("Plant Dataset Added in the Databse")

#Creating Routes
#Home Route
@app.route('/')
def home():
    return "Backend Server is Running!!",200

#Fetch sensor data from ESP server 
@app.rout('/fetch_sensor_data',methods=['GET'])
def fetch_sensor_data():
    try:
        sensor_response = requests.get(ESP_SERVER_URL,timeout=2)
        if sensor_response.status_code ==200:
            return sensor_response.json(),200
        else:
            return jsonify({"error":"Failed to fetch sensor data"}),500
    except Exception as e:
        return jsonify({"error":str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)