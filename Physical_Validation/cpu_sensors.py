import subprocess
import csv
import os
import time

def get_cpu_temperature_hwinfo(csv_path: str) -> float:
    """Reads the last line of an active HWiNFO CSV log to get the CPU Package Temperature."""
    if not os.path.exists(csv_path):
        return -1.0
        
    try:
        # Read the last line efficiently
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            # We must parse headers first to find "CPU Package [C]"
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                return -1.0
                
            cpu_pkg_idx = -1
            for i, h in enumerate(headers):
                if 'CPU Package' in h and '[C]' in h:
                    cpu_pkg_idx = i
                    break
            
            if cpu_pkg_idx == -1:
                return -1.0

            # Get last line
            # Go to the end of the file and read backwards
            f.seek(0, os.SEEK_END)
            filesize = f.tell()
            block_size = 8192  # HWiNFO rows can be very wide, need a large block
            
            # Read last chunk
            if filesize > block_size:
                f.seek(filesize - block_size)
            else:
                f.seek(0)
                
            data = f.read()
            lines = [line for line in data.splitlines() if line.strip()]
            if lines:
                last_line = lines[-1]
            else:
                return -1.0
                
            row = last_line.split(',')
            if len(row) > cpu_pkg_idx:
                val = row[cpu_pkg_idx].strip()
                if val:
                    try:
                        return float(val)
                    except ValueError:
                        return -1.0
                    
    except Exception as e:
        print(f"Error reading CSV: {e}")
        
    return -1.0


def get_cpu_temp_powershell() -> float:
    """Attempts to read CPU temp via LibreHardwareMonitor/OpenHardwareMonitor WMI via PowerShell."""
    try:
        # Try LibreHardwareMonitor
        ps_script = "(Get-WmiObject -Namespace root\\LibreHardwareMonitor -Class Sensor -ErrorAction SilentlyContinue | Where-Object { $_.SensorType -eq 'Temperature' -and $_.Name -match 'CPU Package' }).Value"
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_script], text=True, stderr=subprocess.DEVNULL).strip()
        if out:
            return float(out)
            
        # Try OpenHardwareMonitor
        ps_script = "(Get-WmiObject -Namespace root\\OpenHardwareMonitor -Class Sensor -ErrorAction SilentlyContinue | Where-Object { $_.SensorType -eq 'Temperature' -and $_.Name -match 'CPU Package' }).Value"
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_script], text=True, stderr=subprocess.DEVNULL).strip()
        if out:
            return float(out)
            
    except Exception:
        pass
        
    return -1.0


def get_cpu_temperature() -> float:
    """Gets the dominant CPU temperature (Package/Tjunction)."""
    # 1. First try PowerShell (LHM/OHM WMI)
    temp = get_cpu_temp_powershell()
    if temp > 0:
        return temp
        
    # 2. If it fails, rely on the user having HWiNFO logging to `cpu_test.csv`
    csv_fallback = r"L:\Steel_Brain\RID\RID_Completed\Physical_Validation\cpu_test.csv"
    temp = get_cpu_temperature_hwinfo(csv_fallback)
    if temp > 0:
        return temp
        
    return -1.0

def calculate_cpu_thermal_ltp(current_temp: float, target_max: float = 95.0, target_safe: float = 75.0) -> float:
    """
    Calculates LTP for the CPU. 
    LTP is bound [0.0, 1.0].
    """
    if current_temp < 0:
        # Failsafe if we can't read thermal
        return 1.0
    if current_temp >= target_max:
        return 0.0
    if current_temp <= target_safe:
        return 1.0
        
    return (target_max - current_temp) / (target_max - target_safe)
