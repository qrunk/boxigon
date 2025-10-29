
"""Simple Discord RPC wrapper using pypresence.

This module provides a minimal, defensive wrapper around pypresence so the
game can update a Rich Presence. If pypresence is not installed or the
connection fails the code will fall back to logging to console instead of
raising errors.

Notes for the user:
- Replace CLIENT_ID with your Discord application's numeric client id for
  full functionality. The wrapper tolerates missing/invalid IDs and missing
  dependency so it won't crash the game.
"""
from __future__ import annotations

import threading
import time
import typing
import os

try:
	from pypresence import Presence
except Exception:
	Presence = None  # type: ignore

# Default placeholder - replace with your own app id to actually connect.
CLIENT_ID = os.environ.get('BOXIGON_DISCORD_CLIENT_ID', 'REPLACE_WITH_CLIENT_ID')


class _DiscordRPC:
	def __init__(self, client_id: str = CLIENT_ID) -> None:
		self.client_id = client_id
		self._rpc = None
		self._connected = False
		self._thread: typing.Optional[threading.Thread] = None
		self._running = False
		self._lock = threading.Lock()
		# keep last activity so background thread can refresh it
		self._last_activity: typing.Dict[str, typing.Any] = {}

	def start(self) -> None:
		"""Attempt to connect to Discord RPC. Non-fatal if it fails."""
		if Presence is None:
			print("DiscordRPC: pypresence not installed, presence disabled")
			return
		if not self.client_id or self.client_id == 'REPLACE_WITH_CLIENT_ID':
			print("DiscordRPC: CLIENT_ID missing or placeholder - presence will not connect")
			return
		try:
			self._rpc = Presence(self.client_id)
			self._rpc.connect()
			self._connected = True
			self._running = True
			# start heartbeat thread to refresh presence periodically
			self._thread = threading.Thread(target=self._heartbeat, daemon=True)
			self._thread.start()
			# set an initial activity so users see something quickly
			self.set_menu()
			print("DiscordRPC: connected")
		except Exception as e:
			print("DiscordRPC: failed to start:", e)
			self._connected = False

	def _heartbeat(self) -> None:
		# Refresh presence every 15 seconds to keep it alive
		while self._running:
			try:
				if self._connected and self._last_activity:
					with self._lock:
						self._rpc.update(**self._last_activity)
			except Exception:
				# ignore and try again later
				pass
			time.sleep(15)

	def shutdown(self) -> None:
		self._running = False
		try:
			if self._rpc and self._connected:
				with self._lock:
					try:
						self._rpc.clear()
					except Exception:
						pass
					try:
						self._rpc.close()
					except Exception:
						pass
		except Exception:
			pass

	def _set_activity(self, details: str | None = None, state: str | None = None, large_image: str | None = None, large_text: str | None = None) -> None:
		# prepare payload without small image
		payload: typing.Dict[str, typing.Any] = {}
		if details is not None:
			payload['details'] = details
		if state is not None:
			payload['state'] = state
		if large_image is not None:
			payload['large_image'] = large_image
		if large_text is not None:
			payload['large_text'] = large_text

		# update last known activity
		self._last_activity = dict(payload)

		if self._connected and self._rpc:
			try:
				with self._lock:
					# pypresence ignores None keys, but be explicit
					self._rpc.update(**payload)
			except Exception:
				# don't let presence errors bubble up
				pass
		else:
			# fallback: log to console for debugging
			print("DiscordRPC (mock update):", payload)

	# Convenience helpers used by the game
	def set_menu(self) -> None:
		# Show large image only, no small image
		self._set_activity(details="In the menus", state=None, large_image="boxigon", large_text="Main Menu")

	def set_game(self, mode: str = 'singleplayer') -> None:
		# details: first line, state: second line
		details = "In the Box"
		state = mode
		self._set_activity(details=details, state=state, large_image="boxigon", large_text="Boxigon")


# Module-level singleton
_client = _DiscordRPC()


def start() -> None:
	_client.start()


def shutdown() -> None:
	_client.shutdown()


def set_menu() -> None:
	_client.set_menu()


def set_game(mode: str = 'singleplayer') -> None:
	_client.set_game(mode)

