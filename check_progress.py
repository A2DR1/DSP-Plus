from pathlib import Path

path = Path('/home/austinsz/Lean_QC/DSP-Plus/result/dsp_minif2f')
target_file = 'finished.txt'

# Find all subdirectories
folders = [f for f in path.iterdir() if f.is_dir()]

print(f"Checking {len(folders)} folders...")

contain_cnt = 0
for folder in folders:
    # Check if 'finished.txt' exists inside this specific folder
    file_path = folder / target_file
    
    if file_path.exists():
        print(f"[✓] {folder.name} contains {target_file}")
        contain_cnt += 1
    else:
        print(f"[ ] {folder.name} does NOT contain {target_file}")

print(f'{contain_cnt} of the {len(folders)} proofs are finished.')