#!/usr/bin/env python
#
# PyBorg IRC module
#
# Copyright (c) 2000, 2006 Tom Morton, Sebastien Dailly
# Bug Fixes and improvements by Brenton Scott
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#        
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

import sys
import re

try:
	from ircbot import *
	from irclib import *
except:
	print "ERROR !!!!\nircbot.py and irclib.py not found, please install them\n( http://python-irclib.sourceforge.net/ )"
	sys.exit(1)

#overide irclib function
def my_remove_connection(self, connection):
	if self.fn_to_remove_socket:
		self.fn_to_remove_socket(connection._get_socket())

IRC._remove_connection = my_remove_connection

import os
import pyborg
import cfgfile
import random
import time
import traceback
import thread

def get_time():
	"""
	Return time as a nice yummy string
	"""
	return time.strftime("%H:%M:%S", time.localtime(time.time()))

def write_log(name, text):
	"""
	Writes the private conversations to a log file ;)
	"""
	logtime = time.strftime("%d-%m-%Y")
	file = open("./logs/%s-%s.log" % (name, logtime), "a")
	file.write(text+"\n")
	file.close()


class ModIRC(SingleServerIRCBot):
	"""
	Module to interface IRC input and output with the PyBorg learn
	and reply modules.
	"""
	# The bot recieves a standard message on join. The standard part
	# message is only used if the user doesn't have a part message.
	join_msg = "%s"# is here"
	part_msg = "%s"# has left"

	# For security the owner's host mask is stored
	# DON'T CHANGE THIS
	owner_mask = []


	# Command list for this module
	commandlist =   "IRC Module Commands:\n!chans, !ignore, \
!join, !nick, !part, !quit, !quitmsg, !reply2ignored, !replyrate, !shutup, \
!stealth, !unignore, !wakeup, !talk, !owner"
	# Detailed command description dictionary
	commanddict = {
		"shutup": "Owner command. Usage: !shutup\nStop the bot talking",
		"wakeup": "Owner command. Usage: !wakeup\nAllow the bot to talk",
		"join": "Owner command. Usage: !join #chan1 [#chan2 [...]]\nJoin one or more channels",
		"part": "Owner command. Usage: !part #chan1 [#chan2 [...]]\nLeave one or more channels",
		"chans": "Owner command. Usage: !chans\nList channels currently on",
		"nick": "Owner command. Usage: !nick nickname\nChange nickname",
		"ignore": "Owner command. Usage: !ignore [nick1 [nick2 [...]]]\nIgnore one or more nicknames. Without arguments it lists ignored nicknames",
		"unignore": "Owner command. Usage: !unignore nick1 [nick2 [...]]\nUnignores one or more nicknames",
		"replyrate": "Owner command. Usage: !replyrate [rate%]\nSet rate of bot replies to rate%. Without arguments (not an owner-only command) shows the current reply rate",
		"reply2ignored": "Owner command. Usage: !reply2ignored [on|off]\nAllow/disallow replying to ignored users. Without arguments shows the current setting",
		"stealth": "Owner command. Usage: !stealth [on|off]\nTurn stealth mode on or off (disable non-owner commands and don't return CTCP VERSION). Without arguments shows the current setting",
		"quitmsg": "Owner command. Usage: !quitmsg [message]\nSet the quit message. Without arguments show the current quit message",
		"talk": "Owner commande. Usage !talk nick message\nmake the bot send the sentence 'message' to 'nick'",
		"quit": "Owner command. Usage: !quit\nMake the bot quit IRC",
		"owner": "Usage: !owner password\nAllow to become owner of the bot"
	}

	def __init__(self, my_pyborg, args):
		"""
		Args will be sys.argv (command prompt arguments)
		"""
		# PyBorg
		self.pyborg = my_pyborg
		# load settings
		
		self.settings = cfgfile.cfgset()
		self.settings.load("pyborg-irc.cfg",
			{ "myname": ("The bot's nickname", "PyBorg"),
			  "realname": ("Reported 'real name'", "Pyborg"),
			  "owners": ("Owner(s) nickname", [ "OwnerNick" ]),
			  "servers": ("IRC Server to connect to (server, port [,password])", [("irc.gigirc.com", 6667)]),
			  "chans": ("Channels to auto-join", ["#test"]),
			  "speaking": ("Allow the bot to talk on channels", 1),
			  "stealth": ("Hide the fact we are a bot", 1),
			  "ignorelist": ("Ignore these nicknames:", []),
			  "reply2ignored": ("Reply to ignored people", 0),
			  "reply_chance": ("Chance of reply (%) per message", 33),
			  "quitmsg": ("IRC quit message", "Bye :-("),
			  "password": ("password for control the bot (Edit manually !)", "")
			} )

		self.owners = self.settings.owners[:]
		self.chans = self.settings.chans[:]

		# Parse command prompt parameters
		
		for x in xrange(1, len(args)):
			# Specify servers
			if args[x] == "-s":
				self.settings.servers = []
				# Read list of servers
				for y in xrange(x+1, len(args)):
					if args[y][0] == "-":
						break
					server = args[y].split(":")
					# Default port if none specified
					if len(server) == 1:
						server.append("6667")
					self.settings.servers.append( (server[0], int(server[1])) )
			# Channels
			if args[x] == "-c":
				self.settings.chans = []
				# Read list of channels
				for y in xrange(x+1, len(args)):
					if args[y][0] == "-":
						break
					self.settings.chans.append("#"+args[y])
			# Nickname
			if args[x] == "-n":
				try:
					self.settings.myname = args[x+1]
				except IndexError:
					pass

	def our_start(self):
		print "Connecting to server..."
		SingleServerIRCBot.__init__(self, self.settings.servers, self.settings.myname, self.settings.realname, 2)
		self.start()

	def on_welcome(self, c, e):
		for i in self.chans:
			c.join(i)

	def shutdown(self):
		try:
			my_pyborg.kill_timers()
			self.die() # disconnect from server
		except AttributeError, e:
			# already disconnected probably (pingout or whatever)
			my_pyborg.kill_timers()
			pass

	def get_version(self):
		if self.settings.stealth:
			# stealth mode. we shall be a windows luser today
			return "mIRC v6.35 Khaled Mardam-Bey"
		else:
			return self.pyborg.ver_string

	def on_kick(self, c, e):
		"""
		Process leaving
		"""
		# Parse Nickname!username@host.mask.net to Nickname
		kicked = e.arguments()[0]
		kicker = e.source().split("!")[0]
		target = e.target() #channel
		if len(e.arguments()) >= 2:
			reason = e.arguments()[1]
		else:
			reason = ""

		if kicked == self.settings.myname:
			print "[%s] <-- %s was kicked off %s by %s (%s)" % (get_time(), kicked, target, kicker, reason)
			try:
				self.chans.remove(target)
				c.join(target)
				self.chans.append(target)
			finally:
				pass

	def on_privmsg(self, c, e):
		self.on_msg(c, e)
	
	def on_pubmsg(self, c, e):
		self.on_msg(c, e)

	def on_ctcp(self, c, e):
		ctcptype = e.arguments()[0]
		if ctcptype == "ACTION":
			self.on_msg(c, e)
		else:
			SingleServerIRCBot.on_ctcp(self, c, e)

	def _on_disconnect(self, c, e):
		print "Disconnected"
		self.pyborg.kill_timers()
		self.connection.execute_delayed(self.reconnection_interval, self._connected_checker)

	def on_msg(self, c, e):
		"""
		Process messages.
		"""
		# Parse Nickname!username@host.mask.net to Nickname
		source = e.source().split("!")[0]
		target = e.target()

		learn = 1

		# First message from owner 'locks' the owner host mask
		# se people can't change to the owner nick and do horrible
		# stuff like '!unlearn the' :-)
		if not e.source() in self.owner_mask and source in self.owners:
			self.owner_mask.append(e.source())

		# Message text
		if len(e.arguments()) == 1:
			# Normal message
			body = e.arguments()[0]
		else:
			# A CTCP thing
			if e.arguments()[0] == "ACTION":
				body = "+"+e.arguments()[1]
			else:
				# Ignore all the other CTCPs
				return

		# Ignore self.
		if source == self.settings.myname: return

		# We want replies reply_chance%, if speaking is on
		replyrate = self.settings.reply_chance
		not_quiet = self.settings.speaking

		# A 9.5 out of 10 chance of responding seems reasonable for seeing our own nickname ;)
		# Responds to lower use of nickname because some people are lazy...
		if self.settings.myname.lower() in body.lower():
			replyrate = 95

		# Ignore selected nicks
		if self.settings.ignorelist.count(source.lower()) > 0 \
			and self.settings.reply2ignored == 1:
			learn = 0
		elif self.settings.ignorelist.count(source.lower()) > 0: return

		# Ignore quoted and urls
		quoted_message = re.match("( )*(<|\(|\[|\"|'|\.){1}", body[0:2], re.IGNORECASE)
		url_message = re.match("http(s)*:\/\/", body[0:], re.IGNORECASE) 
		if quoted_message and not body[0:2] == "<3" and not body[0:3] == "<.<": return
		if url_message: return

		# Stealth mode. Disables commands for non owners
		if (not source in self.owners) and body[0:1] == "!":
			if (not self.settings.stealth):
				if self.irc_commands(body, source, target, c, e) == 1: return
			else: return

		# Always reply to private messages
		if e.eventtype() == "privmsg":
			replyrate = 100
			not_quiet = 1
			try:
				if body[0] == "!":
					if self.irc_commands(body, source, target, c, e) == 1: return
			except: pass

		# Replaces own nick with #nick
		if e.eventtype() == "pubmsg":
			try:
				if body[0] == "!":
					if self.irc_commands(body, source, target, c, e) == 1: return
			except: pass
			body = body.replace(self.settings.myname, "#nick")
			body = body.replace(self.settings.myname.lower(), "#nick")
			# Some clever tricks for re-using other users' responses:
			for x in self.channels[target].users():
				x = re.sub("[\&\%\+\@\~]","", x)
				if x:
					body = body.replace(x+":", "#nick:")
					body = body.replace("@ "+x, "@ #nick")

		if body == "": return
		
		# Pass message onto pyborg
		if source in self.owners and e.source() in self.owner_mask:
			self.pyborg.process_msg(self, body, replyrate, learn, (body, source, target, c, e), 1, not_quiet)
		else:
			#start a new thread
			thread.start_new_thread(self.pyborg.process_msg, (self, body, replyrate, learn, (body, source, target, c, e), 0, not_quiet))

	def irc_commands(self, body, source, target, c, e):
		"""
		Special IRC commands.
		"""
		msg = ""

		command_list = body.split()
		command_list[0] = command_list[0].lower()

		### User commands
		# Query replyrate
		if command_list[0] == "!replyrate" and len(command_list)==1:
			msg = "Reply rate is "+`self.settings.reply_chance`+"%."

		if command_list[0] == "!owner" and len(command_list) > 1 and source not in self.owners:
			if command_list[1] == self.settings.password:
				self.owners.append(source)
				self.output("You've been added to owners list", ("", source, target, c, e))
			else:
				self.output("Try again", ("", source, target, c, e))

		### Owner commands
		if source in self.owners:

			# Change nick
			if command_list[0] == "!nick":
				try:
					self.connection.nick(command_list[1])
					self.settings.myname = command_list[1]
				except:
					pass
			# stealth mode
			elif command_list[0] == "!stealth":
				msg = "Stealth mode "
				if len(command_list) == 1:
					if self.settings.stealth == 0:
						msg = msg + "off"
					else:
						msg = msg + "on"
				else:
					toggle = command_list[1].lower()
					if toggle == "on":
						msg = msg + "on"
						self.settings.stealth = 1
					else:
						msg = msg + "off"
						self.settings.stealth = 0

			# Allow/disallow replying to ignored nicks
			# (they will never be learnt from)
			elif command_list[0] == "!reply2ignored":
				msg = "Replying to ignored users "
				if len(command_list) == 1:
					if self.settings.reply2ignored == 0:
						msg = msg + "off"
					else:
						msg = msg + "on"
				else:
					toggle = command_list[1]
					if toggle == "on":
						msg = msg + "on"
						self.settings.reply2ignored = 1
					else:
						msg = msg + "off"
						self.settings.reply2ignored = 0
			# Stop talking
			elif command_list[0] == "!shutup":
				if self.settings.speaking == 1:
					msg = "I'll be quiet :-("
					self.settings.speaking = 0
				else:
					msg = ":-x"
			# Wake up again
			elif command_list[0] == "!wakeup":
				if self.settings.speaking == 0:
					self.settings.speaking = 1
					msg = "Whoohoo!"
				else:
					msg = "But i'm already awake..."
						
			# Join a channel or list of channels
			elif command_list[0] == "!join":
				for x in xrange(1, len(command_list)):
					if not command_list[x] in self.chans:
						msg = "Attempting to join channel %s" % command_list[x]
						self.chans.append(command_list[x])
						c.join(command_list[x])

			# Part a channel or list of channels
			elif command_list[0] == "!part":
				for x in xrange(1, len(command_list)):
					if command_list[x] in self.chans:
						msg = "Leaving channel %s" % command_list[x]
						self.chans.remove(command_list[x])
						c.part(command_list[x])

			# List channels currently on
			elif command_list[0] == "!chans":
				if len(self.channels.keys())==0:
					msg = "I'm currently on no channels"
				else:
					msg = "I'm currently on "
					channels = self.channels.keys()
					for x in xrange(0, len(channels)):
						msg = msg+channels[x]+" "
			# add someone to the ignore list
			elif command_list[0] == "!ignore":
				# if no arguments are given say who we are
				# ignoring
				if len(command_list) == 1:
					msg = "I'm ignoring "
					if len(self.settings.ignorelist) == 0:
						msg = msg + "nobody"
					else:
						for x in xrange(0, len(self.settings.ignorelist)):
							msg = msg + self.settings.ignorelist[x] + " "
				# Add everyone listed to the ignore list
				# eg !ignore tom dick harry
				else:
					for x in xrange(1, len(command_list)):
						self.settings.ignorelist.append(command_list[x].lower())
						msg = "done"
			# remove someone from the ignore list
			elif command_list[0] == "!unignore":
				# Remove everyone listed from the ignore list
				# eg !unignore tom dick harry
				for x in xrange(1, len(command_list)):
					try:
						self.settings.ignorelist.remove(command_list[x].lower())
						msg = "done"
					except:
						pass
			# set the quit message
			elif command_list[0] == "!quitmsg":
				if len(command_list) > 1:
					self.settings.quitmsg = body.split(" ", 1)[1]
					msg = "New quit message is \"%s\"" % self.settings.quitmsg
				else:
					msg = "Quit message is \"%s\"" % self.settings.quitmsg
			# make the pyborg quit
			elif command_list[0] == "!quit":
				self.pyborg.kill_timers()
				sys.exit(0)
			# Change reply rate
			elif command_list[0] == "!replyrate":
				try:
					self.settings.reply_chance = int(command_list[1])
					msg = "Now replying to %d%% of messages." % int(command_list[1])
				except:
					msg = "Reply rate is %d%%." % self.settings.reply_chance
			# make the bot talk
			elif command_list[0] == "!talk":
				if len(command_list) >= 2:
					phrase=""
					for x in xrange (2, len (command_list)):
						phrase = phrase + str(command_list[x]) + " "
					self.output(phrase, ("", command_list[1], "", c, e))
	
		if msg == "":
			return 0
		else:
			self.output(msg, ("<none>", source, target, c, e))
			return 1
			
	def output(self, message, args):
		"""
		Output a line of text. args = (body, source, target, c, e)
		"""
		if not self.connection.is_connected():
			print "Can't send reply : not connected to server"
			return

		# Unwrap arguments
		body, source, target, c, e = args

		# Let's try fixing #nick responses...
		message = message.strip().split()
		if message[0] == "#nick,":
			message[0] = "#nick:"
		if message[0] == "#nick;":
			message[0] = "#nick:"
		if message[0] == ":":
			message[0] = "#nick:"
		message = " ".join(message)

		# Fixes the Alia in words bug
		message = message.replace("Austr#nick", "Australia")
		message = message.replace("austr#nick", "Australia")

		# Replace with the target's nickname
		message = message.replace("#nick", source)
		
		# Should we do a action?
		if message[:1] == "+":
			action = 1
			message = message[1:]
		else:
			action = 0
		
		# Joins replies and public messages
		if e.eventtype() == "pubmsg" or e.eventtype() == "ctcp":
			if action == 0:
				c.privmsg(target, message)
			else:
				c.action(target, message)
		# Private messages
		elif e.eventtype() == "privmsg":
			# normal private msg
			if action == 0:
				c.privmsg(source, message)
				# send copy to owner
				if not source in self.owners:
					c.privmsg(','.join(self.owners), "("+source+") "+body)
					write_log(source, "["+get_time()+"] ("+source+") "+body)
					c.privmsg(','.join(self.owners), "("+self.settings.myname+") "+message)
					write_log(source, "["+get_time()+"] ("+self.settings.myname+") "+message)
			# ctcp action priv msg
			else:
				c.action(source, message)
				# send copy to owner
				if not source in self.owners:
					map ( ( lambda x: c.action(x, "* "+source+" "+body) ), self.owners)
					write_log(source, "["+get_time()+"] * "+source+" "+body)
					map ( ( lambda x: c.action(x, "* "+self.settings.myname+" "+message) ), self.owners)
					write_log(source, "["+get_time()+"] * "+self.settings.myname+" "+message)

if __name__ == "__main__":
	
	if "--help" in sys.argv:
		print "Pyborg irc bot. Usage:"
		print " pyborg-irc.py [options]"
		print " -s   server:port"
		print " -c   channel"
		print " -n   nickname"
		print "Defaults stored in pyborg-irc.cfg"
		print
		sys.exit(0)
	# start the pyborg
	my_pyborg = pyborg.pyborg()
	bot = ModIRC(my_pyborg, sys.argv)
	try:
		bot.our_start()
	except KeyboardInterrupt, e:
		my_pyborg.kill_timers()
	except SystemExit, e:
		my_pyborg.kill_timers()
	except:
		traceback.print_exc()
	my_pyborg.kill_timers()
	bot.disconnect(bot.settings.quitmsg)
	del my_pyborg