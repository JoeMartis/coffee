"""Coffee RPG - Game state management."""

import random
import string
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    LOBBY = "lobby"
    SETUP = "setup"
    BREW = "brew"
    POUR = "pour"
    ENDED = "ended"


class CoffeeStyle(str, Enum):
    BLACK = "black"
    MILK = "milk"
    MILK_AND_SUGAR = "milk_and_sugar"


class GameLength(str, Enum):
    ESPRESSO = "espresso"      # 3 sips each
    GRANDE = "grande"          # 2 sips each
    VENTI = "venti"            # 1 sip each
    OPEN = "open"              # play until group decides


STYLE_DESCRIPTIONS = {
    CoffeeStyle.BLACK: "Sharper moments, heavier choices, stronger consequences.",
    CoffeeStyle.MILK: "Softer scenes, smaller risks, gentler outcomes.",
    CoffeeStyle.MILK_AND_SUGAR: "Lighthearted scenes, gentle stories, humour, friendly outcomes.",
}

LENGTH_DESCRIPTIONS = {
    GameLength.ESPRESSO: "3 Sips each — best for 2–3 players",
    GameLength.GRANDE: "2 Sips each — best for 4–5 players",
    GameLength.VENTI: "1+ Sip each — best for 6+ players",
    GameLength.OPEN: "Play until the story feels complete or sugar runs out",
}


@dataclass
class SideCharacter:
    name: str
    description: str
    positive: bool  # True = helpful, False = hindering
    introduced_by: str  # player id
    introduced_sip: int


@dataclass
class Sip:
    """One complete turn: Brew (resolve) + Pour (new scene)."""
    number: int
    narrator_id: str
    # Brew
    die_result: Optional[int] = None
    favorable: Optional[bool] = None
    sugar_used: bool = False
    sugar_used_by: Optional[str] = None
    brew_narration: str = ""
    die_revealed: bool = False
    # Pour
    pour_narration: str = ""
    pour_question: str = ""
    coffee_action: Optional[str] = None  # "drunk" or "spilled" or None
    side_character: Optional[SideCharacter] = None


@dataclass
class Player:
    id: str
    name: str
    sid: str  # socket id
    connected: bool = True
    is_host: bool = False


@dataclass
class Game:
    room_code: str
    players: dict = field(default_factory=dict)  # id -> Player
    turn_order: list = field(default_factory=list)  # list of player ids
    phase: Phase = Phase.LOBBY
    coffee_style: Optional[CoffeeStyle] = None
    game_length: Optional[GameLength] = None
    sugar: int = 0
    current_turn_index: int = 0
    sips: list = field(default_factory=list)
    current_sip: Optional[Sip] = None
    sip_count: int = 0
    # Brew sub-phase tracking
    brew_phase: str = "rolling"  # rolling -> narrating -> revealed
    # Safety tools
    lines: list = field(default_factory=list)
    veils: list = field(default_factory=list)
    x_card_active: bool = False
    # Side characters
    side_characters: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def current_narrator_id(self) -> Optional[str]:
        if not self.turn_order:
            return None
        return self.turn_order[self.current_turn_index % len(self.turn_order)]

    @property
    def max_sips(self) -> Optional[int]:
        if self.game_length == GameLength.ESPRESSO:
            return 3 * len(self.players)
        elif self.game_length == GameLength.GRANDE:
            return 2 * len(self.players)
        elif self.game_length == GameLength.VENTI:
            return 1 * len(self.players)
        return None  # open-ended

    def player_sip_counts(self) -> dict:
        counts = {pid: 0 for pid in self.turn_order}
        for sip in self.sips:
            if sip.narrator_id in counts:
                counts[sip.narrator_id] += 1
        if self.current_sip and self.current_sip.narrator_id in counts:
            counts[self.current_sip.narrator_id] += 1
        return counts

    def to_dict(self, for_player_id: Optional[str] = None) -> dict:
        """Serialize game state. Hides die result if not yet revealed."""
        current_sip_data = None
        if self.current_sip:
            s = self.current_sip
            current_sip_data = {
                "number": s.number,
                "narrator_id": s.narrator_id,
                "narrator_name": self.players[s.narrator_id].name if s.narrator_id in self.players else "?",
                "die_revealed": s.die_revealed,
                "brew_narration": s.brew_narration,
                "pour_narration": s.pour_narration,
                "pour_question": s.pour_question,
                "coffee_action": s.coffee_action,
                "sugar_used": s.sugar_used,
                "sugar_used_by": s.sugar_used_by,
                "favorable": s.favorable if s.die_revealed else None,
                "die_result": s.die_result if s.die_revealed or for_player_id == s.narrator_id else None,
                "side_character": {
                    "name": s.side_character.name,
                    "description": s.side_character.description,
                    "positive": s.side_character.positive,
                } if s.side_character else None,
            }

        past_sips = []
        for s in self.sips:
            past_sips.append({
                "number": s.number,
                "narrator_id": s.narrator_id,
                "narrator_name": self.players[s.narrator_id].name if s.narrator_id in self.players else "?",
                "die_result": s.die_result,
                "favorable": s.favorable,
                "sugar_used": s.sugar_used,
                "brew_narration": s.brew_narration,
                "pour_narration": s.pour_narration,
                "pour_question": s.pour_question,
                "coffee_action": s.coffee_action,
                "side_character": {
                    "name": s.side_character.name,
                    "description": s.side_character.description,
                    "positive": s.side_character.positive,
                } if s.side_character else None,
            })

        players_list = []
        for pid in self.turn_order:
            if pid in self.players:
                p = self.players[pid]
                players_list.append({
                    "id": p.id,
                    "name": p.name,
                    "connected": p.connected,
                    "is_host": p.is_host,
                })
        # Add players not yet in turn order
        for pid, p in self.players.items():
            if pid not in self.turn_order:
                players_list.append({
                    "id": p.id,
                    "name": p.name,
                    "connected": p.connected,
                    "is_host": p.is_host,
                })

        side_chars = [{
            "name": sc.name,
            "description": sc.description,
            "positive": sc.positive,
        } for sc in self.side_characters]

        return {
            "room_code": self.room_code,
            "phase": self.phase.value,
            "brew_phase": self.brew_phase,
            "coffee_style": self.coffee_style.value if self.coffee_style else None,
            "game_length": self.game_length.value if self.game_length else None,
            "sugar": self.sugar,
            "current_narrator_id": self.current_narrator_id,
            "current_turn_index": self.current_turn_index,
            "players": players_list,
            "current_sip": current_sip_data,
            "past_sips": past_sips,
            "sip_count": self.sip_count,
            "max_sips": self.max_sips,
            "side_characters": side_chars,
            "lines": self.lines,
            "veils": self.veils,
            "x_card_active": self.x_card_active,
        }


class GameManager:
    """Manages all active games."""

    def __init__(self):
        self.games: dict[str, Game] = {}  # room_code -> Game
        self.player_rooms: dict[str, str] = {}  # sid -> room_code

    def generate_room_code(self) -> str:
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            if code not in self.games:
                return code

    def create_game(self, host_name: str, sid: str) -> tuple[Game, Player]:
        code = self.generate_room_code()
        player_id = self._gen_player_id()
        player = Player(id=player_id, name=host_name, sid=sid, is_host=True)
        game = Game(room_code=code, players={player_id: player})
        self.games[code] = game
        self.player_rooms[sid] = code
        return game, player

    def join_game(self, room_code: str, player_name: str, sid: str) -> tuple[Optional[Game], Optional[Player], str]:
        code = room_code.upper().strip()
        if code not in self.games:
            return None, None, "Room not found."
        game = self.games[code]
        if game.phase != Phase.LOBBY:
            return None, None, "Game already in progress."
        if len(game.players) >= 10:
            return None, None, "Room is full. Consider hiring mercenaries and invading Belgium instead."
        player_id = self._gen_player_id()
        player = Player(id=player_id, name=player_name, sid=sid)
        game.players[player_id] = player
        self.player_rooms[sid] = code
        return game, player, ""

    def start_game(self, game: Game, coffee_style: str, game_length: str):
        game.coffee_style = CoffeeStyle(coffee_style)
        game.game_length = GameLength(game_length)
        game.sugar = math.ceil(len(game.players) / 2)
        game.turn_order = list(game.players.keys())
        random.shuffle(game.turn_order)
        game.phase = Phase.BREW
        game.current_turn_index = 0
        game.sip_count = 1
        game.current_sip = Sip(number=1, narrator_id=game.current_narrator_id)
        game.brew_phase = "rolling"

    def roll_die(self, game: Game) -> int:
        result = random.randint(1, 6)
        game.current_sip.die_result = result
        game.current_sip.favorable = (result % 2 == 0)
        game.brew_phase = "narrating"
        return result

    def use_sugar(self, game: Game, player_id: str) -> bool:
        if game.sugar <= 0:
            return False
        if game.current_sip.sugar_used:
            return False
        if game.brew_phase != "narrating":
            return False
        if game.current_sip.die_revealed:
            return False
        game.sugar -= 1
        game.current_sip.sugar_used = True
        game.current_sip.sugar_used_by = player_id
        game.current_sip.favorable = not game.current_sip.favorable
        return True

    def submit_brew(self, game: Game, narration: str):
        game.current_sip.brew_narration = narration
        game.current_sip.die_revealed = True
        game.brew_phase = "revealed"
        game.phase = Phase.POUR

    def submit_pour(self, game: Game, narration: str, question: str,
                    coffee_action: Optional[str] = None,
                    side_char_name: Optional[str] = None,
                    side_char_desc: Optional[str] = None):
        sip = game.current_sip
        sip.pour_narration = narration
        sip.pour_question = question
        sip.coffee_action = coffee_action

        if coffee_action and side_char_name:
            sc = SideCharacter(
                name=side_char_name,
                description=side_char_desc or "",
                positive=(coffee_action == "drunk"),
                introduced_by=sip.narrator_id,
                introduced_sip=sip.number,
            )
            sip.side_character = sc
            game.side_characters.append(sc)

        # Complete this sip and advance
        game.sips.append(sip)
        game.current_turn_index += 1
        game.sip_count += 1

        # Check if game should end
        if self._should_end(game):
            game.phase = Phase.ENDED
            game.current_sip = None
            return

        # Next sip
        game.current_sip = Sip(
            number=game.sip_count,
            narrator_id=game.current_narrator_id,
        )
        game.phase = Phase.BREW
        game.brew_phase = "rolling"

    def end_game(self, game: Game):
        game.phase = Phase.ENDED
        game.current_sip = None

    def x_card(self, game: Game):
        """Activate X-Card - signals that current content should be reframed."""
        game.x_card_active = True

    def clear_x_card(self, game: Game):
        game.x_card_active = False

    def handle_disconnect(self, sid: str) -> Optional[Game]:
        if sid not in self.player_rooms:
            return None
        code = self.player_rooms.pop(sid)
        if code not in self.games:
            return None
        game = self.games[code]
        for p in game.players.values():
            if p.sid == sid:
                p.connected = False
                break
        # Clean up empty games
        if not any(p.connected for p in game.players.values()):
            del self.games[code]
            return None
        return game

    def handle_reconnect(self, sid: str, player_id: str, room_code: str) -> tuple[Optional[Game], Optional[Player]]:
        code = room_code.upper().strip()
        if code not in self.games:
            return None, None
        game = self.games[code]
        if player_id not in game.players:
            return None, None
        player = game.players[player_id]
        player.sid = sid
        player.connected = True
        self.player_rooms[sid] = code
        return game, player

    def _should_end(self, game: Game) -> bool:
        if game.sugar <= 0 and game.game_length == GameLength.OPEN:
            return True
        max_sips = game.max_sips
        if max_sips and game.sip_count > max_sips:
            return True
        return False

    def _gen_player_id(self) -> str:
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
