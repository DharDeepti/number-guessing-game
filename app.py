
import random
import sqlite3
import streamlit as st

# ---------- 1. PAGE SETUP ----------

st.set_page_config(
    page_title="Number Guessing Game",
    page_icon="🎯",
    layout="centered"
)

DB_NAME = "game_scores.db"
ATTEMPT_SCORES = [50, 40, 30, 20, 10]


# ---------- 2. DATABASE SETUP ----------

def get_connection():
    return sqlite3.connect(DB_NAME)


def setup_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                total_score INTEGER DEFAULT 0,
                recent_score INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0
            )
        """)


def register_user(username):
    username = username.strip()

    if not username:
        return False, "Username cannot be empty."

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username) VALUES (?)",
                (username,)
            )
        return True, "Registration successful!"

    except sqlite3.IntegrityError:
        return False, "Username already exists. Please log in."


def login_user(username):
    with get_connection() as conn:
        row = conn.execute("""
            SELECT username, total_score,
                   recent_score, games_played
            FROM users
            WHERE username = ?
        """, (username.strip(),)).fetchone()

    if row is None:
        return False

    st.session_state.username = row[0]
    st.session_state.total_score = row[1]
    st.session_state.recent_score = row[2]
    st.session_state.games_played = row[3]
    return True


setup_database()


# ---------- 3. SESSION STATE ----------

defaults = {
    "username": None,
    "total_score": 0,
    "recent_score": 0,
    "games_played": 0,
    "score_history": [],
    "secret_number": None,
    "guesses": [],
    "attempts": 0,
    "score": 0,
    "game_active": False,
    "game_over": False,
    "saved_this_game": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = (
            value.copy() if isinstance(value, list) else value
        )


# ---------- 4. REGISTER / LOGIN SCREEN ----------

st.title("🎯 Number Guessing Game")
st.write("Guess the secret number between 1 and 100.")
st.caption("Five attempts • Maximum 50 points per game")

if st.session_state.username is None:

    register_tab, login_tab = st.tabs(["Register", "Login"])

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Create a username")
            register_clicked = st.form_submit_button("Register")

        if register_clicked:
            success, message = register_user(new_username)
            if success:
                login_user(new_username)
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with login_tab:
        with st.form("login_form"):
            entered_username = st.text_input("Enter your username")
            login_clicked = st.form_submit_button("Login")

        if login_clicked:
            if login_user(entered_username):
                st.rerun()
            else:
                st.error("Username not found. Please register first.")

    st.stop()


# ---------- 5. USER DASHBOARD ----------

st.subheader(f"Welcome, {st.session_state.username}!")

col1, col2, col3 = st.columns(3)
col1.metric("Total score", st.session_state.total_score)
col2.metric("Recent score", st.session_state.recent_score)
col3.metric("Games played", st.session_state.games_played)


def reset_game():
    st.session_state.secret_number = None
    st.session_state.guesses = []
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.game_active = False
    st.session_state.game_over = False
    st.session_state.saved_this_game = False


if st.button("Logout"):
    for key, value in defaults.items():
        st.session_state[key] = (
            value.copy() if isinstance(value, list) else value
        )
    st.rerun()


# ---------- 6. START GAME ----------

if not st.session_state.game_active and not st.session_state.game_over:
    if st.button("Start Game", type="primary"):
        st.session_state.secret_number = random.randint(1, 100)
        st.session_state.guesses = []
        st.session_state.attempts = 0
        st.session_state.score = 0
        st.session_state.game_active = True
        st.session_state.saved_this_game = False
        st.rerun()


# ---------- 7. GUESSING LOGIC ----------

if st.session_state.game_active:
    st.subheader("Make your guess")
    st.write(f"Attempt {st.session_state.attempts + 1} of 5")

    with st.form("guess_form"):
        guess = st.number_input(
            "Choose a number",
            min_value=1,
            max_value=100,
            value=50,
            step=1
        )
        submitted = st.form_submit_button("Submit Guess")

    if submitted:
        guess = int(guess)
        st.session_state.guesses.append(guess)
        st.session_state.attempts += 1

        if guess == st.session_state.secret_number:
            st.session_state.score = ATTEMPT_SCORES[
                st.session_state.attempts - 1
            ]
            st.session_state.game_over = True
            st.session_state.game_active = False

        elif st.session_state.attempts == 5:
            st.session_state.score = 0
            st.session_state.game_over = True
            st.session_state.game_active = False

        st.rerun()

    if st.session_state.guesses:
        st.write("Your guesses:", st.session_state.guesses)

        last_guess = st.session_state.guesses[-1]

        if last_guess == st.session_state.secret_number:
            st.success("Correct guess!")
        elif st.session_state.game_active:
            if last_guess < st.session_state.secret_number:
                st.warning("Too low! Guess higher.")
            else:
                st.warning("Too high! Guess lower.")


# ---------- 8. SAVE FINAL GAME RESULT ----------

if st.session_state.game_over and not st.session_state.saved_this_game:

    score = st.session_state.score

    with get_connection() as conn:
        conn.execute("""
            UPDATE users
            SET total_score = total_score + ?,
                recent_score = ?,
                games_played = games_played + 1
            WHERE username = ?
        """, (
            score,
            score,
            st.session_state.username
        ))

    st.session_state.total_score += score
    st.session_state.recent_score = score
    st.session_state.games_played += 1
    st.session_state.score_history.append(score)
    st.session_state.saved_this_game = True


# ---------- 9. GAME SUMMARY ----------

if st.session_state.game_over:
    st.subheader("Game Summary")

    if st.session_state.score > 0:
        st.success(f"You guessed correctly! Score: {st.session_state.score}")
    else:
        st.error(
            f"Game over! The number was "
            f"{st.session_state.secret_number}."
        )

    st.write("Guesses:", st.session_state.guesses)
    st.write("Recent score:", st.session_state.recent_score)
    st.write("Total score:", st.session_state.total_score)
    st.write("Games played:", st.session_state.games_played)
    st.write("Session score history:", st.session_state.score_history)

    if st.button("Play Again", type="primary"):
        reset_game()
        st.rerun()


# ---------- 10. LEADERBOARD ----------

st.divider()
st.subheader("🏆 Leaderboard")

with get_connection() as conn:
    rows = conn.execute("""
        SELECT username, total_score, games_played
        FROM users
        ORDER BY total_score DESC, username ASC
    """).fetchall()

if rows:
    st.dataframe(
        [
            {
                "Username": row[0],
                "Total Score": row[1],
                "Games Played": row[2]
            }
            for row in rows
        ],
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("No players registered yet.")
