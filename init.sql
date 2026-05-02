-- Users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    age INTEGER,
    weight_kg DECIMAL(5,2),
    height_cm INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exercises table
CREATE TABLE exercises (
    exercise_id SERIAL PRIMARY KEY,
    exercise_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    calories_per_minute DECIMAL(5,2),
    description TEXT
);

-- Workouts table
CREATE TABLE workouts (
    workout_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    workout_date DATE NOT NULL,
    duration_minutes INTEGER,
    total_calories DECIMAL(7,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workout_exercises table
CREATE TABLE workout_exercises (
    workout_exercise_id SERIAL PRIMARY KEY,
    workout_id INTEGER REFERENCES workouts(workout_id) ON DELETE CASCADE,
    exercise_id INTEGER REFERENCES exercises(exercise_id) ON DELETE CASCADE,
    sets INTEGER,
    reps INTEGER,
    duration_minutes INTEGER,
    calories_burned DECIMAL(6,2),
    UNIQUE(workout_id, exercise_id)
);

-- ==================== INDEXES FOR STAGE 3 ====================

-- Index 1: Speed up workout filtering by date range (used in filter_workouts report)
-- Justification: The workout filter report frequently queries workouts within date ranges
CREATE INDEX idx_workouts_date ON workouts(workout_date);

-- Index 2: Speed up workout filtering by calories (used in filter_workouts report)
-- Justification: Users often filter workouts by calorie ranges to track goals
CREATE INDEX idx_workouts_calories ON workouts(total_calories);

-- Index 3: Speed up user lookup by username (used in login/search features)
-- Justification: Username searches are common when viewing user profiles
CREATE INDEX idx_users_username ON users(username);

-- Index 4: Composite index for workout queries by user and date
-- Justification: The user workout history report queries by user_id and orders by date
CREATE INDEX idx_workouts_user_date ON workouts(user_id, workout_date DESC);

-- Index 5: Speed up exercise category filtering (used in add_workout dropdown)
-- Justification: Exercises are often filtered by category in the UI
CREATE INDEX idx_exercises_category ON exercises(category);

-- ==================== SAMPLE DATA ====================

INSERT INTO exercises (exercise_name, category, calories_per_minute, description) VALUES
('Running', 'cardio', 10.0, 'Outdoor or treadmill running'),
('Cycling', 'cardio', 8.0, 'Stationary or outdoor cycling'),
('Swimming', 'cardio', 11.0, 'Lap swimming'),
('Bench Press', 'strength', 5.0, 'Chest exercise with barbell'),
('Squats', 'strength', 6.0, 'Lower body compound exercise'),
('Deadlifts', 'strength', 6.5, 'Full body compound exercise'),
('Yoga', 'flexibility', 3.0, 'Flexibility and balance'),
('Push-ups', 'strength', 4.0, 'Bodyweight chest exercise'),
('Pull-ups', 'strength', 5.5, 'Bodyweight back exercise'),
('Plank', 'core', 3.5, 'Core stability exercise');

INSERT INTO users (username, email, age, weight_kg, height_cm) VALUES
('john_doe', 'john@example.com', 25, 75.5, 180),
('jane_smith', 'jane@example.com', 30, 62.0, 165),
('mike_jones', 'mike@example.com', 28, 85.0, 175);

INSERT INTO workouts (user_id, workout_date, duration_minutes, total_calories, notes) VALUES
(1, '2026-01-20', 60, 450, 'Morning cardio session'),
(1, '2026-01-21', 45, 300, 'Strength training'),
(2, '2026-01-20', 30, 200, 'Quick workout'),
(1, '2026-01-22', 90, 650, 'Long endurance run'),
(2, '2026-01-22', 50, 350, 'Mixed cardio and strength');

INSERT INTO workout_exercises (workout_id, exercise_id, duration_minutes, calories_burned) VALUES
(1, 1, 30, 300),
(1, 7, 30, 150),
(2, 4, 20, 100),
(2, 5, 25, 200),
(3, 3, 30, 330),
(4, 1, 90, 900),
(5, 2, 30, 240),
(5, 4, 20, 100);