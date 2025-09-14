from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Quiz questions organized by categories
questions = {
    "Geography": [
        {"question": "What is the capital of France?", "options": ["Paris", "London", "Berlin", "Madrid"], "answer": "Paris"},
        {"question": "Which continent is Egypt in?", "options": ["Asia", "Africa", "Europe", "Australia"], "answer": "Africa"},
        {"question": "Which country has the most population?", "options": ["India", "USA", "China", "Russia"], "answer": "China"}
    ],
    "Science": [
        {"question": "What planet is known as the Red Planet?", "options": ["Earth", "Mars", "Jupiter", "Venus"], "answer": "Mars"},
        {"question": "What is H2O?", "options": ["Oxygen", "Water", "Hydrogen", "Helium"], "answer": "Water"},
        {"question": "What gas do plants absorb?", "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"], "answer": "Carbon Dioxide"}
    ],
    "Sport": [
        {"question": "How many players in a football team?", "options": ["9", "10", "11", "12"], "answer": "11"},
        {"question": "Which country won the 2018 FIFA World Cup?", "options": ["France", "Croatia", "Brazil", "Germany"], "answer": "France"},
        {"question": "In which sport is Wimbledon played?", "options": ["Tennis", "Golf", "Football", "Basketball"], "answer": "Tennis"}
    ],
    "History": [
        {"question": "Who discovered America?", "options": ["Columbus", "Vespucci", "Magellan", "Cook"], "answer": "Columbus"},
        {"question": "When did World War II end?", "options": ["1945", "1939", "1918", "1950"], "answer": "1945"},
        {"question": "Who was the first President of the USA?", "options": ["Lincoln", "Washington", "Jefferson", "Adams"], "answer": "Washington"}
    ]
}

@app.route('/categories', methods=['GET'])
def get_categories():
    return jsonify(list(questions.keys()))

@app.route('/questions', methods=['GET'])
def get_questions():
    category = request.args.get('category')
    if category in questions:
        return jsonify(questions[category])
    else:
        return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000)) 
    app.run(debug=True, host='0.0.0.0', port=port)
