from core.dispatcher import Dispatcher
import sys
import time
import threading

if __name__ == "__main__":
    dispatcher = Dispatcher()
    stop_event = threading.Event()

    try:
        dispatcher._listen_to_user_messages()
        print("Listening... Press Ctrl+C to stop.")
        stop_event.wait()  # Aspetta finché non viene interrotto
    except KeyboardInterrupt:
        print("Interrupted. Shutting down cleanly...")
        dispatcher.stop_listening()
        sys.exit(0)
