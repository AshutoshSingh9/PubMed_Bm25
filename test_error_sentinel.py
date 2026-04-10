import time
from agents.error_sentinel import sentinel

def flakey_function():
    # Intentionally failing function to demonstrate the sentinel
    print("Executing flakey_function...")
    raise ConnectionError("Network unreachable")

def main():
    print("Starting Error Sentinel...")
    sentinel.start()

    print("Attempting to run flakey_function with retry logic via sentinel...")
    try:
        sentinel.execute_with_retry("DemoComponent", flakey_function)
    except Exception as e:
        print(f"Final failure surfaced to main thread: {e}")

    # Give the background monitor thread a second to process logs
    time.sleep(2)
    
    print("Stopping Error Sentinel...")
    sentinel.stop()
    print("Sentinel history:", sentinel.error_history)

if __name__ == "__main__":
    main()
