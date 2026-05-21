# G-DOJO-Adaptive-Game-Controller-project
G-DOJO is an adaptive game controller designed specifically to eliminate hardware barriers for gamers with motor disabilities, allowing them to comfortably engage in fast-paced video games. 

The system operates through four main components: a touchpad that captures the user’s swiping and tapping actions, custom physical buttons that serve as dedicated input mechanisms, a Raspberry Pi that acts as a central hub receiving all raw touchpad and button data, and a charging station that securely holds and powers the buttons.

The hardware architecture centers on 3D-printed Physical Buttons and the Charging Station. 

Each custom button is equipped with an ATTINY84A as the microcontroller, an NRF2401 module for wireless communication, and a Hall effect sensor that detects physical presses via an internal magnet and compression spring. 

The main charging station safely docks all eight buttons using magnetic pogo-pin connectors and features a comprehensive power management system including a USB-C Power Delivery (PD) trigger, a charge controller, and a high-efficiency step-down converter to reliably power the setup and manage the internal lithium-ion batteries.

The software methodology integrates embedded firmware, networking, and a full-stack interface to translate user inputs into actionable gameplay. The physical buttons wirelessly transmit data to the Raspberry Pi using a randomized transmit strategy across radio pipes to prevent signal collisions, while the Pi simultaneously captures multi-touch data from the touchpad via Bluetooth and streams everything to a client laptop over WebSockets. 
<img width="15073" height="175" alt="image" src="https://github.com/user-attachments/assets/ceb3f495-2967-420d-b151-5438ca053eaf" />

