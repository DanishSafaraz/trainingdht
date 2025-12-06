import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import random

# Konfigurasi HiveMQ
MQTT_BROKER = "48be83e63863499c87afce855025c93e.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = "iot/model/ml"

# Setup Streamlit
st.set_page_config(
    page_title="IoT Dashboard - HiveMQ",
    page_icon="🌡️",
    layout="wide"
)

# Judul
st.title("🌡️ IoT Machine Learning Dashboard")
st.markdown("---")

# Inisialisasi session state
if 'data' not in st.session_state:
    st.session_state.data = []
if 'mqtt_connected' not in st.session_state:
    st.session_state.mqtt_connected = False
if 'client' not in st.session_state:
    st.session_state.client = None

# Sidebar untuk kontrol
with st.sidebar:
    st.header("⚙️ Kontrol Panel")
    
    # Input credentials MQTT
    st.subheader("MQTT Settings")
    mqtt_user = st.text_input("Username", value="your_username")
    mqtt_pass = st.text_input("Password", type="password", value="your_password")
    
    # Tombol Connect/Disconnect
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.mqtt_connected:
            if st.button("🔗 Connect", use_container_width=True):
                try:
                    # Setup MQTT client
                    client = mqtt.Client()
                    client.username_pw_set(mqtt_user, mqtt_pass)
                    
                    # Untuk SSL
                    import ssl
                    client.tls_set(cert_reqs=ssl.CERT_NONE)
                    client.tls_insecure_set(True)
                    
                    # Callback functions
                    def on_connect(client, userdata, flags, rc):
                        if rc == 0:
                            st.session_state.mqtt_connected = True
                            client.subscribe(MQTT_TOPIC)
                            st.success("✅ Connected to MQTT!")
                        else:
                            st.error(f"❌ Connection failed: {rc}")
                    
                    def on_message(client, userdata, msg):
                        try:
                            payload = msg.payload.decode()
                            data = json.loads(payload)
                            
                            # Tambah timestamp
                            data['timestamp'] = datetime.now().strftime("%H:%M:%S")
                            
                            # Simpan ke session state
                            st.session_state.data.append(data)
                            
                            # Keep only last 50 data points
                            if len(st.session_state.data) > 50:
                                st.session_state.data = st.session_state.data[-50:]
                                
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error processing message: {e}")
                    
                    # Assign callbacks
                    client.on_connect = on_connect
                    client.on_message = on_message
                    
                    # Connect
                    client.connect(MQTT_BROKER, MQTT_PORT, 60)
                    client.loop_start()
                    
                    # Simpan client ke session state
                    st.session_state.client = client
                    st.session_state.mqtt_connected = True
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Connection error: {e}")
    
    with col2:
        if st.session_state.mqtt_connected:
            if st.button("🔌 Disconnect", use_container_width=True):
                if st.session_state.client:
                    st.session_state.client.loop_stop()
                    st.session_state.client.disconnect()
                st.session_state.mqtt_connected = False
                st.session_state.client = None
                st.rerun()
    
    st.markdown("---")
    
    # Kontrol manual
    st.subheader("Manual Control")
    if st.button("🎲 Generate Test Data"):
        test_data = {
            "temperature": round(random.uniform(20, 35), 2),
            "humidity": round(random.uniform(40, 85), 2),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "prediction": random.choice(["NORMAL", "WARNING", "ALERT"])
        }
        st.session_state.data.append(test_data)
        st.rerun()
    
    if st.button("🧹 Clear Data"):
        st.session_state.data = []
        st.rerun()

# Main Dashboard
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📡 MQTT Status", 
              "✅ CONNECTED" if st.session_state.mqtt_connected else "❌ DISCONNECTED",
              delta="Active" if st.session_state.mqtt_connected else "Inactive")
    
with col2:
    data_count = len(st.session_state.data)
    st.metric("📊 Data Points", data_count)

with col3:
    if st.session_state.data:
        last_temp = st.session_state.data[-1].get('temperature', 0)
        st.metric("🌡️ Last Temp", f"{last_temp:.1f}°C")

st.markdown("---")

# Data Visualization
if st.session_state.data:
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.data)
    
    # Display latest data
    st.subheader("📈 Latest Sensor Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Temperature Chart
        if 'temperature' in df.columns:
            st.line_chart(df.set_index('timestamp')['temperature'])
            st.caption("Temperature Trend")
    
    with col2:
        # Humidity Chart
        if 'humidity' in df.columns:
            st.line_chart(df.set_index('timestamp')['humidity'])
            st.caption("Humidity Trend")
    
    # Data Table
    st.subheader("📋 Historical Data")
    
    # Display table
    display_df = df.copy()
    if 'timestamp' in display_df.columns:
        display_df = display_df[['timestamp', 'temperature', 'humidity', 'prediction']].tail(10)
    
    st.dataframe(display_df, use_container_width=True)
    
    # Download button
    if st.button("📥 Download CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Click to download",
            data=csv,
            file_name=f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

else:
    st.info("📭 No data available. Connect to MQTT or generate test data.")

# Status di footer
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.session_state.mqtt_connected:
        st.success("🟢 MQTT: Connected to HiveMQ Cloud")
    else:
        st.warning("🔴 MQTT: Disconnected")
        
with col2:
    if st.session_state.data:
        last_update = st.session_state.data[-1]['timestamp']
        st.caption(f"Last update: {last_update}")

# Auto refresh jika connected
if st.session_state.mqtt_connected:
    time.sleep(5)
    st.rerun()