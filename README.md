# Image Logger – Distributed Webcam Monitoring System

Open-source system for collecting images and environmental data from multiple Raspberry Pi cameras and storing them on a centralized server.

The goal of this project is to create a **low-cost, easily replicable webcam monitoring system** capable of capturing images and environmental data such as temperature, humidity and atmospheric pressure.

Each camera node periodically captures a photo and sends it together with sensor measurements to a central server where the data are stored and displayed through a web interface.

This project was developed as part of a school project and is released as **open source** so anyone can build their own monitoring network.

---

# Features

- 📷 Periodic image capture
- 🌡 Environmental measurements (temperature, humidity, pressure)
- 🖥 Centralized server for data collection
- 💾 SQLite database storage
- 🌐 Simple web interface for viewing images
- 📡 Multiple camera support
- 🧩 Modular and easy to replicate
- 🔓 Open-source

---

# System Architecture

The system consists of two main components.

## Camera Node

Hardware installed in a weatherproof box that captures images and reads sensor data.

Typical configuration:

- Raspberry Pi 4B
- PoE+ HAT (Power over Ethernet)
- Digital camera (e.g. Canon PowerShot)
- BME280 environmental sensor
- Weatherproof enclosure

The camera node performs:

1. Capturing an image
2. Reading sensor data
3. Sending data to the server via HTTP

---

## Central Server

The server receives uploaded images and stores them together with metadata.

Responsibilities:

- image storage
- measurement logging
- web interface
- device identification
- database management

Technologies used:

- Python
- Flask
- SQLite

---

# Project Structure

```
image-logger/
│
├── server.py          # Flask server
├── image_logger.py    # Client script for Raspberry Pi
├── images/            # Stored images
├── database.db        # SQLite database
└── README.md
```

---

# Installation

## 1. Clone the repository

```
git clone https://github.com/yourusername/image-logger.git
cd image-logger
```

## 2. Install dependencies

```
pip install -r requirements.txt
```

If requirements.txt is missing you can install manually:

```
pip install flask werkzeug
```

---

# Running the Server

Start the server using:

```
python server.py
```

The server will start on:

```
http://localhost:5000
```

Uploaded images will be stored in the `images/` directory and metadata will be saved in the SQLite database.

---

# API

## Upload image

Endpoint:

```
POST /upload
```

### Example request

```
curl -X POST http://server-address/upload \
 -F image=@image.jpg \
 -F temperature=21.5 \
 -F humidity=60 \
 -F pressure=1012 \
 -F device_id=rpi01
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| image | captured image |
| temperature | measured temperature |
| humidity | measured humidity |
| pressure | atmospheric pressure |
| device_id | unique device identifier |

---

# Example Workflow

1. Raspberry Pi captures an image
2. Sensors measure environmental values
3. Data are sent to the server via HTTP request
4. Server stores image and metadata
5. Images become visible in the web interface

---

# Hardware Setup

Example camera node hardware:

| Component | Description |
|--------|-------------|
| Raspberry Pi 4B | main controller |
| PoE HAT | power via Ethernet |
| Canon PowerShot | external camera |
| BME280 | temperature, humidity and pressure sensor |
| Waterproof box | outdoor enclosure |

---

# Replication

The project is designed to be easily replicable.

To add a new camera:

1. deploy the client script on another Raspberry Pi
2. configure `device_id`
3. set the server address
4. start periodic capture

Multiple cameras can send data to the same server.

---

# Possible Improvements

Future improvements may include:

- authentication for devices
- time-lapse generation
- environmental graphs
- cloud deployment
- API key security
- automatic image tagging

---

# License

This project is released under the **MIT License**.

You are free to use, modify and distribute this software.

---

# Author

Name: Your Name  
Field of study: Your Study Program

---

# Project Goal

The main goal of this project is to provide a **low-cost open-source solution for building distributed webcam monitoring systems** that anyone can reproduce and expand.

---

# Acknowledgements

This project uses:

- Python
- Flask
- Raspberry Pi
- BME280 sensor
