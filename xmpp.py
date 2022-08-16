import slixmpp
import asyncio
import webbrowser
import validators
import mimetypes
import uuid
from slixmpp.exceptions import IqError, IqTimeout
import xml.etree.ElementTree as ET

class Client(slixmpp.ClientXMPP):

    def __init__(self, jid, password, status, status_message):
        slixmpp.ClientXMPP.__init__(self, jid, password)
        
        # Plugins
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0004') # Data Forms
        self.register_plugin('xep_0045') # MUC
        self.register_plugin('xep_0060') # PubSub
        self.register_plugin('xep_0066') # Out-of-band Data
        self.register_plugin('xep_0077') # In-band Registration
        self.register_plugin('xep_0133') # Service administration
        self.register_plugin('xep_0199') # XMPP Ping
        self.register_plugin('xep_0363') # Files
        self.register_plugin('xep_0065') # SOCKS5 Bytestreams
        self.register_plugin('xep_0085') # Notifications
        
        self.local_jid = jid
        self.alias = jid[:jid.index("@")]
        self.status = status
        self.status_message = status_message

        # App logic
        self.messages = {}
        self.contacts = {}
        self.actualRoom = ""
        self.roomOwner = False
        self.lastChat = None
        self.clientOffline = True

        # Auto authorize & subscribe on subscription received
        self.roster.auto_authorize = True
        self.roster.auto_subscribe = True
        self.outter_presences = asyncio.Event()

        # Event handlers
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("presence_subscribe", self.new_subscription)
        self.add_event_handler("got_online", self.got_online)
        self.add_event_handler("got_offline", self.got_offline)
        self.add_event_handler("groupchat_message", self.muc_message)
        self.add_event_handler("disco_info",self.show_info)
        self.add_event_handler("disco_items", self.show_info)
        self.add_event_handler("chatstate", self.show_chatstate)

    async def start(self, event):
        # Send presence
        self.send_presence(pshow=self.status, pstatus=self.status_message)
        
        try:
            # Ask for everyone in server
            await self.get_roster()
            print("\n Login successfully: ",self.local_jid)
            self.clientOffline = False
        except:
            print("Error on login! Try Again")
            self.disconnect()

    # Add contact
    def send_contact_subscription(self, recipient):
        try:
            # Subscribe
            self.send_presence_subscription(recipient, self.local_jid)
            print("Contact added: ", recipient)
        except:
            print("Error adding contact!")
    
    # Messages
    def message(self, message):
        if message['type'] == "chat":

            sender = str(message['from'])
            sender = sender[:sender.index("@")]
            body = str(message['body'])
            
            currentMsg = f"{sender}: {body}"

            if sender in self.messages.keys():
                self.messages[sender]["messages"].append(currentMsg)
            else:
                self.messages[sender] = {"messages": [currentMsg]}

            if not self.lastChat == sender:
                print(f"\n NEW MESSAGE FROM {sender}")
            else:
                # If is a message from last chat, just print it
                print(f"\n{currentMsg}")
                print("--> ")
                # Receive images and docs
                if sender != self.alias and validators.url(body):
                    webbrowser.open(body)

    def direct_message(self, recipient, message = ""):
        self.send_message(
            mto = recipient, 
            mbody = message, 
            mtype = "chat", 
            mfrom = self.local_jid
        )

        recipient = recipient[:recipient.index("@")]
        sender = self.local_jid[:self.local_jid.index("@")]

        # Final message
        currentMsg = f"{sender}: {message}"

        if recipient in self.messages.keys():
            self.messages[recipient]["messages"].append(currentMsg)
        else:
            self.messages[recipient] = {"messages":[currentMsg]}

    def muc_message(self, message = ""):
        alias = str(message['mucnick'])
        body = str(message['body'])

        prevSender = alias == self.alias
        valid = self.actualRoom in str(message['from'])
        currentMsg = f"{alias}: {body}"

        if not prevSender and valid:
            print(currentMsg)
            print("--> ")

    def muc_send_message(self, message):
        self.send_message(mto=self.actualRoom, mbody=message, mtype="groupchat")

    def pm_send_state_message(self, recipient, state):
        sender = self.boundjid.bare

        message = self.make_message(
            mto=recipient,
            mfrom=self.boundjid.bare,
            mtype="chat"
        )
        message["chat_state"] = state
        message.send()
    
    # Rooms
    async def muc_create_room(self, room, alias):
        self.actualRoom = room
        self.alias = alias
        self.roomOwner = True
        
        # Create
        self['xep_0045'].join_muc(room, alias)
        self['xep_0045'].set_affiliation(room, self.boundjid, affiliation='owner')

        # Event handlers
        self.add_event_handler(f"muc::{self.actualRoom}::got_online", self.muc_on_join)
        self.add_event_handler(f"muc::{self.actualRoom}::got_offline", self.muc_on_left)

        try:
            query = ET.Element('{http://jabber.org/protocol/muc#owner}query')
            elem = ET.Element('{jabber:x:data}x', type='submit')
            query.append(elem)

            iq = self.make_iq_set(query)
            iq['to'] = room
            iq['from'] = self.boundjid
            iq.send()
        except:
            print("Error on create room")

    def muc_discover_rooms(self):
        try:
            asyncio.run(self.print_my_rooms())
        except (IqError, IqTimeout):
            print("Error on discovering rooms")

    async def print_my_rooms(self):
        try:
            rooms = await self['xep_0030'].get_items(jid = f"conference.alumchat.fun", iterator=True)
            return rooms
        except (IqError, IqTimeout):
            print("Error on discovering rooms")


    def muc_exit_room(self, message = ''):
        self['xep_0045'].leave_muc(self.actualRoom, self.alias, msg=message)
        # Reset
        self.roomOwner = False
        self.actualRoom = None
        self.alias = ''

    def muc_join(self, room, alias):
        # Set local atributes for room
        self.actualRoom = room
        self.alias = alias

        # Join
        self['xep_0045'].join_muc(room, alias, wait=True, maxhistory=False)
        self.add_event_handler(f"muc::{self.actualRoom}::got_online", self.muc_on_join)
        self.add_event_handler(f"muc::{self.actualRoom}::got_offline", self.muc_on_left)


    def muc_on_join(self, presence):
        if presence['muc']['nick'] == self.alias:
            print("Joined to your own room!")
            # Affiliation if its owner
        
        else:
            alias = str(presence['muc']['nick'])
            if self.roomOwner:
                self['xep_0045'].set_affiliation(self.actualRoom, nick=alias, affiliation="member")
            print(f"{alias} has arrived to the room!")
        

    def muc_on_left(self, presence):
        if presence['muc']['nick'] != self.alias:
            alias = presence['muc']['nick']
            print(f"{alias} left the room!")

    def got_online(self, event):
        sender = str(event['from'])
        if "conference" in sender:
            return
        sender = sender[:sender.index("@")]
        eventShow = ""
        eventSts = ""

        # Try getting the show and status
        try:
            eventShow = str(event['show'])
            eventSts = str(event['status'])
        except:
            eventShow = "Available"
            eventSts = "Available"

        self.contacts[sender] = {
            "from": sender, 
            "show": eventShow, 
            "status": eventSts
        }

        if not sender == self.local_jid[:self.local_jid.index("@")]:
            print(f"{sender} IS ONLINE NOW. ({eventSts})")

    def got_offline(self, event):
        sender = str(event['from'])
        if "conference" in sender:
            return

        sender = sender[:sender.index("@")]
        self.contacts[sender]["show"] = "Unavailable"
        self.contacts[sender]["status"] = "Unavailable"

        print(f"{sender} IS NOW OFFLINE")

    def got_disconnected(self):
        createdPresence = self.Presence()
        createdPresence['type'] = "Unavailable"
        # Send stanza
        createdPresence.send()

    # Show info
    def show_info(self, iq):
        if str(iq['type']) == 'result' \
            and "conference" in str(iq['from']):
            
            order = 1
            textShow = ""
            
            print("\n Rooms: ")
            for char in str(iq):
                if len(textShow) > 7 and char == '/':
                    print(f"{str(order)}. {textShow}")
                    textShow = ""
                    order += 1
                    continue

                elif "jid=" in textShow:
                    textShow += char
                    continue
                
                if char in ('j', 'i', 'd', '='):
                    textShow += char
                    if char == 'j':
                        textShow = char
                else:
                    # Reset
                    textShow = ''
        return

    def show_chatstate(self, message):
        sender = str(message['from'])
        state = message["chat_state"]

        username = sender[:sender.index("@")]
        if self.lastChat == username:
            print(f"\n{username} status changed to {state}")
            print("--> ")

    # Contacts
    def show_contacts(self):
        self.get_roster()
        contacts = self.roster[self.local_jid]

        if(len(contacts.keys()) == 0):
            print("No contacts yet...")

        for contact in contacts.keys():
            if contact != self.local_jid:
                # Print contact info
                print(f"Contact: {contact}")
                alias = contact

                if alias in self.contacts.keys():
                    info = self.contacts[alias]['show']
                    status = self.contacts[alias]['status']
                    print(f" INFO: { info }")
                    print(f" STATUS: { status }")

                else:
                    print(f" INFO: Unavailable")
                    print(f" STATUS: Unavailable")

                # Print general info
                print(f" - GROUPS: { contacts[alias]['groups'] }")
                print(f" - SUBS: { contacts[alias]['subscription'] }")
            
    # Presence and status
    def new_subscription(self, createdPresence):
        roster = self.roster[createdPresence['to']]
        item = self.roster[createdPresence['to']][createdPresence['from']]
        autocreate = False

        if item["whitelisted"]:
            item.authorize()
            if roster.auto_subscribe:
                autocreate = True

        # Auto authorize
        elif roster.auto_authorize:
            item.authorize()
            if roster.auto_subscribe:
                autocreate = True

        elif roster.auto_authorize == False:
            item.unauthorize()

        # Subscribe
        if autocreate:
            item.subscribe()

    # File sending
    def file_sender(self, recipient, filename):
        asyncio.run(self.send_file(recipient, filename))

    async def send_file(self, recipient, filename):
        try:
            with open(filename, 'rb') as upfile:
                print(f"\nReading {filename}...")
                file = upfile.read()
            filesize = len(file)
            fileType = mimetypes.guess_type(filename)[0]
            if fileType is None:
                fileType = "application/octet-stream"
            url = await self['xep_0363'].upload_file(
                str(uuid.uuid4()), 
                size=filesize,
                file=file,
                content_type=fileType,
            )
            # Send Response
            self.direct_message(f"{recipient}@alumchat.fun", url)
        except (IqError, IqTimeout):
            print('File transfer errored')
        else:
            print('\nFile transfer finished!!!')

class RegisterClient(slixmpp.ClientXMPP):

    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0004') # Data forms
        self.register_plugin('xep_0066') # Out-of-band Data
        self.register_plugin('xep_0077') # In-band Registration
        
        # Force registration
        self['xep_0077'].force_registration = True

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("register", self.register)

    async def start(self, event):
        self.send_presence()
        # Auto register & disconnect
        await self.get_roster()
        self.disconnect()

    async def register(self, iq):
        res = self.Iq()
        res['type'] = 'set'
        res['register']['username'] = self.boundjid.user
        res['register']['password'] = self.password

        try:
            await res.send()
            print(f"Account registered successfully: {self.boundjid}!")
        except IqError as e:
            print(f"Error on register new account: {e.iq['error']['text']}")
            self.disconnect()
        except IqTimeout:
            print("No response from server.")
            self.disconnect()


class DeleteClient(slixmpp.ClientXMPP):

    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # Plugins
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0004') # Data forms
        self.register_plugin('xep_0066') # Out-of-band Data
        self.register_plugin('xep_0077') # In-band Registration

        # Event handler
        self.add_event_handler("session_start", self.start)

    async def start(self):
        self.send_presence()
        await self.get_roster()
        # Delete & disconnect
        await self.delete()
        self.disconnect()

    async def delete(self):
        response = self.Iq()
        response['type'] = 'set'
        response['from'] = self.boundjid.user
        response['password'] = self.password
        response['register']['remove'] = 'remove'

        try:
            await response.send()
            print(f"Account delete successfully: {self.boundjid}!")
        except IqError as e:
            print(f"Couldn't delete account: {e.iq['error']['text']}")
            self.disconnect()
        except IqTimeout:
            print("No response from server.")
            self.disconnect()