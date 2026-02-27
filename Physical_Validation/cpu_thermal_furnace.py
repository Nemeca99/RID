import time
import csv
import logging
import multiprocessing
import math
import sys

# Append L:\AIOS_V2 to the path so we can import the RID triangle
sys.path.append(r"L:\AIOS_V2")

try:
    from rid_core.triangle import stability_scalar
except ImportError:
    print("Failed to import AIOS V2 RID logic. Ensure it's executed from the right environment.")
    sys.exit(1)

from cpu_sensors import get_cpu_temperature, calculate_cpu_thermal_ltp

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# --- CPU PHYSICAL CONSTANTS FOR i7-11700F ON CORSAIR H100i ---
THERMAL_MAX = 95.0  # Tjunction max cutoff safety buffer
THERMAL_SAFE = 75.0  # Target optimal threshold
PROCESS_UPDATE_INTERVAL = 0.5 # A bit slower to account for AIO fluid thermal inertia

def mathematical_furnace_worker(run_event):
    """
    A purely mathematical, integer/float heavy CPU burn.
    Calculates massive prime numbers or does heavy iterative operations to saturate the core.
    Listens to 'run_event' to know when to pause (Shed Load) and when to burn (Add Fuel).
    """
    while True:
        if run_event.is_set():
            # Heavy CPU math burn
            number = 2
            while run_event.is_set():
                # Just arbitrary intensive math to spin the CPU up
                _ = math.factorial(1000)
                _ = sum(math.sqrt(i) for i in range(10000))
        else:
            time.sleep(0.05)


def cpu_thermal_governor_loop():
    print("=" * 60)
    print(" IGNITING CPU THERMAL FURNACE (AIO Edition) ")
    print(" Hardware: Intel i7-11700F / Corsair H100i Elite Capellix ")
    print(f" Target Safe Base: {THERMAL_SAFE}°C")
    print(f" Target Max Limit: {THERMAL_MAX}°C")
    print("=" * 60)
    
    # Pre-flight check
    t = get_cpu_temperature()
    if t < 0:
        print("\n[CRITICAL WARNING] Could not read CPU telemetry natively.")
        print("Please ensure one of the following:")
        print(" 1. LibreHardwareMonitor or OpenHardwareMonitor is running in the background.")
        print(" 2. OR you have HWiNFO logging to 'L:\\Steel_Brain\\RID\\RID_Completed\\Physical_Validation\\cpu_test.csv'")
        print("Waiting 10 seconds for you to start HWiNFO logging...")
        time.sleep(10)
        t = get_cpu_temperature()
        if t < 0:
            print("Still no telemetry. Continuing anyway, but S_n will remain stuck at 1.0!")
    
    # 8 cores, 16 threads. We will orchestrate 16 worker processes.
    max_workers = 16 
    workers = []
    run_events = []
    
    for _ in range(max_workers):
        ev = multiprocessing.Event()
        # Start them all paused
        ev.clear() 
        p = multiprocessing.Process(target=mathematical_furnace_worker, args=(ev,))
        p.daemon = True
        p.start()
        workers.append(p)
        run_events.append(ev)

    tick = 0
    active_threads = 0
    
    csv_out = "cpu_thermal_trace.csv"
    with open(csv_out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Tick", "Temp_C", "LTP", "S_n", "Active_Threads", "Action"])
        
        try:
            while True:
                # 1. READ PHYSICAL SENSORS
                cpu_temp = get_cpu_temperature()
                
                # 2. AIOS MATHEMATICS
                # For this isolated 1-axis test, RSR and RLE = 1.0
                rsr_n = 1.0
                rle_n = 1.0
                ltp_n = calculate_cpu_thermal_ltp(cpu_temp, target_max=THERMAL_MAX, target_safe=THERMAL_SAFE)
                s_n = stability_scalar(rsr_n, ltp_n, rle_n)
                
                # 3. RID GOVERNOR ACTIONS OVER MULTIPROCESSING
                action = ""
                
                if s_n >= 1.0:
                    action = "ADD_FUEL"
                    # Add threads aggressively if we are safe, to fight liquid thermal inertia
                    active_threads += 2
                elif s_n > 0.0:
                    action = "SHED_LOAD"
                    # Cut active threads proportional to S_n
                    # e.g., if S_n drops to 0.7, we instantly cut threads to 16 * 0.7 = 11.2 -> 11
                    active_threads = int(max_workers * s_n)
                else:
                    action = "CRITICAL_COOLING"
                    active_threads = 0 # Sleep everything
                
                active_threads = max(0, min(max_workers, active_threads))
                
                # Apply the fuel adjustment across the core topology
                for i in range(max_workers):
                    if i < active_threads:
                        run_events[i].set()
                    else:
                        run_events[i].clear()
                
                # 4. LOGGING
                logging.info(f"Tick {tick:04d} | Temp: {cpu_temp:04.1f}°C | LTP: {ltp_n:0.3f} | S_n: {s_n:0.3f} | Threads Pegged: {active_threads:02d} | Action: {action}")
                writer.writerow([tick, cpu_temp, ltp_n, s_n, active_threads, action])
                f.flush()
                
                tick += 1
                time.sleep(PROCESS_UPDATE_INTERVAL)

        except KeyboardInterrupt:
            print("\n=================")
            print("ABORTING TEST. SAVED THERMAL TRACE.")
            print("Killing workers...")
            for p in workers:
                p.terminate()
            print("=================")
                
if __name__ == "__main__":
    cpu_thermal_governor_loop()
