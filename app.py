from flask import Flask, request, render_template, redirect, url_for, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
import os

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host='db',
        database='fitnessdb',
        user='fitnessuser',
        password='fitnesspass'
    )
    return conn

@app.route('/')
def index():
    return render_template('index.html')

# ==================== SQL INJECTION PROTECTION DEMO ====================

@app.route('/sql-injection-demo')
def sql_injection_demo():
    """
    Demonstration page showing SQL injection protection.
    This page will be used in the Stage 3 demo.
    """
    return render_template('sql_injection_demo.html')

@app.route('/search-user-unsafe', methods=['POST'])
def search_user_unsafe():
    """
    UNSAFE VERSION - Vulnerable to SQL Injection (for demonstration only!)
    DO NOT USE THIS IN PRODUCTION
    """
    username = request.form['username']
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # DANGEROUS: String concatenation - vulnerable to SQL injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    
    try:
        cur.execute(query)
        users = cur.fetchall()
        result = {
            'method': 'UNSAFE (String Concatenation)',
            'query': query,
            'vulnerable': True,
            'users': [dict(u) for u in users]
        }
    except Exception as e:
        result = {
            'method': 'UNSAFE',
            'query': query,
            'error': str(e),
            'vulnerable': True
        }
    
    cur.close()
    conn.close()
    return jsonify(result)

@app.route('/search-user-safe', methods=['POST'])
def search_user_safe():
    """
    SAFE VERSION - Protected from SQL Injection using parameterized queries
    """
    username = request.form['username']
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # SAFE: Parameterized query with %s placeholders
    # psycopg2 automatically escapes the input
    query = "SELECT * FROM users WHERE username = %s"
    
    try:
        cur.execute(query, (username,))  # Tuple with parameters
        users = cur.fetchall()
        result = {
            'method': 'SAFE (Parameterized Query)',
            'query': query,
            'parameters': username,
            'vulnerable': False,
            'users': [dict(u) for u in users]
        }
    except Exception as e:
        result = {
            'method': 'SAFE',
            'query': query,
            'error': str(e),
            'vulnerable': False
        }
    
    cur.close()
    conn.close()
    return jsonify(result)

# ==================== INDEXES DEMO ====================

@app.route('/indexes-demo')
def indexes_demo():
    """Show which indexes exist and explain their purpose"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Query to get all indexes on our tables
    cur.execute("""
        SELECT 
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename IN ('users', 'workouts', 'exercises', 'workout_exercises')
        ORDER BY tablename, indexname;
    """)
    
    indexes = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('indexes_demo.html', indexes=indexes)

@app.route('/explain-query', methods=['POST'])
def explain_query():
    """
    Show EXPLAIN output for a query to demonstrate index usage
    """
    query_type = request.form.get('query_type')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    queries = {
        'date_filter': """
            EXPLAIN ANALYZE
            SELECT * FROM workouts 
            WHERE workout_date BETWEEN '2026-01-01' AND '2026-12-31'
            ORDER BY workout_date DESC;
        """,
        'calorie_filter': """
            EXPLAIN ANALYZE
            SELECT * FROM workouts 
            WHERE total_calories BETWEEN 200 AND 600;
        """,
        'user_workouts': """
            EXPLAIN ANALYZE
            SELECT w.*, u.username 
            FROM workouts w
            JOIN users u ON w.user_id = u.user_id
            WHERE u.user_id = 1
            ORDER BY w.workout_date DESC;
        """,
        'category_filter': """
            EXPLAIN ANALYZE
            SELECT * FROM exercises 
            WHERE category = 'cardio'
            ORDER BY exercise_name;
        """
    }
    
    query = queries.get(query_type, queries['date_filter'])
    
    cur.execute(query)
    explain_result = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify({
        'query': query,
        'explain': [dict(row) for row in explain_result]
    })

# ==================== TRANSACTIONS & CONCURRENCY DEMO ====================

@app.route('/transactions-demo')
def transactions_demo():
    """Demonstration of transactions and isolation levels"""
    return render_template('transactions_demo.html')

@app.route('/transfer-workout', methods=['POST'])
def transfer_workout():
    """
    Demonstrate ACID transactions by transferring a workout from one user to another.
    This must be atomic - either both operations succeed or both fail.
    """
    workout_id = request.form.get('workout_id', type=int)
    new_user_id = request.form.get('new_user_id', type=int)
    isolation_level = request.form.get('isolation_level', 'READ COMMITTED')
    
    conn = get_db_connection()
    
    # Set isolation level
    isolation_map = {
        'READ UNCOMMITTED': psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED,
        'READ COMMITTED': psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED,
        'REPEATABLE READ': psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ,
        'SERIALIZABLE': psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
    }
    
    conn.set_isolation_level(isolation_map.get(isolation_level, psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED))
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Start transaction (BEGIN is implicit with psycopg2)
        
        # Step 1: Get current workout info
        cur.execute("SELECT * FROM workouts WHERE workout_id = %s FOR UPDATE", (workout_id,))
        workout = cur.fetchone()
        
        if not workout:
            raise Exception("Workout not found")
        
        old_user_id = workout['user_id']
        
        # Step 2: Update workout to new user
        cur.execute(
            "UPDATE workouts SET user_id = %s WHERE workout_id = %s",
            (new_user_id, workout_id)
        )
        
        # Step 3: Log the transfer (simulate a multi-step transaction)
        # In a real app, you might have an audit log table
        
        # COMMIT the transaction
        conn.commit()
        
        result = {
            'success': True,
            'message': f'Workout {workout_id} transferred from user {old_user_id} to user {new_user_id}',
            'isolation_level': isolation_level,
            'old_user_id': old_user_id,
            'new_user_id': new_user_id
        }
        
    except Exception as e:
        # ROLLBACK on error
        conn.rollback()
        result = {
            'success': False,
            'message': f'Transaction failed: {str(e)}',
            'isolation_level': isolation_level
        }
    
    finally:
        cur.close()
        conn.close()
    
    return jsonify(result)

@app.route('/concurrent-update-demo', methods=['POST'])
def concurrent_update_demo():
    """
    Demonstrate concurrent updates and potential race conditions.
    Shows why transactions and proper isolation levels matter.
    """
    user_id = request.form.get('user_id', type=int)
    weight_change = request.form.get('weight_change', type=float)
    use_transaction = request.form.get('use_transaction', 'true') == 'true'
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if use_transaction:
            # SAFE: Using SELECT FOR UPDATE to lock the row
            cur.execute(
                "SELECT weight_kg FROM users WHERE user_id = %s FOR UPDATE",
                (user_id,)
            )
            user = cur.fetchone()
            
            if user:
                new_weight = float(user['weight_kg']) + weight_change
                cur.execute(
                    "UPDATE users SET weight_kg = %s WHERE user_id = %s",
                    (new_weight, user_id)
                )
                conn.commit()
                
                result = {
                    'success': True,
                    'method': 'WITH Transaction & Row Lock (FOR UPDATE)',
                    'old_weight': float(user['weight_kg']),
                    'new_weight': new_weight,
                    'safe': True
                }
        else:
            # UNSAFE: Read-modify-write without locking (race condition possible)
            cur.execute(
                "SELECT weight_kg FROM users WHERE user_id = %s",
                (user_id,)
            )
            user = cur.fetchone()
            
            if user:
                new_weight = float(user['weight_kg']) + weight_change
                # Simulate delay where another transaction could interfere
                cur.execute(
                    "UPDATE users SET weight_kg = %s WHERE user_id = %s",
                    (new_weight, user_id)
                )
                conn.commit()
                
                result = {
                    'success': True,
                    'method': 'WITHOUT Row Lock (potential race condition)',
                    'old_weight': float(user['weight_kg']),
                    'new_weight': new_weight,
                    'safe': False,
                    'warning': 'This approach is vulnerable to lost updates in concurrent scenarios'
                }
        
    except Exception as e:
        conn.rollback()
        result = {
            'success': False,
            'error': str(e)
        }
    
    finally:
        cur.close()
        conn.close()
    
    return jsonify(result)

# ==================== ORIGINAL CRUD OPERATIONS (WITH SQL INJECTION PROTECTION) ====================

@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        # SQL INJECTION PROTECTION: Using parameterized queries
        username = request.form['username']
        email = request.form['email']
        age = request.form['age']
        weight_kg = request.form['weight_kg']
        height_cm = request.form['height_cm']
        
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # SAFE: Parameters passed as tuple, not concatenated into query string
            cur.execute(
                'INSERT INTO users (username, email, age, weight_kg, height_cm) VALUES (%s, %s, %s, %s, %s)',
                (username, email, age, weight_kg, height_cm)
            )
            conn.commit()
            message = "User added successfully!"
        except Exception as e:
            conn.rollback()
            message = f"Error: {e}"
        finally:
            cur.close()
            conn.close()
        
        return render_template('add_user.html', message=message)
    
    return render_template('add_user.html')

@app.route('/users/update/<int:user_id>', methods=['GET', 'POST'])
def update_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        weight_kg = request.form['weight_kg']
        age = request.form['age']
        
        # TRANSACTION: Update with proper transaction handling
        try:
            cur.execute(
                'UPDATE users SET weight_kg = %s, age = %s WHERE user_id = %s',
                (weight_kg, age, user_id)
            )
            conn.commit()
            message = "User updated successfully!"
        except Exception as e:
            conn.rollback()
            message = f"Error: {e}"
    else:
        message = None
    
    # INDEXED QUERY: This benefits from primary key index
    cur.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    return render_template('update_user.html', user=user, message=message)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # TRANSACTION: Delete with CASCADE (will delete related workouts)
        cur.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('list_users'))

@app.route('/users')
def list_users():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM users ORDER BY user_id')
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('list_users.html', users=users)

@app.route('/workouts/filter', methods=['GET', 'POST'])
def filter_workouts():
    if request.method == 'POST':
        # SQL INJECTION PROTECTION: All inputs parameterized
        min_calories = request.form.get('min_calories', 0)
        max_calories = request.form.get('max_calories', 10000)
        min_duration = request.form.get('min_duration', 0)
        max_duration = request.form.get('max_duration', 500)
        start_date = request.form.get('start_date', '2020-01-01')
        end_date = request.form.get('end_date', '2030-12-31')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # INDEXED QUERY: Benefits from idx_workouts_date and idx_workouts_calories
        cur.execute('''
            SELECT 
                w.workout_id,
                u.username,
                w.workout_date,
                w.duration_minutes,
                w.total_calories,
                w.notes
            FROM workouts w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.total_calories BETWEEN %s AND %s
            AND w.duration_minutes BETWEEN %s AND %s
            AND w.workout_date BETWEEN %s AND %s
            ORDER BY w.workout_date DESC, w.total_calories DESC
        ''', (min_calories, max_calories, min_duration, max_duration, start_date, end_date))
        
        workouts = cur.fetchall()
        cur.close()
        conn.close()
        
        return render_template('workout_report.html', workouts=workouts, 
                             filters={'min_calories': min_calories, 'max_calories': max_calories,
                                    'min_duration': min_duration, 'max_duration': max_duration,
                                    'start_date': start_date, 'end_date': end_date})
    
    return render_template('filter_workouts.html')

@app.route('/workouts/add', methods=['GET', 'POST'])
def add_workout():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # INDEXED QUERY: Benefits from idx_users_username
    cur.execute('SELECT user_id, username, email FROM users ORDER BY username')
    users = cur.fetchall()
    
    # INDEXED QUERY: Benefits from idx_exercises_category
    cur.execute('SELECT exercise_id, exercise_name, category FROM exercises ORDER BY category, exercise_name')
    exercises = cur.fetchall()
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        workout_date = request.form['workout_date']
        duration_minutes = request.form['duration_minutes']
        total_calories = request.form['total_calories']
        notes = request.form['notes']
        selected_exercises = request.form.getlist('exercises')
        
        try:
            # TRANSACTION: Multi-table insert must be atomic
            cur.execute(
                'INSERT INTO workouts (user_id, workout_date, duration_minutes, total_calories, notes) VALUES (%s, %s, %s, %s, %s) RETURNING workout_id',
                (user_id, workout_date, duration_minutes, total_calories, notes)
            )
            workout_id = cur.fetchone()['workout_id']
            
            for exercise_id in selected_exercises:
                cur.execute(
                    'INSERT INTO workout_exercises (workout_id, exercise_id, duration_minutes, calories_burned) VALUES (%s, %s, %s, %s)',
                    (workout_id, exercise_id, 10, 50)
                )
            
            conn.commit()
            message = "Workout added successfully!"
        except Exception as e:
            conn.rollback()
            message = f"Error: {e}"
    else:
        message = None
    
    cur.close()
    conn.close()
    
    return render_template('add_workout.html', users=users, exercises=exercises, message=message)

@app.route('/exercises/add', methods=['GET', 'POST'])
def add_exercise():
    if request.method == 'POST':
        exercise_name = request.form['exercise_name']
        category = request.form['category']
        calories_per_minute = request.form['calories_per_minute']
        description = request.form['description']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute(
                'INSERT INTO exercises (exercise_name, category, calories_per_minute, description) VALUES (%s, %s, %s, %s)',
                (exercise_name, category, calories_per_minute, description)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
        finally:
            cur.close()
            conn.close()
        
        return redirect(url_for('add_workout'))
    
    return render_template('add_exercise.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)