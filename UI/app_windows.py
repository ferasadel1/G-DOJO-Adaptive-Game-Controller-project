import asyncio
import json
import vgamepad as vg
import sys
import argparse
import psycopg2
from pynput import mouse

# =========================
# CLI
# =========================
parser = argparse.ArgumentParser(description="PS4 Emulator Client (Mouse/Trackpad Pointer Version)")
parser.add_argument("--user", default=None, help="Player profile name to load")
parser.add_argument("--db-host", default="localhost", help="PostgreSQL host")
parser.add_argument("--db-port", default=5432, type=int, help="PostgreSQL port")
parser.add_argument("--db-user", default="postgres", help="PostgreSQL user")
parser.add_argument("--db-password", default="$Hulk5628", help="PostgreSQL password")
parser.add_argument("--db-name", default="UI", help="PostgreSQL database name")
args = parser.parse_args()

print("🚀 WINDOWS Emulator starting in MOUSE POINTER mode...")

# =========================
# DATABASE
# =========================
PS_MAPPING_ALIASES = {
    "X": "CROSS", "CROSS": "CROSS", "O": "CIRCLE", "CIRCLE": "CIRCLE",
    "△": "TRIANGLE", "TRIANGLE": "TRIANGLE", "□": "SQUARE", "SQUARE": "SQUARE",
    "L1": "L1", "R1": "R1", "L2": "L2", "R2": "R2", "L3": "L3", "R3": "R3",
    "UP": "UP", "DOWN": "DOWN", "LEFT": "LEFT", "RIGHT": "RIGHT",
    "OPTIONS": "OPTIONS", "SHARE": "SHARE", "PS": "PS", "TOUCHPAD": "TOUCHPAD",
}

def load_profile_regions(profile_name=None):
    try:
        conn = psycopg2.connect(host=args.db_host, port=args.db_port, user=args.db_user, password=args.db_password, dbname=args.db_name)
        cursor = conn.cursor()
        if profile_name: cursor.execute("SELECT profile_name, mapping_data FROM player_profiles WHERE profile_name = %s", (profile_name,))
        else: cursor.execute("SELECT profile_name, mapping_data FROM player_profiles ORDER BY last_updated DESC LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is None:
            print("❌ Profile not found!")
            sys.exit(1)

        regions = row[1]
        if isinstance(regions, str): regions = json.loads(regions)
        print(f"✅ Loaded profile '{row[0]}' ({len(regions)} regions).")
        return regions
    except Exception as e:
        print(f"❌ DB Error: {e}")
        sys.exit(1)

loaded_regions = load_profile_regions(args.user)

def is_point_in_region(x, y, region):
    r_type = region.get("type", "rect")
    r_left, r_top = region.get("left", 0), region.get("top", 0)
    eff_w = region.get("width", 0) * region.get("scaleX", 1)
    eff_h = region.get("height", 0) * region.get("scaleY", 1)

    if r_type == "circle":
        rx, ry = eff_w / 2, eff_h / 2
        if rx == 0 or ry == 0: return False
        return ((x - (r_left + rx)) / rx) ** 2 + ((y - (r_top + ry)) / ry) ** 2 <= 1.0
    return (r_left <= x <= r_left + eff_w) and (r_top <= y <= r_top + eff_h)

# =========================
# GAMEPAD INIT (WINDOWS)
# =========================
try:
    gamepad = vg.VDS4Gamepad()
    gamepad.update()
    print("✅ Virtual PS4 Controller ready!")
except Exception as e:
    print(f"❌ Failed to spawn Virtual Controller: {e}")
    sys.exit(1)

BUTTON_MAP = {
    "CROSS": vg.DS4_BUTTONS.DS4_BUTTON_CROSS, "CIRCLE": vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,
    "TRIANGLE": vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE, "SQUARE": vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,
    "L1": vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT, "R1": vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT,
    "L3": vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT, "R3": vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT,
    "OPTIONS": vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS, "SHARE": vg.DS4_BUTTONS.DS4_BUTTON_SHARE,
}
SPECIAL_BUTTON_MAP = {
    "PS": vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS, "TOUCHPAD": vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD,
}
DPAD_NAMES = {"UP", "DOWN", "LEFT", "RIGHT"}

active_buttons = set()

def sync_gamepad(pressed_btns):
    global active_buttons
    
    # Release old buttons
    for btn in active_buttons - pressed_btns:
        if btn in BUTTON_MAP: gamepad.release_button(button=BUTTON_MAP[btn])
        elif btn in SPECIAL_BUTTON_MAP: gamepad.release_special_button(special_button=SPECIAL_BUTTON_MAP[btn])
        elif btn == "L2": gamepad.left_trigger_float(value_float=0.0)
        elif btn == "R2": gamepad.right_trigger_float(value_float=0.0)
        
    # Press new buttons
    for btn in pressed_btns - active_buttons:
        if btn in BUTTON_MAP: gamepad.press_button(button=BUTTON_MAP[btn])
        elif btn in SPECIAL_BUTTON_MAP: gamepad.press_special_button(special_button=SPECIAL_BUTTON_MAP[btn])
        elif btn == "L2": gamepad.left_trigger_float(value_float=1.0)
        elif btn == "R2": gamepad.right_trigger_float(value_float=1.0)
        
    # D-PAD
    up, down, left, right = "UP" in pressed_btns, "DOWN" in pressed_btns, "LEFT" in pressed_btns, "RIGHT" in pressed_btns
    d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE
    if up and left: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
    elif up and right: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
    elif down and left: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
    elif down and right: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
    elif up: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
    elif down: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
    elif left: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
    elif right: d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
    gamepad.directional_pad(direction=d)
    
    gamepad.update()
    active_buttons = pressed_btns

# =========================
# MOUSE LISTENER
# =========================
def on_click(x, y, button, pressed):
    """
    When you click the touchpad (or mouse), this function checks if the cursor 
    is inside one of your database regions.
    """
    if pressed:
        btns_to_press = set()
        for r in loaded_regions:
            if is_point_in_region(x, y, r):
                if ps_raw := r.get("ps_mapping", ""):
                    mapped_btn = PS_MAPPING_ALIASES.get(str(ps_raw).upper(), str(ps_raw).upper())
                    btns_to_press.add(mapped_btn)
                    print(f"👉 Clicked inside '{r.get('id')}' at ({x}, {y}) -> Pressing {mapped_btn}")
        sync_gamepad(btns_to_press)
    else:
        # On release, release all buttons
        sync_gamepad(set())

if __name__ == "__main__":
    print("\n🖱️  Use your Magic Trackpad to move the mouse cursor and CLICK to trigger regions!")
    print("🛑 Press Ctrl+C in this terminal to stop.")
    try:
        # Start listening to system-wide mouse clicks and suppress them from the OS
        with mouse.Listener(on_click=on_click, suppress=True) as listener:
            listener.join()
    except KeyboardInterrupt:
        gamepad.reset()
        gamepad.update()
        print("\n🛑 Emulator stopped.")