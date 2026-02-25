import csv, sys

with open(r'l:\Steel_Brain\RID\RID_Completed\HW-Info\2_25_2026_test_1.CSV', encoding='latin-1') as f:
    reader = csv.reader(f)
    headers = next(reader)
    row2 = next(reader)

gpu_kw = ['gpu','vram','temperature','power','fan','shader','video','fb','hot spot','junction',
          'memory used','memory load','board','core clk','gr clk']

gpu_cols = [(i, h) for i, h in enumerate(headers) if any(kw in h.lower() for kw in gpu_kw)]
print(f'Total columns: {len(headers)}')
for i, h in gpu_cols:
    val = row2[i] if i < len(row2) else 'N/A'
    print(f'[{i:3d}] {h!r:55s} = {val}')
