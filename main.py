import time
from getpass import getpass
import asyncio
import threading
from xmpp import Client, RegisterClient, DeleteClient

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
            
            xmpp_client = Client(jid, password, status, statusMsg)
            xmpp_client.connect()

            # Threading options
            stop_threads = False
            xmpp_app_thread = threading.Thread(target = app_thread, args=(xmpp_client, lambda : stop_threads,))
            xmpp_app_thread.start()

            time.sleep(3)

            # Timeout connection
            if xmpp_client.clientOffline:
                time.sleep(2)
                if xmpp_client.clientOffline:
                    print("Can't connect to OpenFire server, try again.\n")
                    stop_threads = True
                    xmpp_app_thread.join()
                    return

            # When Logged
            while True:
                print("1. Private Messages \n2. Send Private Message \n3. Add Contact \n4. Show Contacts \n5. Show Contact Info \n6. Room Chats \n7. Logout")
                secOpt = int(input('Choose one: '))
                
                # Show private messages
                if secOpt == 1:
                    if len(xmpp_client.messages.keys()) == 0:
                        print("Your don't have new messages.")
                        continue
                    print("Choose one of the following chats:")
                    chatNumber = 1
                    for key in xmpp_client.messages.keys():
                        print(f"{chatNumber}. Chat with {key}")
                        chatNumber += 1

                    # User select conversation
                    try:
                        chat = int(input("Choose one: "))
                    except:
                        print("Choose a valid option")
                        continue
                    
                    if chat < 1 or chat > len(xmpp_client.messages.keys()):
                        print("Choose a valid option")
                    else:
                        # Get user and messages
                        otherUser = list(xmpp_client.messages.keys())[chat - 1]
                        messages_sent = xmpp_client.messages[otherUser]["messages"]
                        xmpp_client.last_chat_with = otherUser
                        xmpp_client.pm_send_state_message(f"{otherUser}@alumchat.fun", "active")

                        print(f"\n******* Chat with {otherUser} *******")
                        print("* Write and press enter to respond (/f for Send a File and /exit or /e to Exit) *")

                        for message_history in messages_sent:
                            print(message_history)

                        while True:
                            message = input('-> ')

                            # Options
                            if message == '/exit' or message == '/e' :
                                xmpp_client.pm_send_state_message(f"{otherUser}@alumchat.fun", "paused")
                                break
                            elif '/f ' in message:
                                filename = message.split()[1]
                                xmpp_client.file_sender(otherUser, filename)
                            else:
                                # Send Response  
                                xmpp_client.direct_message(f"{otherUser}@alumchat.fun", message)

                        xmpp_client.current_chat_with = None

                # Send private message
                elif secOpt == 2:
                    message_to = input("To: ")
                    message = input("Message: ")
                    xmpp_client.direct_message(message_to, message)
                
                # Add contact
                elif secOpt == 3:
                    message_to = input("Name: ")
                    xmpp_client.send_contact_subscription(message_to)
                
                # Show contacts
                elif secOpt == 4:
                    print("\n ******** CONTACTS ******** ")
                    xmpp_client.show_contacts()

                # Show contact info
                elif secOpt == 5:
                    jid = input("JID: ")
                    print("\n ******** CONTACTS ******** ")
                    xmpp_client.show_contact_by_jid(jid)

                # Room options
                elif secOpt == 6:
                    while True:
                        try:
                            print("1. Join Room \n2. Create Room \n3. Show Rooms \n4. Back")
                            room_option = int(input('> '))

                            # Check option is in range
                            if room_option < 1 or room_option > 4:
                                print("Choose a valid option")
                                continue

                            break
                        except:
                            room_option = 4
                            break
                    
                    # Back
                    if room_option == 4:
                        continue
                    
                    # Show rooms
                    elif room_option == 3:
                        xmpp_client.muc_discover_rooms()
                        continue
                    
                    # Room Options
                    room = input("Room: ")
                    username = input("Username: ")

                    # Create Room
                    if room_option == 2:
                        asyncio.run(xmpp_client.muc_create_room(room, username))
                    
                    # Join room
                    elif room_option == 1:
                        xmpp_client.muc_join(room, username)

                    print(f"\n******** Group Chat: {room} ********")
                    print("* write and press enter to respond (-exit or /e to Exit) *")

                    while True:
                        try:
                            message = input('-> ')
                            if message == '/exit' or message == '/e':
                                break

                            xmpp_client.muc_send_message(message)
                        except:
                            continue
                    
                    # Leave room on exit
                    xmpp_client.muc_exit_room()

                # Logout
                elif secOpt == 7:
                    stop_threads = True
                    xmpp_app_thread.join()
                    print("Logout Successfully")
                    break
                else:
                    print("Invalid option, Try Again")
                    continue

        # Remove account
        elif opt == 3:
            jid = input("JID: ")
            password = getpass("Password: ")
            xmpp_client = DeleteClient(jid, password)
            xmpp_client.connect()
            xmpp_client.process(forever=False)

        # Exit
        elif opt == 4:
            print("Bye! See You Soon!")
            return
        else:
            print("Invalid option, Try Again")
            continue

start()
exit(1)
