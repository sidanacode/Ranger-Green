document.addEventListener('DOMContentLoaded', () => {
    const plantSelect = document.getElementById('plantSelect');
    const stateSelect = document.getElementById('stateSelect');
    const submitBtn = document.getElementById('submitBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const recommendedSection = document.getElementById('recommendedSection');
    const suggestionSection = document.getElementById('suggestionSection');

    // Elements for displaying data
    const recommendedMoisture = document.getElementById('recommendedMoisture');
    const recommendedHumidity = document.getElementById('recommendedHumidity');
    const recommendedLight = document.getElementById('recommendedLight');
    const recommendedTemperature = document.getElementById('recommendedTemperature');
    const currentMoisture = document.getElementById('currentMoisture');
    const currentTemp = document.getElementById('currentTemp');
    const currentHumidity = document.getElementById('currentHumidity');
    const currentLight = document.getElementById('currentLight');
    const currentpumpstatus = document.getElementById('currentpumpstatus');
    const careSuggestion = document.getElementById('careSuggestion');

    let selectedPlant = ""; // Store selected plant name
    let selectedState = ""; // Store selected state name
    
    function getBackendUrl() {
        return 'http://localhost:5000'; // Your backend server address
    }

    // ✅ Fetch only sensor data
    async function fetchSensorData() {
        try {
            const response = await fetch(`${getBackendUrl()}/fetch_sensor_data`);
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();

            currentMoisture.textContent = (data.soil_moisture !== undefined && data.soil_moisture !== null) ? `${data.soil_moisture}%` : "0%";
            currentTemp.textContent = (data.temperature !== undefined && data.temperature !== null) ? `${data.temperature}°C` : "0°C";
            currentHumidity.textContent = (data.humidity !== undefined && data.humidity !== null) ? `${data.humidity}%` : "0%";
            currentLight.textContent = (data.light_intensity !== undefined && data.light_intensity !== null) ? `${data.light_intensity} lux` : "0 lux";
            currentpumpstatus.textContent = (data.pump_status !== undefined && data.pump_status !== null) ? `${data.pump_status}` : "OFF";
        

            if (selectedPlant) {
                fetchPlantData();
            }
        } catch (error) {
            console.error('Error fetching sensor data:', error);
        }
    }

    // ✅ Fetch plant data & care suggestions
    async function fetchPlantData() {
        if (!selectedPlant || !selectedState) return;

        try {
            const response = await fetch(`${getBackendUrl()}/compare_plant`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: selectedPlant, state: selectedState })
            });

            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();

            recommendedSection.classList.remove('hidden');
            suggestionSection.classList.remove('hidden');

            recommendedMoisture.textContent = data.plant?.ideal_moisture ? `${data.plant.ideal_moisture}%` : "No Data";
            recommendedHumidity.textContent = data.plant?.ideal_humidity ? `${data.plant.ideal_humidity}%` : "No Data";
            recommendedLight.textContent = data.plant?.ideal_light ? `${data.plant.ideal_light} lux` : "No Data";
            recommendedTemperature.textContent = data.plant?.ideal_temperature ? `${data.plant.ideal_temperature}°C` : "No Data";

            // ✅ Now care suggestions update correctly
            careSuggestion.textContent = data.suggestions?.length ? data.suggestions.join(", ") : "No suggestion available";

            console.log("Updated Plant Data & Care Suggestions:", data);
        } catch (error) {
            console.error('Error fetching plant data:', error);
        }
    }

    // Check if ESP IP is configured
    const espIp = localStorage.getItem('espServerIP');
    if (!espIp) {
        window.location.href = 'index.html';
    }

    // ✅ Start real-time sensor data updates
    fetchSensorData();
    setInterval(fetchSensorData, 2000);

    // ✅ Handle user input
    submitBtn.addEventListener('click', () => {
        selectedPlant = plantSelect.value;
        selectedState = stateSelect.value;
        
        if (!selectedPlant || !selectedState) {
            alert('Please select a plant and a state');
            return;
        }

        loadingIndicator.classList.remove('hidden');
        fetchPlantData().then(() => {
            loadingIndicator.classList.add('hidden');
        });
    });

    // ✅ Initialize Dropdowns
    async function initDropdowns() {
        try {
            const response = await fetch(`${getBackendUrl()}/get_plants`);
            if (!response.ok) throw new Error('Failed to fetch plants');
            const plants = await response.json();
            
            plants.forEach(plant => {
                const option = document.createElement('option');
                option.value = plant;
                option.textContent = plant;
                plantSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching plants:', error);
        }
    }
    
    plantSelect.addEventListener('change', async () => {
        const plant = plantSelect.value;
        stateSelect.innerHTML = '<option value="">Select State</option>'; // Reset
        stateSelect.disabled = true;
        
        if (!plant) return;
        
        try {
            const response = await fetch(`${getBackendUrl()}/get_states?plant_name=${encodeURIComponent(plant)}`);
            if (!response.ok) throw new Error('Failed to fetch states');
            const states = await response.json();
            
            states.forEach(state => {
                const option = document.createElement('option');
                option.value = state;
                option.textContent = state;
                stateSelect.appendChild(option);
            });
            stateSelect.disabled = false;
        } catch (error) {
            console.error('Error fetching states:', error);
        }
    });

    initDropdowns();
});
