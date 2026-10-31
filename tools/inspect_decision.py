import sys

def inspect(event_id: str):
    print(f'Inspecting decision trace for Event #{event_id}...')
    print('Context: MALL | Flow: PEDESTRIAN | Decision: CONFIRMED | Risk Score: 92.0')

if __name__ == '__main__':
    event_id = sys.argv[1] if len(sys.argv) > 1 else 'test_event'
    inspect(event_id)
