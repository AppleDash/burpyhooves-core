import json

from modules import ModuleManager
from permissions import Permissions
from connection import IRCConnection
from hooks import HookManager, EventHook, CommandHook

class BurpyHooves:
	def __init__(self, config):
		self.config = config
		self.me = self.config["me"]
		self.net = self.config["network"]
		self.module_manager = ModuleManager(self)
		self.hook_manager = HookManager(self)
		self.perms = Permissions(self)
		self.connection = IRCConnection(self.net["address"], self.net["port"], self.net["ssl"])
		self.running = True
		self.state = {} # Dict used to hold stuff like last line received and last message etc...

	def run(self):
		self.connection.connect()
		self.raw("NICK %s" % self.me["nicks"][0]) # Nicks thing is a temp hack
		self.raw("USER %s * * :%s" % (self.me["ident"], self.me["gecos"]))

		self.module_manager.load_module("core")

		while self.running:
			self.loop()

	def raw(self, line):
		print("<- %s" % line)
		self.connection.write_line(line)

	def parse_line(self, ln):
		print("-> %s" % ln.linestr)
		if ln.command == "PING":
			self.raw(ln.linestr.replace("PING", "PONG"))
		elif ln.command == "376":
			for channel in self.net["channels"]:
				self.join(channel)

	def loop(self):
		self.connection.loop()
		if self.connection.has_line():
			ln = self.connection.last_line
			self.state["last_line"] = ln
			self.parse_line(ln)
			self.hook_manager.run_hooks(ln)

	def stop(self):
		self.raw("QUIT :Bye!")
		self.connection.disconnect()
		self.running = False

	# Helper functions
	def hook_command(self, cmd, callback):
		self.hook_manager.add_hook(CommandHook(cmd, callback))

	def hook_event(self, event, callback):
		self.hook_event.add_hook(EventHook(event, callback))

	def is_admin(self, hostmask=None):
		if hostmask is None:
			hostmask = self.state["last_line"].hostmask

		return self.perms.check_permission(hostmask, "admin")


	# IRC-related stuff begins here
	def _msg_like(self, verb, target, message):
		self.raw("%s %s :%s" % (verb, target, message))

	def privmsg(self, target, message):
		self._msg_like("PRIVMSG", target, message)

	def act(self, target, action):
		self.privmsg(target, "\x01ACTION %s\x01" % action)

	def notice(self, target, message):
		self._msg_like("NOTICE", target, message)

	def join(self, channel):
		self.raw("JOIN %s" % channel)

	def part(self, channel):
		self.raw("PART %s" % channel)

	# IRC-related stuff that involves state.
	def reply(self, message):
		ln = self.state["last_line"]
		reply_to = ln.hostmask.nick

		if ln.params[0][0] == "#":
			reply_to = ln.params[0]

		self.privmsg(reply_to, message)

	def reply_notice(self, message):
		ln = self.state["last_line"]
		self.notice(ln.hostmask.nick, message)



loaded = json.load(open("./burpyhooves.json"))
bh = BurpyHooves(loaded)
try:
	bh.run()
except KeyboardInterrupt:
	print("\nInterrupted, exiting cleanly!")
	bh.stop()
