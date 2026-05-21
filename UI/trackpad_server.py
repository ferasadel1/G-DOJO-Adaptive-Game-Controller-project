import hid
import time

APPLE_VID = 0x004C
MAGIC_TRACKPAD_PIDS = [0x0265, 0x0267, 0x0264, 0x0315]

def main():
    print("Searching for Magic Trackpad...")
    device_paths = [d['path'] for d in hid.enumerate() if d['vendor_id'] == APPLE_VID and d['product_id'] in MAGIC_TRACKPAD_PIDS]

    if not device_paths:
        print("❌ Trackpad not found! Check Bluetooth connection.")
        return

    open_devices = []
    
    # 1. Open all interfaces
    for path in device_paths:
        try:
            dev = hid.device()
            dev.open_path(path)
            dev.set_nonblocking(True)
            open_devices.append(dev)
        except OSError:
            continue

    if not open_devices:
        print("❌ Windows blocked all access. Run terminal as Administrator.")
        return

    print("✅ Devices opened. Attempting to send Apple Raw-Mode commands...")

    # 2. Send the Magic Wake-Up Commands
    for dev in open_devices:
        try:
            # Apple Command 1: Trackpad 2/3 Raw Mode
            dev.send_feature_report(bytearray([0x02, 0x01]))
        except Exception:
            pass
            
        try:
            # Apple Command 2: Legacy Trackpad Raw Mode
            dev.send_feature_report(bytearray([0xD7, 0x01]))
        except Exception:
            pass

    print("\n👆 TOUCH THE TRACKPAD NOW! (Move your fingers around)")
    print("Waiting for raw multi-touch data...\n")
    
    try:
        while True:
            for dev in open_devices:
                report = dev.read(64)
                if report:
                    # We got data! Print it out.
                    hex_str = " ".join([f"{b:02X}" for b in report[:15]])
                    print(f"Data! -> {hex_str}")
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\nExiting...")
        for dev in open_devices:
            dev.close()

if __name__ == "__main__":
    main()
