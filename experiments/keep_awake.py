"""Keep Windows from sleeping while long experiments run (no power settings are changed; effect ends with the process)."""
import ctypes
import sys
import time

ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
end = time.time() + hours * 3600
while time.time() < end:
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    time.sleep(60)
ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
