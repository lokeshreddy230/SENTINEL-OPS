import sys
import httpx

API_URL = "http://localhost:8000"

def inject_scenario(scenario_id: str):
    url = f"{API_URL}/api/demo/scenario/{scenario_id}"
    print(f"Injecting failure scenario {scenario_id} via API: {url}...")
    try:
        response = httpx.post(url, timeout=10.0)
        if response.status_code == 200:
            print("Success: Scenario injected.")
            print(response.json())
        else:
            print(f"Error: Server responded with status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Failed to connect to backend server at {API_URL}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python failure_injector.py <scenario_id>")
        print("Scenarios:")
        print("  1 - Database Connection Pool Exhaustion")
        print("  2 - Memory Leak")
        print("  3 - Cascading Failure")
        sys.exit(1)
        
    inject_scenario(sys.argv[1])
