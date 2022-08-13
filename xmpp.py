import slixmpp
from slixmpp.exceptions import IqError, IqTimeout
import xml.etree.ElementTree as ET

class MainClient(slixmpp.ClientXMPP):

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
        self.nickname = jid[:jid.index("@")]
        self.status = status
        self.status_message = status_message

        # Event handlers
        self.add_event_handler("session_start", self.start)
        

    async def start(self, event):
        # Send presence
        self.send_presence(pshow=self.status, pstatus=self.status_message)
        
        try:
            # Ask for everyone in server
            await self.get_roster()
            print("\n Login successfully: ",self.local_jid)
            self.is_client_offline = False
        except:
            print("Error on login! Try Again")
            self.disconnect()

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