from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import datetime
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'secretkey'
db = SQLAlchemy(app)

class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    proteins = db.Column(db.Float, nullable=False)
    fats = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class ConsumedDish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), nullable=False)
    date_consumed = db.Column(db.Date, nullable=False)
    grams = db.Column(db.Float, nullable=False)
    dish = db.relationship('Dish', backref='consumed_dishes')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        proteins = float(request.form['proteins'])
        fats = float(request.form['fats'])
        carbs = float(request.form['carbs'])
        new_dish = Dish(name=name, proteins=proteins, fats=fats, carbs=carbs)
        
        db.session.add(new_dish)
        db.session.commit()
        return redirect('/')
    
    dishes = Dish.query.order_by(Dish.date_added.desc()).all()
    return render_template('index.html', dishes=dishes)


@app.route('/search', methods=['POST'])
def livesearch():
    searchbox = request.form.get("search_keyword")
    if searchbox:
        dishes = Dish.query.filter(Dish.name.contains(searchbox)).all()
    else:
        dishes = Dish.query.order_by(Dish.date_added.desc()).all()
    return render_template('index.html', dishes=dishes)


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    dish = Dish.query.get_or_404(id)
    if request.method == 'POST':
        dish.name = request.form['name']
        dish.proteins = float(request.form['proteins'])
        dish.fats = float(request.form['fats'])
        dish.carbs = float(request.form['carbs'])

        db.session.commit()
        return redirect('/')
    
    return render_template('edit.html', dish=dish)

@app.route('/delete/<int:id>')
def delete(id):
    dish = Dish.query.get_or_404(id)
    
    db.session.delete(dish)
    db.session.commit()
    flash('Dish deleted successfully!', 'success')
    return redirect('/')


@app.route('/plot', methods=['GET'])
def plot_consumed():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date or end_date:
        if not start_date:
            start_date = datetime.datetime.utcnow().date()
        if not end_date:
            end_date = datetime.datetime.utcnow().date()
        consumed_dishes = ConsumedDish.query.filter(
            ConsumedDish.date_consumed >= start_date,
            ConsumedDish.date_consumed <= end_date
        ).order_by(ConsumedDish.date_consumed.desc()).all()
    else:
        consumed_dishes = ConsumedDish.query.order_by(ConsumedDish.date_consumed.desc()).all()

    daily_calories = {}
    for consumed in consumed_dishes:
        date = consumed.date_consumed
        calories = (3 * consumed.dish.proteins + 2 * consumed.dish.fats + 5 * consumed.dish.carbs) * consumed.grams / 100
        if date in daily_calories:
            daily_calories[date] += calories
        else:
            daily_calories[date] = calories
    
    dates = list(daily_calories.keys())
    calories = list(daily_calories.values())

    plt.figure(figsize=(10, 6))
    plt.plot(dates, calories, marker='o')
    plt.xlabel('Date')
    plt.ylabel('Calories')
    plt.title('Calories Consumed Over Time')
    plt.grid()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')

    return render_template('plot.html', plot_url=plot_url)


@app.route('/consume', methods=['GET', 'POST'])
def consume():
    dishes = Dish.query.all()
    
    if request.method == 'POST':
        dish_id = request.form['dish_id']
        grams = float(request.form['grams'])
        date_consumed = request.form['date']
        
        consumed_dish = ConsumedDish(dish_id=dish_id, grams=grams, date_consumed=datetime.datetime.strptime(date_consumed, '%Y-%m-%d').date())
        
        db.session.add(consumed_dish)
        db.session.commit()
        flash('Consumed dish added successfully!', 'success')
        return redirect('/consume')

    return render_template('consume.html', dishes=dishes)


@app.route('/consumed')
def consumed():
    consumed_dishes = ConsumedDish.query.order_by(ConsumedDish.date_consumed.desc()).all()
    return render_template('consumed.html', consumed_dishes=consumed_dishes)


@app.route('/consumed/delete/<int:id>', methods=['POST'])
def delete_consumed(id):
    consumed_dish = ConsumedDish.query.get_or_404(id)

    db.session.delete(consumed_dish)
    db.session.commit()
    flash(f'Record for {consumed_dish.dish.name} on {consumed_dish.date_consumed} deleted successfully!', 'success')
    
    return redirect('/consumed')


@app.route('/consumed/edit/<int:id>', methods=['GET', 'POST'])
def edit_consumed(id):
    consumed_dish = ConsumedDish.query.get_or_404(id)
    dishes = Dish.query.all()

    if request.method == 'POST':
        consumed_dish.dish_id = request.form['dish_id']
        consumed_dish.grams = float(request.form['grams'])
        consumed_dish.date_consumed = datetime.datetime.strptime(request.form['date'], '%Y-%m-%d').date()

        db.session.commit()
        return redirect('/consumed')

    return render_template('edit_consumed.html', consumed_dish=consumed_dish, dishes=dishes)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5001, debug=True)
