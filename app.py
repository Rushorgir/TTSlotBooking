from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def home():  # put application's code here
    return render_template('home_page.html')

@app.route('/booking')
def bookings():
    # This tells Flask to find and return bookings.html from the 'templates' folder
    return render_template('booking.html')


if __name__ == '__main__':
    app.run()
