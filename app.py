"""Coffee RPG - Flask + SocketIO server."""

import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from game import GameManager, Phase

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

gm = GameManager()


# --- HTTP Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/join/<room_code>")
def join_link(room_code):
    """Direct link to join a room."""
    return render_template("index.html", join_code=room_code.upper())


# --- SocketIO Events ---

def broadcast_state(game, event="game_state"):
    """Send personalized state to each player in the room."""
    for pid, player in game.players.items():
        if player.connected:
            emit(event, {
                "state": game.to_dict(for_player_id=pid),
                "your_id": pid,
            }, room=player.sid)


@socketio.on("connect")
def on_connect():
    pass


@socketio.on("disconnect")
def on_disconnect():
    game = gm.handle_disconnect(request.sid)
    if game:
        broadcast_state(game)


@socketio.on("create_game")
def on_create_game(data):
    name = data.get("name", "").strip()
    if not name:
        emit("error", {"message": "Please enter a name."})
        return
    game, player = gm.create_game(name, request.sid)
    join_room(game.room_code)
    emit("game_created", {
        "room_code": game.room_code,
        "player_id": player.id,
        "state": game.to_dict(for_player_id=player.id),
        "your_id": player.id,
    })


@socketio.on("join_game")
def on_join_game(data):
    name = data.get("name", "").strip()
    code = data.get("room_code", "").strip()
    if not name:
        emit("error", {"message": "Please enter a name."})
        return
    if not code:
        emit("error", {"message": "Please enter a room code."})
        return
    game, player, err = gm.join_game(code, name, request.sid)
    if err:
        emit("error", {"message": err})
        return
    join_room(game.room_code)
    emit("game_joined", {
        "room_code": game.room_code,
        "player_id": player.id,
    })
    broadcast_state(game)


@socketio.on("reconnect_game")
def on_reconnect_game(data):
    player_id = data.get("player_id", "")
    room_code = data.get("room_code", "")
    game, player = gm.handle_reconnect(request.sid, player_id, room_code)
    if not game:
        emit("error", {"message": "Could not reconnect."})
        return
    join_room(game.room_code)
    emit("reconnected", {"player_id": player.id})
    broadcast_state(game)


@socketio.on("start_game")
def on_start_game(data):
    game = _get_game()
    if not game:
        return
    player = _get_player(game)
    if not player or not player.is_host:
        emit("error", {"message": "Only the host can start the game."})
        return
    if len(game.players) < 2:
        emit("error", {"message": "Need at least 2 players."})
        return
    coffee_style = data.get("coffee_style", "black")
    game_length = data.get("game_length", "espresso")
    try:
        gm.start_game(game, coffee_style, game_length)
    except ValueError as e:
        emit("error", {"message": str(e)})
        return
    broadcast_state(game)


@socketio.on("roll_die")
def on_roll_die():
    game = _get_game()
    if not game:
        return
    player = _get_player(game)
    if not player:
        return
    if game.phase != Phase.BREW:
        emit("error", {"message": "Not in Brew phase."})
        return
    if player.id != game.current_narrator_id:
        emit("error", {"message": "It's not your turn."})
        return
    if game.brew_phase != "rolling":
        emit("error", {"message": "Die already rolled."})
        return
    gm.roll_die(game)
    broadcast_state(game)


@socketio.on("use_sugar")
def on_use_sugar():
    game = _get_game()
    if not game:
        return
    player = _get_player(game)
    if not player:
        return
    if not gm.use_sugar(game, player.id):
        emit("error", {"message": "Cannot use sugar right now."})
        return
    broadcast_state(game)
    # Notify everyone
    for p in game.players.values():
        if p.connected:
            emit("sugar_used", {
                "by": player.name,
                "sugar_remaining": game.sugar,
            }, room=p.sid)


@socketio.on("submit_brew")
def on_submit_brew(data):
    game = _get_game()
    if not game:
        return
    player = _get_player(game)
    if not player:
        return
    if game.phase != Phase.BREW or player.id != game.current_narrator_id:
        emit("error", {"message": "Not your turn to Brew."})
        return
    narration = data.get("narration", "").strip()
    if not narration:
        emit("error", {"message": "Please write your narration."})
        return
    gm.submit_brew(game, narration)
    broadcast_state(game)


@socketio.on("submit_pour")
def on_submit_pour(data):
    game = _get_game()
    if not game:
        return
    player = _get_player(game)
    if not player:
        return
    if game.phase != Phase.POUR or player.id != game.current_narrator_id:
        emit("error", {"message": "Not your turn to Pour."})
        return
    narration = data.get("narration", "").strip()
    question = data.get("question", "").strip()
    if not narration:
        emit("error", {"message": "Please write your narration."})
        return
    if not question:
        emit("error", {"message": "Please pose a question with two possible outcomes."})
        return
    coffee_action = data.get("coffee_action")  # "drunk", "spilled", or None
    side_char_name = data.get("side_char_name", "").strip() or None
    side_char_desc = data.get("side_char_desc", "").strip() or None
    gm.submit_pour(game, narration, question, coffee_action, side_char_name, side_char_desc)
    broadcast_state(game)


@socketio.on("x_card")
def on_x_card():
    game = _get_game()
    if not game:
        return
    gm.x_card(game)
    for p in game.players.values():
        if p.connected:
            emit("x_card_activated", {}, room=p.sid)


@socketio.on("clear_x_card")
def on_clear_x_card():
    game = _get_game()
    if not game:
        return
    gm.clear_x_card(game)
    broadcast_state(game)


@socketio.on("end_game")
def on_end_game():
    game = _get_game()
    if not game:
        return
    player = _get_player(game)
    if not player or not player.is_host:
        emit("error", {"message": "Only the host can end the game."})
        return
    gm.end_game(game)
    broadcast_state(game)


@socketio.on("update_safety")
def on_update_safety(data):
    game = _get_game()
    if not game:
        return
    if "lines" in data:
        game.lines = [l.strip() for l in data["lines"] if l.strip()]
    if "veils" in data:
        game.veils = [v.strip() for v in data["veils"] if v.strip()]
    broadcast_state(game)


# --- Helpers ---

def _get_game():
    code = gm.player_rooms.get(request.sid)
    if not code or code not in gm.games:
        emit("error", {"message": "Not in a game."})
        return None
    return gm.games[code]


def _get_player(game):
    for p in game.players.values():
        if p.sid == request.sid:
            return p
    emit("error", {"message": "Player not found."})
    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
