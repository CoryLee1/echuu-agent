# Script to convert vtuber_multiagent.py to Jupyter notebook
import json
import re

with open('vtuber_multiagent.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("File length:", len(content))
print("Last 100 chars:", repr(content[-100:]))
print("First 100 chars:", repr(content[:100]))

# Check if it's a truncated notebook JSON
if content.strip().startswith('{') and '"cells"' in content:
    print("\nThis appears to be notebook JSON format")
    
    # Check if it ends properly
    if not content.strip().endswith('}'):
        print("File appears to be truncated!")
        
        # Find where it's cut off
        lines = content.split('\n')
        print(f"Total lines: {len(lines)}")
        print("Last 5 lines:")
        for line in lines[-5:]:
            print(f"  {repr(line)}")

