import time
import csv
import logging
import multiprocessing
import math
import sys
import psutil
import random
import copy

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
THERMAL_MAX = 95.0
THERMAL_SAFE = 75.0
PROCESS_UPDATE_INTERVAL = 0.5

# --- SYSTEM RAM CONSTANTS FOR RLE ---
RAM_MAX_PERCENT = 95.0
RAM_SAFE_PERCENT = 80.0

# --- STRUCTURAL DRIFT CONSTANTS FOR RSR ---
RSR_MAX_TOLERANCE = 1000.0  # Max permitted distance before identity loss


def calculate_ram_rle(safe_pct: float, max_pct: float) -> float:
    """
    RLE is 1.0 when memory is safe.
    It decays towards 0.0 as RAM approaches the maximum capacity (OS freeze limit).
    """
    mem = psutil.virtual_memory()
    current_pct = mem.percent
    
    if current_pct <= safe_pct:
        return 1.0
    if current_pct >= max_pct:
        return 0.0
        
    return (max_pct - current_pct) / (max_pct - safe_pct)


def calculate_rsr_drift(working_matrix: list, baseline_matrix: list) -> float:
    """
    Calculates RSR by measuring the L2 Discrepancy between the working soul memory and the baseline.
    As bit-flips accumulate, the distance grows, and RSR decays towards 0.0.
    """
    dist = 0.0
    for w, b in zip(working_matrix, baseline_matrix):
        dist += (w - b) ** 2
    
    dist = math.sqrt(dist)
    
    if dist >= RSR_MAX_TOLERANCE:
        return 0.0
    
    return 1.0 - (dist / RSR_MAX_TOLERANCE)


def mathematical_furnace_worker(run_event):
    """
    Intensive math worker governed strictly by S_n.
    When run_event is clear, the worker sleeps.
    """
    while True:
        if run_event.is_set():
            number = 2
            while run_event.is_set():
                _ = math.factorial(1000)
                _ = sum(math.sqrt(i) for i in range(10000))
        else:
            time.sleep(0.05)


def tri_axis_furnace_loop():
    print("=" * 70)
    print(" FATAL TRI-AXIS PHYSICS ENGINE (Full Triangle Validation) ")
    print(" Hardware: Core i7-11700F / 32GB RAM ")
    print(" Axis 1 (LTP): CPU Thermal Capacity (AIO Liquid)")
    print(" Axis 2 (RLE): System Memory Depletion (Garbage Allocation)")
    print(" Axis 3 (RSR): Structural Identity Drift (Forced Bit Flips)")
    print("=" * 70)
    
    t = get_cpu_temperature()
    if t < 0:
        print("\n[CRITICAL WARNING] Start HWiNFO logging to `cpu_test.csv`!")
        time.sleep(10)
    
    max_workers = 16 
    workers = []
    run_events = []
    
    for _ in range(max_workers):
        ev = multiprocessing.Event()
        ev.clear() 
        p = multiprocessing.Process(target=mathematical_furnace_worker, args=(ev,))
        p.daemon = True
        p.start()
        workers.append(p)
        run_events.append(ev)

    tick = 0
    active_threads = 0
    
    # RLE Garbage Allocation (RAM Soaking)
    garbage_memory = []
    allocation_chunk_size = 1000 * 1024 * 1024  # 1GB chunks
    
    # RSR Structural Baseline (Soul Anchor)
    baseline_matrix = [1.0] * 500
    working_matrix = copy.deepcopy(baseline_matrix)
    
    csv_out = "tri_axis_trace.csv"
    with open(csv_out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Tick", "Temp_C", "LTP", "RAM_Pct", "RLE", "RSR_Dist", "RSR", "S_n", "Active_Threads", "Action"])
        
        try:
            while True:
                # ==========================================
                # 1. READ PHYSICAL SENSORS / CALCULATE AXES
                # ==========================================
                
                # --- Axis 1: LTP (Thermals) ---
                cpu_temp = get_cpu_temperature()
                ltp_n = calculate_cpu_thermal_ltp(cpu_temp, target_max=THERMAL_MAX, target_safe=THERMAL_SAFE)
                
                # --- Axis 2: RLE (RAM Entropy) ---
                rle_n = calculate_ram_rle(RAM_SAFE_PERCENT, RAM_MAX_PERCENT)
                ram_pct = psutil.virtual_memory().percent
                
                # --- Axis 3: RSR (Identity Drift) ---
                rsr_n = calculate_rsr_drift(working_matrix, baseline_matrix)
                # Calculate absolute drift for logging
                rsr_dist = math.sqrt(sum((w - b)**2 for w, b in zip(working_matrix, baseline_matrix)))
                
                # ==========================================
                # 2. THE GRAND TRIANGLE EQUATION
                # ==========================================
                s_n = stability_scalar(rsr_n, ltp_n, rle_n)
                
                # ==========================================
                # 3. APPLY STRESS (FORCE THE PHYSICAL WORLD)
                # ==========================================
                
                # --- Unstoppable Environmental Entropy ---
                # 1. External RAM Leak (Simulating external memory pressure)
                if ram_pct < RAM_MAX_PERCENT:
                    garbage_memory.append(bytearray(allocation_chunk_size))
                
                # 2. Continuous Hardware Faults / Radiation
                for _ in range(100):
                    idx = random.randint(0, len(working_matrix) - 1)
                    working_matrix[idx] += random.uniform(-10.0, 10.0)

                # --- OS Governor Logic (Reacting to S_n) ---
                action = ""
                if s_n >= 1.0:
                    action = "ADD_STRESS"
                    # The OS feels perfectly safe natively, so it ramps up CPU workload
                    active_threads = min(max_workers, active_threads + 2)
                        
                elif s_n > 0.0:
                    action = f"GOVERN_S_N"
                    
                    # 1. Throttle CPU proportionally purely by mathematical S_n
                    active_threads = int(max_workers * s_n)
                    
                    # 2. Free Memory proportional to RLE collapse
                    # The OS desperately tries to free memory to fight the external leak
                    target_chunks = int(len(garbage_memory) * s_n)
                    while len(garbage_memory) > target_chunks:
                        garbage_memory.pop()
                        
                    # 3. No Structural Healing!
                    # RSR will monotonically decay due to constant environmental noise
                    # until S_n collapses to 0.0.
                else:
                    action = "CRITICAL_COLLAPSE"
                    active_threads = 0
                    garbage_memory.clear() # Dump all RAM stress
                    working_matrix = copy.deepcopy(baseline_matrix) # Hard reset identity
                
                active_threads = max(0, min(max_workers, active_threads))
                
                # Dispatch CPU workload instructions
                for i in range(max_workers):
                    if i < active_threads:
                        run_events[i].set()
                    else:
                        run_events[i].clear()
                
                # ==========================================
                # 4. LOGGING
                # ==========================================
                # Format a precise clean log output
                log_str = (f"Tk {tick:04d} | "
                           f"LTP:{ltp_n:0.3f} (T:{cpu_temp:04.1f}C) | "
                           f"RLE:{rle_n:0.3f} (R:{ram_pct:04.1f}%) | "
                           f"RSR:{rsr_n:0.3f} (D:{rsr_dist:06.1f}) | "
                           f"S_n: {s_n:0.3f} | Th:{active_threads:02d} | Act: {action}")
                           
                logging.info(log_str)
                writer.writerow([tick, cpu_temp, ltp_n, ram_pct, rle_n, rsr_dist, rsr_n, s_n, active_threads, action])
                f.flush()
                
                tick += 1
                time.sleep(PROCESS_UPDATE_INTERVAL)

        except KeyboardInterrupt:
            print("\n=================")
            print("ABORTING TEST. SAVED THERMAL TRACE.")
            print("Cleaning up memory and dropping workers...")
            garbage_memory.clear()
            for p in workers:
                p.terminate()
            print("=================")
                
if __name__ == "__main__":
    tri_axis_furnace_loop()
