import sys
sys.path.insert(0, r"d:\agent\gui\os-harm-all")
try:
    import run_crossplatform_tests
    print("Import OK")
except SyntaxError as e:
    print(f"SyntaxError: {e}")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
