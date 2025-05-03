# app.py
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import date, timedelta, datetime

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class Day(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    weight = db.Column(db.Float, nullable=True)
    goal_calories = db.Column(db.Integer, default=1800)
    
class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey('day.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, nullable=False)

class Candy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey('day.id'), nullable=False)
    count = db.Column(db.Integer, default=0)

# --- Helpers ---
def get_or_create_day(query_date):
    day = Day.query.filter_by(date=query_date).first()
    if not day:
        day = Day(date=query_date)
        db.session.add(day)
        db.session.commit()
    return day

# --- Routes ---
@app.route('/')
def index():
    query = request.args.get('date')
    current_date = date.fromisoformat(query) if query else date.today()
    day = get_or_create_day(current_date)
    candies = Candy.query.filter_by(day_id=day.id).first()
    foods = Food.query.filter_by(day_id=day.id).all()
    total_food_cals = sum(f.calories for f in foods)
    candy_cals = (candies.count * 22.5) if candies else 0
    total_cals = total_food_cals + candy_cals
    return render_template(
        'index.html',
        day=day,
        candies=candies,
        foods=foods,
        total_cals=total_cals,
        timedelta=timedelta
    )

@app.route('/add_weight', methods=['POST'])
def add_weight():
    weight = float(request.form['weight'])
    day = get_or_create_day(date.today())
    day.weight = weight
    db.session.commit()
    return redirect('/')

@app.route('/add_candy', methods=['POST'])
def add_candy():
    day = get_or_create_day(date.today())
    candies = Candy.query.filter_by(day_id=day.id).first()
    if not candies:
        candies = Candy(day_id=day.id, count=1)
        db.session.add(candies)
    else:
        candies.count += 1
    db.session.commit()
    return redirect('/')

@app.route('/remove_candy', methods=['POST'])
def remove_candy():
    day = get_or_create_day(date.today())
    candies = Candy.query.filter_by(day_id=day.id).first()
    if candies and candies.count > 0:
        candies.count -= 1
        db.session.commit()
    return redirect('/')

@app.route('/add_food', methods=['POST'])
def add_food():
    name = request.form['name']
    calories = int(request.form['calories'])
    day = get_or_create_day(date.today())
    food = Food(day_id=day.id, name=name, calories=calories)
    db.session.add(food)
    db.session.commit()
    return redirect('/')

@app.route('/edit_goal', methods=['POST'])
def edit_goal():
    goal = int(request.form['goal'])
    day = get_or_create_day(date.today())
    day.goal_calories = goal
    db.session.commit()
    return redirect('/')

@app.route('/delete_food/<int:food_id>', methods=['POST'])
def delete_food(food_id):
    food = Food.query.get_or_404(food_id)
    day = Day.query.get(food.day_id)
    db.session.delete(food)
    db.session.commit()
    return redirect(f"/?date={day.date.isoformat()}")

@app.route('/reset_day', methods=['POST'])
def reset_day():
    day = get_or_create_day(date.today())
    # Delete associated food entries
    Food.query.filter_by(day_id=day.id).delete()
    # Delete candy record if exists
    Candy.query.filter_by(day_id=day.id).delete()
    # Reset weight and keep goal intact
    day.weight = None
    db.session.commit()
    return redirect('/')

# --- API ---
@app.route('/api/day/<string:query_date>')
def api_day(query_date):
    d = date.fromisoformat(query_date)
    day = get_or_create_day(d)
    foods = Food.query.filter_by(day_id=day.id).all()
    candies = Candy.query.filter_by(day_id=day.id).first()
    total_food_cals = sum(f.calories for f in foods)
    candy_cals = (candies.count * 22.5) if candies else 0
    return jsonify({
        'date': query_date,
        'weight': day.weight,
        'goal_calories': day.goal_calories,
        'total_calories': total_food_cals + candy_cals,
        'candies': candies.count if candies else 0,
        'foods': [dict(name=f.name, calories=f.calories) for f in foods]
    })

@app.route('/api/weight-trend')
def api_weight_trend():
    trend = Day.query.filter(Day.weight != None).order_by(Day.date).all()
    return jsonify([{ 'date': d.date.isoformat(), 'weight': d.weight } for d in trend])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
