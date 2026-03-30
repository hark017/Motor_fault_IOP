# Motor_fault_predictions
## Step 1: Enable UART on RPi

```bash
sudo raspi-config
```
- Go to **Interface Options** → **Serial Port**
- Login shell over serial: **No**
- Serial port hardware enabled: **Yes**
- Reboot: `sudo reboot`

## Step 2: Install Dependencies

```bash
sudo apt update
sudo apt install python3-pip
pip3 install pyserial RPi.GPIO numpy joblib requests
```

## Step 3: Test Script

Save this as `test_sensors.py`:

```python
#!/usr/bin/env python3
import serial
import time
import RPi.GPIO as GPIO

# RST pins
RST_PINS = {
    'I1': 17,  # Pin 11
    'I2': 27,  # Pin 13
    'I3': 22,  # Pin 15
}

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in RST_PINS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

# Open UART
ser = serial.Serial('/dev/serial0', 9600, timeout=1)
time.sleep(0.5)

def read_sensor(name):
    # Disable all sensors
    for n, pin in RST_PINS.items():
        GPIO.output(pin, GPIO.LOW)
    
    time.sleep(0.05)
    
    # Enable only this sensor
    GPIO.output(RST_PINS[name], GPIO.HIGH)
    time.sleep(0.1)
    
    # Clear buffer and read
    ser.reset_input_buffer()
    time.sleep(0.2)
    
    # Try to read
    for _ in range(5):
        line = ser.readline().decode('ascii', errors='ignore').strip()
        if line:
            print(f"  {name} raw: '{line}'")
            try:
                if line[0] in '~+-':
                    value = float(line[1:])
                    if line[0] == '-':
                        value = -value
                    return value
                else:
                    return float(line)
            except:
                pass
    return None

print("="*40)
print("Testing DWCS2200 Sensors")
print("="*40)

try:
    while True:
        print("\nReading sensors...")
        
        I1 = read_sensor('I1')
        I2 = read_sensor('I2')
        I3 = read_sensor('I3')
        
        print(f"\nResults:")
        print(f"  I1 = {I1} A")
        print(f"  I2 = {I2} A")
        print(f"  I3 = {I3} A")
        
        # Re-enable all
        for pin in RST_PINS.values():
            GPIO.output(pin, GPIO.HIGH)
        
        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()
    ser.close()
```

## Step 4: Run Test

```bash
python3 test_sensors.py
```

**Expected Output:**
```
========================================
Testing DWCS2200 Sensors
========================================

Reading sensors...
  I1 raw: '~0.000'
  I2 raw: '~0.000'
  I3 raw: '~0.000'

Results:
  I1 = 0.0 A
  I2 = 0.0 A
  I3 = 0.0 A
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No output | Check VDD/GND connections |
| Garbage data | Check TX wire to Pin 10 |
| Only one sensor works | Check RST pin connections |
| Permission denied | Run with `sudo python3 test_sensors.py` |

## Step 5: Full Inference Code

Once test works, save this as `motor_monitor.py`:

```python
#!/usr/bin/env python3
import serial
import time
import numpy as np
import joblib
import requests
import RPi.GPIO as GPIO

# =============================================================================
# CONFIGURATION
# =============================================================================
RST_PINS = {'I1': 17, 'I2': 27, 'I3': 22}
UART_PORT = '/dev/serial0'
BAUD_RATE = 9600

THINGSPEAK_API_KEY = 'YOUR_API_KEY_HERE'  # <-- UPDATE THIS
THINGSPEAK_URL = 'https://api.thingspeak.com/update'

MODEL_DIR = 'trained_models'
SAMPLE_INTERVAL = 15

# =============================================================================
# SETUP
# =============================================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for pin in RST_PINS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

ser = serial.Serial(UART_PORT, BAUD_RATE, timeout=1)
time.sleep(0.5)

# =============================================================================
# FUNCTIONS
# =============================================================================
def read_sensor(name):
    for pin in RST_PINS.values():
        GPIO.output(pin, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST_PINS[name], GPIO.HIGH)
    time.sleep(0.1)
    ser.reset_input_buffer()
    time.sleep(0.2)
    
    for _ in range(5):
        line = ser.readline().decode('ascii', errors='ignore').strip()
        if line:
            try:
                if line[0] in '~+-':
                    value = float(line[1:])
                    return -value if line[0] == '-' else value
                return float(line)
            except:
                pass
    return None

def read_all():
    I1 = read_sensor('I1')
    I2 = read_sensor('I2')
    I3 = read_sensor('I3')
    for pin in RST_PINS.values():
        GPIO.output(pin, GPIO.HIGH)
    return I1, I2, I3

def compute_features(I1, I2, I3):
    I_sum = I1 + I2 + I3
    I_max = max(abs(I1), abs(I2), abs(I3))
    I_min = min(abs(I1), abs(I2), abs(I3))
    I_range = I_max - I_min
    I_std = np.std([I1, I2, I3])
    return np.array([[I1, I2, I3, I_sum, I_max, I_min, I_range, I_std]], dtype=np.float32)

def upload(I1, I2, I3, preds):
    params = {
        'api_key': THINGSPEAK_API_KEY,
        'field1': f"{I1:.3f}",
        'field2': f"{I2:.3f}",
        'field3': f"{I3:.3f}",
        'field4': preds['binary'],
        'field5': preds['severity'],
        'field6': preds['phase'],
        'field7': preds['load']
    }
    try:
        r = requests.get(THINGSPEAK_URL, params=params, timeout=10)
        if r.status_code == 200 and r.text != '0':
            print(f"  ThingSpeak: OK (entry {r.text})")
        else:
            print(f"  ThingSpeak: Failed")
    except Exception as e:
        print(f"  ThingSpeak Error: {e}")

# =============================================================================
# LOAD MODELS
# =============================================================================
print("Loading models...")
scaler = joblib.load(f'{MODEL_DIR}/scaler.joblib')
models = {
    'binary': joblib.load(f'{MODEL_DIR}/model_binary.joblib'),
    'severity': joblib.load(f'{MODEL_DIR}/model_severity.joblib'),
    'phase': joblib.load(f'{MODEL_DIR}/model_phase.joblib'),
    'load': joblib.load(f'{MODEL_DIR}/model_load.joblib')
}

LABELS = {
    'binary': {0: 'Healthy', 1: 'Faulty'},
    'severity': {0: 'Healthy', 1: '1μ', 2: '3μ', 3: '5μ'},
    'phase': {0: 'Healthy', 1: 'Phase 1', 2: 'Phase 2', 3: 'Phase 3'},
    'load': {0: 'No Load', 1: 'Half Load', 2: 'Full Load'}
}

print("Models loaded!")

# =============================================================================
# MAIN LOOP
# =============================================================================
print("="*50)
print("Motor Fault Detection System - Running")
print("="*50)

try:
    while True:
        I1, I2, I3 = read_all()
        
        if None in (I1, I2, I3):
            print(f"Sensor error: I1={I1}, I2={I2}, I3={I3}")
            time.sleep(SAMPLE_INTERVAL)
            continue
        
        # Predict
        X = compute_features(I1, I2, I3)
        X_scaled = scaler.transform(X)
        
        preds = {}
        for task, model in models.items():
            preds[task] = int(model.predict(X_scaled)[0])
        
        # Display
        print(f"\nCurrents: I1={I1:.3f}A  I2={I2:.3f}A  I3={I3:.3f}A")
        print(f"  Binary:   {LABELS['binary'][preds['binary']]}")
        print(f"  Severity: {LABELS['severity'][preds['severity']]}")
        print(f"  Phase:    {LABELS['phase'][preds['phase']]}")
        print(f"  Load:     {LABELS['load'][preds['load']]}")
        
        # Upload
        upload(I1, I2, I3, preds)
        
        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    ser.close()
    GPIO.cleanup()
    print("Done")
```

## Step 6: Run

```bash
# First update your ThingSpeak API key in the code
# Then run:
python3 motor_monitor.py
```

Does the test script work? Let me know the output.
