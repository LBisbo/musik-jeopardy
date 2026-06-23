from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import math
import os
import time

app = Flask(__name__)

BUZZ_TIME_SECONDS = 10
ANSWER_TIME_SECONDS = 30
REBUZZ_TIME_SECONDS = 5

with open("quiz.json", "r", encoding="utf-8") as file:
    quiz = json.load(file)


def build_rounds():
    rounds = list(quiz.get("rounds", []))

    if quiz.get("tiebreaker"):
        rounds.append({
            "name": "Tie-breaker",
            "categories": [
                {
                    "name": quiz["tiebreaker"].get("name", "Tie-breaker"),
                    "questions": quiz["tiebreaker"].get("questions", [])
                }
            ]
        })

    return rounds


rounds = build_rounds()

state = {
    "teams": {},
    "current_round_index": 0,
    "used_questions": [],
    "active_question": None,
    "audience_view": "board",
    "current_buzz": None,
    "phase": "idle",
    "timer_end": None,
    "timer_duration": 0,
    "last_message": ""
}


def question_key(round_index, category_index, question_index):
    return f"r{round_index}-c{category_index}-q{question_index}"


def get_question(round_index, category_index, question_index):
    return rounds[round_index]["categories"][category_index]["questions"][question_index]


def public_question_payload(round_index, category_index, question_index):
    category = rounds[round_index]["categories"][category_index]
    question = category["questions"][question_index]

    return {
        "key": question_key(round_index, category_index, question_index),
        "round_index": round_index,
        "category_index": category_index,
        "question_index": question_index,
        "round_name": rounds[round_index]["name"],
        "category_name": category["name"],
        "points": question.get("points", 0),
        "question": question.get("question", ""),
        "answer": question.get("answer", ""),
        "question2": question.get("question2"),
        "answer2": question.get("answer2"),
        "gold": bool(question.get("gold", False)),
        "music": bool(question.get("music", False))
    }


def start_timer(seconds):
    state["timer_duration"] = seconds
    state["timer_end"] = time.time() + seconds


def stop_timer():
    state["timer_end"] = None
    state["timer_duration"] = 0


def timer_remaining():
    if not state["timer_end"]:
        return None

    return max(0, math.ceil(state["timer_end"] - time.time()))


def mark_active_question_used():
    active = state["active_question"]

    if active and active["key"] not in state["used_questions"]:
        state["used_questions"].append(active["key"])


def return_to_board():
    state["active_question"] = None
    state["audience_view"] = "board"
    state["current_buzz"] = None
    state["phase"] = "idle"
    stop_timer()


def handle_timer_expiry():
    remaining = timer_remaining()

    if remaining is None or remaining > 0:
        return

    if state["phase"] == "awaiting_buzz":
        mark_active_question_used()
        state["last_message"] = "Ingen buzzede i tide. Spørgsmålet er afsluttet."
        return_to_board()

    elif state["phase"] == "answering":
        stop_timer()


def serialize_rounds():
    serialized = []

    for round_index, round_data in enumerate(rounds):
        categories = []

        for category_index, category in enumerate(round_data.get("categories", [])):
            questions = []

            for question_index, question in enumerate(category.get("questions", [])):
                key = question_key(round_index, category_index, question_index)
                questions.append({
                    "key": key,
                    "points": question.get("points", 0),
                    "question": question.get("question", ""),
                    "answer": question.get("answer", ""),
                    "question2": question.get("question2"),
                    "answer2": question.get("answer2"),
                    "gold": bool(question.get("gold", False)),
                    "music": bool(question.get("music", False)),
                    "used": key in state["used_questions"]
                })

            categories.append({
                "name": category.get("name", ""),
                "questions": questions
            })

        serialized.append({
            "name": round_data.get("name", f"Runde {round_index + 1}"),
            "categories": categories
        })

    return serialized


@app.route("/")
def home():
    return redirect(url_for("host"))


@app.route("/host")
def host():
    return render_template("host.html")


@app.route("/audience")
def audience():
    return render_template("audience.html")


@app.route("/buzzer")
def buzzer():
    return render_template("buzzer.html")


@app.route("/status")
def status():
    handle_timer_expiry()

    return jsonify({
        "title": quiz.get("title", "Musik Jeopardy"),
        "rounds": serialize_rounds(),
        "teams": state["teams"],
        "current_round_index": state["current_round_index"],
        "used_questions": state["used_questions"],
        "active_question": state["active_question"],
        "audience_view": state["audience_view"],
        "current_buzz": state["current_buzz"],
        "phase": state["phase"],
        "timer_remaining": timer_remaining(),
        "last_message": state["last_message"],
        "settings": {
            "buzz_time_seconds": BUZZ_TIME_SECONDS,
            "answer_time_seconds": ANSWER_TIME_SECONDS,
            "rebuzz_time_seconds": REBUZZ_TIME_SECONDS
        }
    })


@app.route("/join", methods=["POST"])
def join():
    data = request.get_json() or {}
    team_name = data.get("team_name", "").strip()

    if not team_name:
        return jsonify({"ok": False, "error": "Holdnavn mangler"}), 400

    if team_name not in state["teams"]:
        state["teams"][team_name] = 0

    return jsonify({
        "ok": True,
        "team_name": team_name,
        "teams": state["teams"]
    })


@app.route("/switch_round", methods=["POST"])
def switch_round():
    data = request.get_json() or {}
    index = int(data.get("round_index", 0))

    if 0 <= index < len(rounds):
        state["current_round_index"] = index
        return_to_board()

    return jsonify({"ok": False, "error": "Ugyldig runde"}), 400


@app.route("/open_question", methods=["POST"])
def open_question():
    data = request.get_json() or {}

    round_index = int(data.get("round_index", state["current_round_index"]))
    category_index = int(data.get("category_index"))
    question_index = int(data.get("question_index"))

    key = question_key(round_index, category_index, question_index)

    if key in state["used_questions"]:
        return jsonify({"ok": False, "error": "Spørgsmålet er allerede brugt"}), 400

    payload = public_question_payload(round_index, category_index, question_index)

    state["active_question"] = payload
    state["current_round_index"] = round_index
    state["current_buzz"] = None
    state["last_message"] = ""

    if payload["music"]:
        state["audience_view"] = "music_intro"
        state["phase"] = "music_intro"
        stop_timer()
    else:
        state["audience_view"] = "question"
        state["phase"] = "awaiting_buzz"
        start_timer(BUZZ_TIME_SECONDS)

    return jsonify({"ok": True})


@app.route("/reveal_question", methods=["POST"])
def reveal_question():
    if not state["active_question"]:
        return jsonify({"ok": False, "error": "Intet aktivt spørgsmål"}), 400

    state["audience_view"] = "question"
    state["phase"] = "awaiting_buzz"
    state["current_buzz"] = None
    start_timer(BUZZ_TIME_SECONDS)

    return jsonify({"ok": True})


@app.route("/buzz", methods=["POST"])
def buzz():
    handle_timer_expiry()

    data = request.get_json() or {}
    team_name = data.get("team_name", "").strip()

    if not team_name:
        return jsonify({"ok": False, "error": "Holdnavn mangler"}), 400

    if team_name not in state["teams"]:
        state["teams"][team_name] = 0

    if state["phase"] != "awaiting_buzz":
        return jsonify({
            "ok": False,
            "current_buzz": state["current_buzz"],
            "message": "Buzzeren er ikke åben lige nu"
        })

    if state["current_buzz"] is None:
        state["current_buzz"] = team_name
        state["phase"] = "answering"
        start_timer(ANSWER_TIME_SECONDS)

    return jsonify({
        "ok": True,
        "current_buzz": state["current_buzz"]
    })


@app.route("/reset_buzz", methods=["POST"])
def reset_buzz():
    if not state["active_question"]:
        state["current_buzz"] = None
        state["phase"] = "idle"
        stop_timer()
        return jsonify({"ok": True})

    state["current_buzz"] = None
    state["phase"] = "awaiting_buzz"
    start_timer(REBUZZ_TIME_SECONDS)

    return jsonify({"ok": True})


@app.route("/score", methods=["POST"])
def score():
    data = request.get_json() or {}
    team_name = data.get("team_name", "").strip()
    points = int(data.get("points", 0))

    if team_name in state["teams"]:
        state["teams"][team_name] += points

    return jsonify({
        "ok": True,
        "teams": state["teams"]
    })


@app.route("/answer_correct", methods=["POST"])
def answer_correct():
    data = request.get_json() or {}
    mode = data.get("mode", "normal")

    active = state["active_question"]
    team_name = state["current_buzz"]

    if not active or not team_name:
        return jsonify({"ok": False, "error": "Der mangler aktivt spørgsmål eller buzz-vinder"}), 400

    base_points = int(active.get("points", 0))

    if active.get("gold") and mode == "double":
        points = base_points * 2
    else:
        points = base_points

    if team_name in state["teams"]:
        state["teams"][team_name] += points

    mark_active_question_used()
    return_to_board()

    return jsonify({"ok": True, "awarded": points})


@app.route("/answer_wrong", methods=["POST"])
def answer_wrong():
    active = state["active_question"]
    team_name = state["current_buzz"]

    if not active or not team_name:
        return jsonify({"ok": False, "error": "Der mangler aktivt spørgsmål eller buzz-vinder"}), 400

    points = int(active.get("points", 0))

    if team_name in state["teams"]:
        state["teams"][team_name] -= points

    state["current_buzz"] = None
    state["phase"] = "awaiting_buzz"
    state["audience_view"] = "question"
    start_timer(REBUZZ_TIME_SECONDS)

    return jsonify({"ok": True, "deducted": points})


@app.route("/close_question", methods=["POST"])
def close_question():
    mark_active_question_used()
    return_to_board()
    return jsonify({"ok": True})


@app.route("/cancel_question", methods=["POST"])
def cancel_question():
    return_to_board()
    return jsonify({"ok": True})


@app.route("/reset_game", methods=["POST"])
def reset_game():
    state["teams"].clear()
    state["current_round_index"] = 0
    state["used_questions"].clear()
    state["active_question"] = None
    state["audience_view"] = "board"
    state["current_buzz"] = None
    state["phase"] = "idle"
    state["last_message"] = ""
    stop_timer()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
