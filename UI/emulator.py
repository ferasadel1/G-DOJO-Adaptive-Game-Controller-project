import asyncio
import websockets
import json
import vgamepad as vg
import sys
import argparse

# =========================
# CLI
# =========================
parser = argparse.ArgumentParser(description="PS4 Emulator Client")
parser.add_argument("--ip", default="192.168.1.157", help="Raspberry Pi IP address")
parser.add_argument("--debug", action="store_true", help="Print raw data received from Pi servers")
args = parser.parse_args()

PI_IP = args.ip
DEBUG = args.debug

TOUCHPAD_WEBSOCKET_URI = f"ws://{PI_IP}:8767"
NRF_WEBSOCKET_URI = f"ws://{PI_IP}:8766"

def dprint(*msg):
    if DEBUG:
        print(*msg)

print("🚀 Emulator starting...")
print(f"🌐 Touchpad URI: {TOUCHPAD_WEBSOCKET_URI}")
print(f"🌐 NRF URI: {NRF_WEBSOCKET_URI}")
print(f"🐞 Debug mode: {'ON' if DEBUG else 'OFF'}")

# =========================
# GAMEPAD INIT
# =========================
try:
    gamepad = vg.VDS4Gamepad()
    gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
    gamepad.update()
    gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
    gamepad.update()
    print("✅ Virtual PS4 Controller ready!")
except Exception as e:
    print(f"❌ Failed to spawn Virtual PS4 Controller: {e}")
    sys.exit(1)

# =========================
# GLOBAL STATE
# =========================
active_joystick_state = {"x": 0.0, "y": 0.0}
previous_finger_pos = {}

nrf_buttons = set()
active_effective_buttons = set()
DPAD_NAMES = {"UP", "DOWN", "LEFT", "RIGHT"}

TX_TO_PS_BUTTON = {
    "TX1": "CROSS",
    "TX2": "CIRCLE",
    "TX3": "SQUARE",
    "TX4": "TRIANGLE",
    "TX5": "L1",
    "TX6": "R1",
    "TX7": "L2",
    "TX8": "R2",
    "TX9": "UP",
    "TX10": "DOWN",
    "TX11": "LEFT",
    "TX12": "RIGHT",
    "TX13": "OPTIONS",
    "TX14": "SHARE",
    "TX15": "PS",
    "TX16": "TOUCHPAD",
    "TX17": "L3",
    "TX18": "R3",
}

BUTTON_MAP = {
    "CROSS": vg.DS4_BUTTONS.DS4_BUTTON_CROSS,
    "CIRCLE": vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,
    "TRIANGLE": vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE,
    "SQUARE": vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,
    "L1": vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT,
    "R1": vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT,
    "L3": vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT,
    "R3": vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT,
    "OPTIONS": vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS,
    "SHARE": vg.DS4_BUTTONS.DS4_BUTTON_SHARE,
}

SPECIAL_BUTTON_MAP = {
    "PS": vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS,
    "TOUCHPAD": vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD,
}


def normalize_buttons(buttons):
    return {str(b).strip().upper() for b in buttons if str(b).strip()}


# =========================
# TOUCHPAD MOVEMENT
# =========================
def process_movement(fingers):
    global active_joystick_state, previous_finger_pos

    dprint(f"👆 Raw touchpad fingers: {fingers}")

    valid_fingers = [f for f in fingers if isinstance(f, dict)]

    if not valid_fingers:
        gamepad.left_joystick_float(x_value_float=0.0, y_value_float=0.0)
        gamepad.update()
        active_joystick_state = {"x": 0.0, "y": 0.0}
        previous_finger_pos.clear()
        dprint("👆 No valid fingers -> joystick centered")
        return

    primary = next((f for f in valid_fingers if f.get("id") == 0), valid_fingers[0])

    f_id = primary.get("id", 0)
    curr_x = primary.get("x")
    curr_y = primary.get("y")

    dprint(f"👆 Primary finger: id={f_id}, x={curr_x}, y={curr_y}")

    if curr_x is None or curr_y is None:
        return

    if f_id in previous_finger_pos:
        dx = curr_x - previous_finger_pos[f_id]["x"]
        dy = curr_y - previous_finger_pos[f_id]["y"]

        SENSITIVITY = 0.005

        new_joy_x = active_joystick_state["x"] + (dx * SENSITIVITY)
        new_joy_y = active_joystick_state["y"] + (dy * SENSITIVITY)

        new_joy_x = max(min(new_joy_x, 1.0), -1.0)
        new_joy_y = max(min(new_joy_y, 1.0), -1.0)

        active_joystick_state["x"] = new_joy_x
        active_joystick_state["y"] = new_joy_y

        gamepad.left_joystick_float(x_value_float=new_joy_x, y_value_float=new_joy_y)
        gamepad.update()

        print(f"🕹️ Stick: x={new_joy_x:.3f}, y={new_joy_y:.3f}")
        dprint(f"👆 dx={dx}, dy={dy}, sensitivity={SENSITIVITY}")

    previous_finger_pos[f_id] = {"x": curr_x, "y": curr_y}


# =========================
# BUTTONS
# =========================
def set_non_dpad_control(control, pressed):
    dprint(f"🎮 set_non_dpad_control(control={control}, pressed={pressed})")

    if control in BUTTON_MAP:
        if pressed:
            gamepad.press_button(button=BUTTON_MAP[control])
        else:
            gamepad.release_button(button=BUTTON_MAP[control])

    elif control in SPECIAL_BUTTON_MAP:
        if pressed:
            gamepad.press_special_button(special_button=SPECIAL_BUTTON_MAP[control])
        else:
            gamepad.release_special_button(special_button=SPECIAL_BUTTON_MAP[control])

    elif control == "L2":
        gamepad.left_trigger_float(value_float=1.0 if pressed else 0.0)

    elif control == "R2":
        gamepad.right_trigger_float(value_float=1.0 if pressed else 0.0)


def update_dpad(effective_buttons):
    up = "UP" in effective_buttons and "DOWN" not in effective_buttons
    down = "DOWN" in effective_buttons and "UP" not in effective_buttons
    left = "LEFT" in effective_buttons and "RIGHT" not in effective_buttons
    right = "RIGHT" in effective_buttons and "LEFT" not in effective_buttons

    if up and left:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
    elif up and right:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
    elif down and left:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
    elif down and right:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
    elif up:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
    elif down:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
    elif left:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
    elif right:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
    else:
        d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE

    dprint(f"🧭 D-pad direction: {d}")
    gamepad.directional_pad(direction=d)


def sync_gamepad_state():
    global active_effective_buttons

    effective_buttons = normalize_buttons(nrf_buttons)
    dprint(f"📦 effective_buttons = {effective_buttons}")

    prev_non_dpad = {b for b in active_effective_buttons if b not in DPAD_NAMES}
    curr_non_dpad = {b for b in effective_buttons if b not in DPAD_NAMES}

    for btn in curr_non_dpad - prev_non_dpad:
        print(f"🔘 PRESSED: {btn}")
        set_non_dpad_control(btn, True)

    for btn in prev_non_dpad - curr_non_dpad:
        print(f"⭕ RELEASED: {btn}")
        set_non_dpad_control(btn, False)

    update_dpad(effective_buttons)
    gamepad.update()
    active_effective_buttons = effective_buttons


def update_nrf_buttons_from_packet(packet):
    global nrf_buttons

    dprint(f"📨 Raw NRF packet: {packet}")

    if not isinstance(packet, dict):
        return

    buttons = packet.get("buttons")
    if not isinstance(buttons, dict):
        dprint("⚠️ Packet has no valid 'buttons' dict")
        return

    pressed = set()

    for tx_id, state in buttons.items():
        try:
            tx_key = str(tx_id).strip().upper()
            state_int = int(state)
            mapped = TX_TO_PS_BUTTON.get(tx_key)

            dprint(f"📡 tx={tx_key}, state={state_int}, mapped={mapped}")

            if state_int == 1 and mapped:
                pressed.add(mapped)
        except Exception as e:
            dprint(f"⚠️ Error parsing button entry {tx_id}:{state} -> {e}")

    nrf_buttons = normalize_buttons(pressed)
    sync_gamepad_state()


# =========================
# SOCKET CLIENTS
# =========================
async def connect_to_touchpad():
    print(f"🔄 Touchpad connecting to {TOUCHPAD_WEBSOCKET_URI}...")
    while True:
        try:
            async with websockets.connect(
                TOUCHPAD_WEBSOCKET_URI,
                ping_interval=5,
                ping_timeout=5
            ) as websocket:
                print("✅ Touchpad stream connected!")

                async for message in websocket:
                    dprint(f"📥 Raw touchpad websocket message: {message}")
                    try:
                        payload = json.loads(message)
                        fingers = payload.get("data", []) if isinstance(payload, dict) else payload
                        process_movement(fingers)
                    except json.JSONDecodeError:
                        dprint("⚠️ Invalid JSON from touchpad server")

        except Exception as e:
            print(f"⚠️ Touchpad stream lost ({e}). Retrying in 3 seconds...")
            await asyncio.sleep(3)


async def connect_to_nrf():
    print(f"📡 NRF connecting to {NRF_WEBSOCKET_URI}...")
    while True:
        try:
            async with websockets.connect(
                NRF_WEBSOCKET_URI,
                ping_interval=5,
                ping_timeout=5
            ) as websocket:
                print("✅ NRF stream connected!")

                async for message in websocket:
                    dprint(f"📥 Raw NRF websocket message: {message}")
                    try:
                        packet = json.loads(message)
                        update_nrf_buttons_from_packet(packet)
                    except json.JSONDecodeError:
                        dprint("⚠️ Invalid JSON from NRF receiver")

        except Exception as e:
            print(f"⚠️ NRF stream lost ({e}). Retrying in 3 seconds...")
            await asyncio.sleep(3)


async def main():
    await asyncio.gather(
        connect_to_touchpad(),
        connect_to_nrf(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        gamepad.reset()
        gamepad.update()
        print("\n🛑 Emulator stopped.");