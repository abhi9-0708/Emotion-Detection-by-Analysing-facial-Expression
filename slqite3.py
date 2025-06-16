import sqlite3

class DatabaseManager:
    def __init__(self, db_name="users.db"):
        self.db_name = db_name
        self.create_tables()

    def connect(self):
        return sqlite3.connect(self.db_name)

    def create_tables(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            # Create Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                )
            ''')
            
            # Create Feedback table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    feedback_text TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    # -------------------- USERS CRUD Operations --------------------
    def add_user(self, name, email):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
            conn.commit()
            print(f"User {name} added.")

    def get_users(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            return cursor.fetchall()

    def update_user_email(self, user_id, new_email):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))
            conn.commit()
            print("User email updated.")

    def delete_user(self, email):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email = ?", (email,))
            conn.commit()
            print(f"User with email {email} deleted.")

    # -------------------- FEEDBACK CRUD Operations --------------------
    def add_feedback(self, user_id, feedback_text):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO feedback (user_id, feedback_text) VALUES (?, ?)", (user_id, feedback_text))
            conn.commit()
            print("Feedback added.")

    def get_feedback(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feedback")
            return cursor.fetchall()

    def delete_feedback(self, feedback_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
            conn.commit()
            print("Feedback deleted.")

    # -------------------- LOGS CRUD Operations --------------------
    def add_log(self, action):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO logs (action) VALUES (?)", (action,))
            conn.commit()
            print("Log added.")

    def get_logs(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM logs")
            return cursor.fetchall()

    def delete_logs(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM logs")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'logs'")
            conn.commit()
            print("All logs deleted.")

# Example Usage
db = DatabaseManager()
# db.add_user("Alice", "alice@example.com")
# db.add_feedback(1, "Great service!")
# db.add_log("User Alice added.")

# print("Users:", db.get_users())
# print("Feedback:", db.get_feedback())
# print("Logs:", db.get_logs())
