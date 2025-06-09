import json
import os
import time
from datetime import datetime, timedelta
import threading
from pathlib import Path

class DataHandler:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # File paths
        self.sensor_file = self.data_dir / "sensor_data.json"
        self.matrix_file = self.data_dir / "matrix_data.json"
        self.history_dir = self.data_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Initialize files if they don't exist
        self._init_files()
        
        # Start cleanup task
        self._start_cleanup_task()
    
    def _init_files(self):
        """Initialize data files with default structure"""
        default_sensor = {
            "sensor_value": 0,
            "threshold": 500,
            "state": 0,
            "timestamp": time.time(),
            "last_update": "Never"
        }
        
        default_matrix = {
            "matrix": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
            "timestamp": time.time(),
            "last_update": "Never"
        }
        
        if not self.sensor_file.exists():
            self._write_json_file(self.sensor_file, default_sensor)
        
        if not self.matrix_file.exists():
            self._write_json_file(self.matrix_file, default_matrix)
    
    def _write_json_file(self, filepath, data):
        """Thread-safe JSON file writing"""
        with self.lock:
            try:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception as e:
                print(f"[DataHandler] ❌ Error writing {filepath}: {e}")
                return False
    
    def _read_json_file(self, filepath):
        """Thread-safe JSON file reading"""
        with self.lock:
            try:
                if filepath.exists():
                    with open(filepath, 'r') as f:
                        return json.load(f)
                return None
            except Exception as e:
                print(f"[DataHandler] ❌ Error reading {filepath}: {e}")
                return None
    
    def save_sensor_data(self, sensor_value, threshold=500):
        """Save sensor data from ESP32"""
        state = 1 if sensor_value > threshold else 0
        
        data = {
            "sensor_value": sensor_value,
            "threshold": threshold,
            "state": state,
            "timestamp": time.time(),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save current data
        success = self._write_json_file(self.sensor_file, data)
        
        # Save to history
        if success:
            self._save_to_history("sensor", data)
            print(f"[DataHandler] ✅ Sensor data saved: {sensor_value} (state: {state})")
        
        return success
    
    def save_matrix_data(self, matrix):
        """Save matrix data from ESP32"""
        data = {
            "matrix": matrix,
            "timestamp": time.time(),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        success = self._write_json_file(self.matrix_file, data)
        
        if success:
            self._save_to_history("matrix", data)
            print(f"[DataHandler] ✅ Matrix data saved")
        
        return success
    
    def _save_to_history(self, data_type, data):
        """Save historical data with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H")
            history_file = self.history_dir / f"{data_type}_{timestamp}.json"
            
            # Read existing history or create new
            history_data = []
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
            
            # Add new entry
            history_data.append(data)
            
            # Keep only last 100 entries per hour
            if len(history_data) > 100:
                history_data = history_data[-100:]
            
            # Save history
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            print(f"[DataHandler] ❌ Error saving history: {e}")
    
    def get_sensor_data(self):
        """Get current sensor data"""
        return self._read_json_file(self.sensor_file)
    
    def get_matrix_data(self):
        """Get current matrix data"""
        return self._read_json_file(self.matrix_file)
    
    def get_sensor_history(self, hours=24):
        """Get sensor history for specified hours"""
        history = []
        now = datetime.now()
        
        for i in range(hours):
            timestamp = (now - timedelta(hours=i)).strftime("%Y%m%d_%H")
            history_file = self.history_dir / f"sensor_{timestamp}.json"
            
            if history_file.exists():
                data = self._read_json_file(history_file)
                if data:
                    history.extend(data)
        
        return sorted(history, key=lambda x: x.get('timestamp', 0), reverse=True)
    
    def _start_cleanup_task(self):
        """Start background task to clean old files"""
        def cleanup_old_files():
            while True:
                try:
                    # Clean files older than 7 days
                    cutoff = datetime.now() - timedelta(days=7)
                    
                    for file in self.history_dir.glob("*.json"):
                        if file.stat().st_mtime < cutoff.timestamp():
                            file.unlink()
                            print(f"[DataHandler] 🗑️ Cleaned old file: {file.name}")
                
                except Exception as e:
                    print(f"[DataHandler] ❌ Cleanup error: {e}")
                
                # Sleep for 1 hour
                time.sleep(3600)
        
        cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
        cleanup_thread.start()
