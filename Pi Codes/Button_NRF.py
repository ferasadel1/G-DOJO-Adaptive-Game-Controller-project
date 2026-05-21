import asyncio
import websockets
import json
import struct
import time
from pyrf24 import RF24, RF24_PA_MIN, RF24_2MBPS

PORT = 8766
TIMEOUT_SECONDS = 0.20

radio = RF24(22, 0)

addresses = [
    b"\x78\x78\x78\x78\x78",
    b"\xE8\xE8\xF0\xF0\xE1",
    b"\xE8\xE8\xF0\xF0\xE2",
    b"\xE8\xE8\xF0\xF0\xE3",
    b"\xE8\xE8\xF0\xF0\xE4",
    b"\xE8\xE8\xF0\xF0\xE5"
]

connected_clients = set()
button_states = {}
last_seen_time = {}


def setup_radio():
    if not radio.begin():
        raise RuntimeError("NRF24L01 not responding!")

    radio.setPALevel(RF24_PA_MIN)
    radio.setDataRate(RF24_2MBPS)
    radio.channel = 0x4C
    radio.payload_size = 3
    radio.setAutoAck(False)

    for i in range(6):
        radio.openReadingPipe(i, addresses[i])

    radio.startListening()
    print("✅ NRF Receiver started.")
    print(f"🌐 WebSocket port: {PORT}")


async def broadcast_button_states():
    if not connected_clients:
        return

    message = json.dumps({"buttons": button_states})
    dead_clients = []

    for client in list(connected_clients):
        try:
            await client.send(message)
        except Exception:
            dead_clients.append(client)

    for client in dead_clients:
        connected_clients.discard(client)


async def nrf_reader_loop():
    while True:
        current_time = time.time()
        state_changed = False

        has_payload, pipe_num = radio.available_pipe()

        if has_payload:
            payload = radio.read(3)

            if len(payload) == 3:
                try:
                    tx_id, sensor_state = struct.unpack("<Bh", payload)
                    tx_key = f"TX{tx_id}"

                    is_pressed = 1 if sensor_state == 0 else 0
                    last_seen_time[tx_key] = current_time

                    if button_states.get(tx_key, 0) != is_pressed:
                        button_states[tx_key] = is_pressed
                        print(f"📥 Pipe {pipe_num} | {tx_key} -> {is_pressed}")
                        state_changed = True

                except struct.error as e:
                    print(f"⚠️ Struct unpack error: {e}")

        for tx_key, state in list(button_states.items()):
            if state == 1:
                if (current_time - last_seen_time.get(tx_key, 0)) > TIMEOUT_SECONDS:
                    button_states[tx_key] = 0
                    print(f"⏱️ Timeout release: {tx_key} -> 0")
                    state_changed = True

        if state_changed:
            await broadcast_button_states()

        await asyncio.sleep(0.001)


async def ws_handler(websocket):
    print("💻 Windows emulator connected.")
    connected_clients.add(websocket)

    try:
        await websocket.send(json.dumps({"buttons": button_states}))
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        print("❌ Windows emulator disconnected.")


async def main():
    setup_radio()

    async with websockets.serve(ws_handler, "0.0.0.0", PORT):
        print(f"✅ NRF WebSocket server running at ws://0.0.0.0:{PORT}")
        await nrf_reader_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        radio.powerDown()
        print("\n🛑 Receiver stopped.")
