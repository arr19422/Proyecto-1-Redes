import time
from getpass import getpass
import asyncio
from xmpp import MainClient, RegisterClient

statusArray = ["AvailAble", "Unavailable", "IN A Meeting", "AFK (Away From Keyboard)",]

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def app_thread(xmpp, brk):
    while True:
        # Run the XMPP Client
        try:
            xmpp.process(forever=True, timeout=3)
        except:
            print("XMPP Client Error!!!")
        if brk(): 
            break
        time.sleep(0.2)
    xmpp.got_disconnected()
    return

def start():
    while True: 
        print("1. Register \n2. Login \n3. Remove Account \n4. Exit")
        opt = int(input('Choose one: '))

        # Register User
        if opt == 1:
            jid = input("JID (example@alumchat.fun): ")
            password = getpass("Password: ")
            xmpp_client = RegisterClient(jid, password)
            xmpp_client.connect()
            xmpp_client.process(forever=False)

        # Login User
        elif opt == 2:
            jid = input("JID (example@alumchat.fun): ")
            password = getpass("Password: ")
            status = "Available"

            while True:
                statusOpt = 0
                statusMsg = "Available"
                
                try:
                    print("1. Available \n2. Unavailable \n3. AFK \n4. In a meeting")
                    statusOpt = int(input('Choose your status: '))
                    
                    if statusOpt < 1 or statusOpt > 4:
                        print("Invalid option, Try Again")
                        continue

                    statusMsg = input("Status message: ")
                except:
                    print("Invalid option, Try Again")
                    continue

                status = statusArray[statusOpt - 1]
                break
            
            xmpp_client = MainClient(jid, password, status, statusMsg)
            xmpp_client.connect()

        # Exit
        elif opt == 4:
            return
        else:
            print("Invalid option, Try Again")
            continue

start()
exit(1)
