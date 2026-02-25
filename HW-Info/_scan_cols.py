import csv

with open(r'l:\Steel_Brain\RID\RID_Completed\HW-Info\2_25_2026_test_1.CSV', encoding='latin-1') as f:
    reader = csv.reader(f)
    headers = next(reader)
    row2 = next(reader)

# CPU thermal and power columns
cpu_kw = ['core temp','core 0 temp','core 1 temp','core 2 temp','core 3 temp','core 4 temp',
          'core 5 temp','core 6 temp','core 7 temp','package temp','package power',
          'core power','ia core','cpu temp','coolant','tjmax','tdie','core distance']
cpu_cols = [(i, h) for i, h in enumerate(headers) if any(kw in h.lower() for kw in cpu_kw)]

print(f'Total columns: {len(headers)}')
print('CPU Thermal/Power columns:')
for i, h in cpu_cols:
    val = row2[i] if i < len(row2) else 'N/A'
    print(f'[{i:3d}] {h!r:60s} = {val}')
