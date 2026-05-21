import asyncio
import websockets
import json
import evdev
from evdev import ecodes
import sys

PORT = 8767
connected_clients = set()

def find_trackpad():
    """Automatically finds the Apple Magic Trackpad event path."""
    print("Searching for connected trackpads...")
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    
    for device in devices:
        # Looks for keywords in the Bluetooth/USB device name
        if "Trackpad" in device.name or "Apple" in device.name or "Mac" in device.name:
            print(f"✅ Found Trackpad: {device.name} at {device.path}")
            return device
            
    print("❌ Error: No Apple Trackpad found! Make sure it is paired via Bluetooth or plugged in via USB.")
    return None

async def broadcast_touches(dev):
    """Reads raw evdev multi-touch data and broadcasts it to HTML clients."""
    touches = {}
    current_slot = 0
    
    print("📡 Listening for finger movements...")
    
    try:
        # async_read_loop prevents blocking the websocket server
        async for event in dev.async_read_loop():
            if event.type == ecodes.EV_ABS:
                # Slot determines WHICH finger we are currently updating
                if event.code == ecodes.ABS_MT_SLOT:
                    current_slot = event.value
                    
                # Tracking ID tells us if a finger was placed or lifted
                elif event.code == ecodes.ABS_MT_TRACKING_ID:
                    if event.value == -1:  # -1 means finger lifted
                        if current_slot in touches:
                            del touches[current_slot]
                    else:  # Finger placed
                        if current_slot not in touches:
                            touches[current_slot] = {'id': event.value, 'x': 0, 'y': 0, 'pressure': 0}
                        touches[current_slot]['id'] = event.value
                        
                # Update X coordinate
                elif event.code == ecodes.ABS_MT_POSITION_X:
                    if current_slot in touches:
                        touches[current_slot]['x'] = event.value
                        
                # Update Y coordinate
                elif event.code == ecodes.ABS_MT_POSITION_Y:
                    if current_slot in touches:
                        touches[current_slot]['y'] = event.value

                # Update Pressure
                elif event.code == ecodes.ABS_MT_PRESSURE:
                    if current_slot in touches:
                        touches[current_slot]['pressure'] = event.value
                        
            # SYN_REPORT means the trackpad finished sending the current frame
            elif event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                if connected_clients:
                    # Convert active touches dictionary to a list and send
                    payload = json.dumps(list(touches.values()))
                    websockets.broadcast(connected_clients, payload)
                    
    except OSError:
        print("\n⚠️ Trackpad disconnected! Please reconnect it and restart the script.")
        sys.exit(1)

async def websocket_handler(websocket):
    """Handles new HTML clients connecting to the Pi."""
    connected_clients.add(websocket)
    try:
        print(f"💻 New screen connected! Total viewing: {len(connected_clients)}")
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"💻 Screen disconnected. Total viewing: {len(connected_clients)}")

async def main():
    # 1. Auto-detect Trackpad
    dev = find_trackpad()
    if not dev:
        sys.exit(1)

    # 2. Start WebSocket Server
    print(f"🚀 Starting WebSocket server on ws://0.0.0.0:{PORT}")
    print("Waiting for your HTML UI to connect...")
    
    # 0.0.0.0 allows connections from your Windows laptop
    async with websockets.serve(websocket_handler, "0.0.0.0", PORT):
        # 3. Start reading fingers
        await broadcast_touches(dev)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped manually.")


