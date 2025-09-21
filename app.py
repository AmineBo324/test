from flask import Flask, jsonify, request
from flask_cors import CORS
import os, json, random, hashlib

app = Flask(__name__)
CORS(app)

# Load questions from JSON file with multilingual support
with open("questions.json", "r", encoding='utf-8') as f:
    questions = json.load(f)

# Load flags for mini-game with multilingual support
with open("flags.json", "r", encoding='utf-8') as f:
    flags = json.load(f)

# In-memory storage for user progress and used questions (in production, use a database)
user_progress = {}
used_questions = {}  # Store used questions per user/session
used_flags = {}      # Store used flag questions per user/session

def get_question_id(question):
    """Generate a unique ID for a question based on its content"""
    content = question.get('question', '') + str(sorted(question.get('options', [])))
    return hashlib.md5(content.encode()).hexdigest()

def get_flag_id(flag_question):
    """Generate a unique ID for a flag question based on its image"""
    return hashlib.md5(flag_question.get('image', '').encode()).hexdigest()

def get_user_session_id():
    """Get user session ID - in production, use proper session management"""
    # For now, use IP address as session ID (not recommended for production)
    return request.remote_addr or 'default_session'

@app.route('/categories', methods=['GET'])
def get_categories():
    language = request.args.get('language', 'en')
    if language in questions:
        return jsonify(list(questions[language].keys()))
    return jsonify(list(questions['en'].keys()))

@app.route('/difficulties', methods=['GET'])
def get_difficulties():
    return jsonify(["easy", "medium", "hard"])

# Get user progress for a category
@app.route('/progress/<category>', methods=['GET'])
def get_progress(category):
    if category not in user_progress:
        user_progress[category] = {
            'current_level': 1,
            'unlocked_levels': [1],
            'completed_levels': []
        }
    return jsonify(user_progress[category])

# Update user progress
@app.route('/progress/<category>', methods=['POST'])
def update_progress(category):
    data = request.get_json()
    level = data.get('level')
    completed = data.get('completed', False)
    
    if category not in user_progress:
        user_progress[category] = {
            'current_level': 1,
            'unlocked_levels': [1],
            'completed_levels': []
        }
    
    progress = user_progress[category]
    
    if completed and level not in progress['completed_levels']:
        progress['completed_levels'].append(level)
        
        # Unlock next level if it exists
        next_level = level + 1
        total_levels = get_total_levels(category)
        
        if next_level <= total_levels and next_level not in progress['unlocked_levels']:
            progress['unlocked_levels'].append(next_level)
            progress['current_level'] = next_level
    
    return jsonify(progress)

def get_difficulty_for_level(level):
    """Determine difficulty based on level number"""
    if level <= 3:
        return "easy"
    elif level <= 7:
        return "medium"
    else:
        return "hard"

def get_total_levels(category, language='en'):
    """Calculate total number of levels based on available questions"""
    if language not in questions or category not in questions[language]:
        if 'en' in questions and category in questions['en']:
            language = 'en'
        else:
            return 0
    
    # Count questions in each difficulty
    easy_count = len(questions[language][category].get('easy', []))
    medium_count = len(questions[language][category].get('medium', []))
    hard_count = len(questions[language][category].get('hard', []))
    
    # Calculate levels based on progressive difficulty
    # Levels 1-3: easy (need 15 questions minimum)
    # Levels 4-7: medium (need 20 questions minimum) 
    # Levels 8+: hard (remaining questions)
    
    easy_levels = min(3, easy_count // 5) if easy_count >= 5 else 0
    medium_levels = min(4, medium_count // 5) if medium_count >= 5 else 0
    hard_levels = hard_count // 5 if hard_count >= 5 else 0
    
    total_levels = easy_levels + medium_levels + hard_levels
    return max(1, total_levels)

@app.route('/levels/<category>', methods=['GET'])
def get_levels(category):
    language = request.args.get('language', 'en')
    total_levels = get_total_levels(category, language)
    levels = []
    
    for i in range(1, total_levels + 1):
        difficulty = get_difficulty_for_level(i)
        levels.append({
            'level': i,
            'name': f'Level {i}',
            'difficulty': difficulty,
            'questions_count': 5,
            'has_mini_game': True
        })
    
    return jsonify({
        'total_levels': total_levels,
        'levels': levels
    })

# Get difficulty information for a specific level
@app.route('/level-difficulty/<int:level>', methods=['GET'])
def get_level_difficulty(level):
    difficulty = get_difficulty_for_level(level)
    return jsonify({
        'level': level,
        'difficulty': difficulty
    })

@app.route('/questions', methods=['GET'])
def get_questions():
    category = request.args.get('category')
    level = request.args.get('level', type=int, default=1)
    language = request.args.get('language', 'en')
    
    # Get session ID
    session_id = get_user_session_id()
    
    # Initialize used questions for this session if not exists
    if session_id not in used_questions:
        used_questions[session_id] = set()
    
    # Check if language exists, fallback to English
    if language not in questions:
        language = 'en'
    
    if category not in questions[language]:
        return jsonify([])
    
    # Determine difficulty based on level
    difficulty = get_difficulty_for_level(level)
    
    # Get questions for the determined difficulty
    if difficulty not in questions[language][category]:
        return jsonify([])
    
    available_questions_pool = questions[language][category][difficulty]
    
    # Filter out already used questions
    session_used = used_questions[session_id]
    available_questions = []
    
    for question in available_questions_pool:
        question_id = get_question_id(question)
        if question_id not in session_used:
            available_questions.append(question)
    
    # If we don't have enough unused questions in this difficulty, 
    # try to get some from other difficulties as fallback
    if len(available_questions) < 5:
        print(f"Warning: Only {len(available_questions)} unused {difficulty} questions available for {category} level {level}")
        
        # Try to add questions from same or adjacent difficulty levels
        fallback_difficulties = []
        if difficulty == "easy":
            fallback_difficulties = ["easy", "medium"]
        elif difficulty == "medium":
            fallback_difficulties = ["medium", "easy", "hard"]
        else:  # hard
            fallback_difficulties = ["hard", "medium"]
        
        for fallback_difficulty in fallback_difficulties:
            if len(available_questions) >= 5:
                break
            if fallback_difficulty in questions[language][category]:
                for question in questions[language][category][fallback_difficulty]:
                    if len(available_questions) >= 5:
                        break
                    question_id = get_question_id(question)
                    if question_id not in session_used and question not in available_questions:
                        available_questions.append(question)
    
    # If still not enough, allow some reused questions
    if len(available_questions) < 5:
        for question in available_questions_pool:
            if len(available_questions) >= 5:
                break
            question_id = get_question_id(question)
            if question_id in session_used and question not in available_questions:
                available_questions.append(question)
    
    # Select questions for this level
    questions_per_level = min(5, len(available_questions))
    if available_questions:
        selected_questions = random.sample(available_questions, questions_per_level)
    else:
        selected_questions = []
    
    # Mark selected questions as used
    for question in selected_questions:
        question_id = get_question_id(question)
        used_questions[session_id].add(question_id)
    
    return jsonify(selected_questions)

# Reset used questions (optional endpoint for testing)
@app.route('/reset-used-questions', methods=['POST'])
def reset_used_questions():
    session_id = get_user_session_id()
    if session_id in used_questions:
        used_questions[session_id] = set()
    if session_id in used_flags:
        used_flags[session_id] = set()
    return jsonify({"message": "Used questions reset successfully"})

# ---------- Helpers ----------

@app.route('/helpers/fiftyfifty', methods=['POST'])
def fifty_fifty():
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    question = data['question']
    options = question.get('options', [])
    correct = question.get('answer')

    if not options or correct is None:
        return jsonify({"error": "Invalid question format"}), 400

    if correct not in options:
        return jsonify({"error": "Correct answer not in options"}), 400

    wrong_options = [o for o in options if o != correct]

    if len(wrong_options) == 0:
        return jsonify({"question": question.get("question"), "options": [correct], "answer": correct})

    chosen_wrong = random.choice(wrong_options)
    response_options = [correct, chosen_wrong]
    random.shuffle(response_options)

    return jsonify({
        "question": question.get("question"),
        "options": response_options,
        "answer": correct
    })

@app.route('/helpers/ask_audience', methods=['POST'])
def ask_audience():
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    question = data['question']
    options = question.get("options", [])
    correct = question.get("answer")

    if not options or correct not in options:
        return jsonify({"error": "Invalid question format"}), 400

    # Give a random "audience vote" distribution (correct answer usually highest)
    poll = {}
    base = random.randint(50, 80)  # correct gets between 50-80%
    remaining = 100 - base

    poll[correct] = base
    wrongs = [opt for opt in options if opt != correct]
    if wrongs:
        share = [random.randint(0, remaining) for _ in wrongs]
        total = sum(share)
        for i, opt in enumerate(wrongs):
            poll[opt] = int(remaining * (share[i] / total)) if total > 0 else 0

    return jsonify({
        "question": question.get("question"),
        "poll": poll,
        "answer": correct
    })

# Mini-game route with no-repeat system
@app.route('/mini-game/flag', methods=['GET'])
def get_flag_question():
    language = request.args.get('language', 'en')
    session_id = get_user_session_id()
    
    # Initialize used flags for this session if not exists
    if session_id not in used_flags:
        used_flags[session_id] = set()
    
    # Check if language exists in flags, fallback to English
    if language not in flags:
        language = 'en'
    
    # Filter out already used flag questions
    session_used_flags = used_flags[session_id]
    available_flags = []
    
    for flag_question in flags[language]:
        flag_id = get_flag_id(flag_question)
        if flag_id not in session_used_flags:
            available_flags.append(flag_question)
    
    # If all flags have been used, reset the used flags for this session
    if not available_flags:
        print("All flag questions used, resetting...")
        used_flags[session_id] = set()
        available_flags = flags[language].copy()
    
    # Select a random flag question
    selected_flag = random.choice(available_flags)
    
    # Mark this flag as used
    flag_id = get_flag_id(selected_flag)
    used_flags[session_id].add(flag_id)
    
    # Shuffle options before sending
    options = selected_flag["options"].copy()
    random.shuffle(options)
    
    return jsonify({
        "image": selected_flag["image"],
        "options": options,
        "answer": selected_flag["answer"]
    })

# Get statistics about used questions (optional, for debugging)
@app.route('/stats', methods=['GET'])
def get_stats():
    session_id = get_user_session_id()
    return jsonify({
        "session_id": session_id,
        "used_questions_count": len(used_questions.get(session_id, set())),
        "used_flags_count": len(used_flags.get(session_id, set())),
        "total_sessions": len(used_questions)
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)