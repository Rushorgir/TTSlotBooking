from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ttslotbooker@gmail.com'  # Replace with your actual Gmail
app.config['MAIL_PASSWORD'] = 'ghjr pehu knry frpd'     # Replace with your Gmail app password  
app.config['MAIL_DEFAULT_SENDER'] = 'ttslotbooker@gmail.com'  # Replace with your actual Gmail

mail = Mail(app)

# Admin email addresses
ADMIN_EMAILS = ['nangia.ekansh12@gmail.com', 'nayyarrushaan@gmail.com']

# JSON file configuration
JSON_FILE = 'bookings.json'


def load_bookings():
    """Load bookings from JSON file"""
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as f:
            return json.load(f)
    return []


def save_bookings(bookings):
    """Save bookings to JSON file"""
    with open(JSON_FILE, 'w') as f:
        json.dump(bookings, f, indent=2)


def load_pending_bookings():
    """Load pending bookings from JSON file"""
    pending_file = 'pending_bookings.json'
    if os.path.exists(pending_file):
        with open(pending_file, 'r') as f:
            return json.load(f)
    return []


def save_pending_bookings(pending_bookings):
    """Save pending bookings to JSON file"""
    pending_file = 'pending_bookings.json'
    with open(pending_file, 'w') as f:
        json.dump(pending_bookings, f, indent=2)


def send_booking_notification(user_name, user_phone, user_room, slots, total_amount):
    """Send email notification to admins about new booking request"""
    try:
        # Format slot information
        slot_details = []
        for slot in slots:
            slot_details.append(f"- {slot['date']} at {slot['time_slot']}")
        
        slots_text = '\n'.join(slot_details)
        
        # Create email content
        subject = f"New Booking Request - {user_name}"
        body = f"""
A new booking request has been submitted and requires admin approval:

Customer Details:
- Name: {user_name}
- Phone: {user_phone}
- Room: {user_room}

Booking Details:
{slots_text}

Total Amount: ₹{total_amount}

Please log in to the admin panel to approve or reject this request.

Admin Panel: {request.url_root}admin
        """
        
        # Send email to all admin addresses
        msg = Message(subject=subject, recipients=ADMIN_EMAILS, body=body)
        mail.send(msg)
        
        return True
    except Exception as e:
        print(f"Failed to send email notification: {e}")
        return False


def init_json_db():
    """Initialize the JSON database if it doesn't exist"""
    if not os.path.exists(JSON_FILE):
        # Create empty bookings file
        save_bookings([])

    # Insert default time slots for today if they don't exist
    create_slots_for_date(datetime.now().strftime('%Y-%m-%d'))


def create_slots_for_date(date_str):
    """Create time slots for a specific date if they don't exist"""
    bookings = load_bookings()

    time_slots = [
        "8:00 AM - 9:00 AM", "9:00 AM - 10:00 AM", "10:00 AM - 11:00 AM",
        "11:00 AM - 12:00 PM", "12:00 PM - 1:00 PM", "1:00 PM - 2:00 PM",
        "2:00 PM - 3:00 PM", "3:00 PM - 4:00 PM", "4:00 PM - 5:00 PM",
        "5:00 PM - 6:00 PM", "6:00 PM - 7:00 PM", "7:00 PM - 8:00 PM"
    ]

    # Get the next available ID
    next_id = 1
    if bookings:
        next_id = max([booking.get('id', 0) for booking in bookings]) + 1

    # Check if slots for the date already exist
    existing_slots = [b for b in bookings if b['date'] == date_str]
    existing_time_slots = [b['time_slot'] for b in existing_slots]

    # Add missing time slots
    for time_slot in time_slots:
        if time_slot not in existing_time_slots:
            new_booking = {
                'id': next_id,
                'date': date_str,
                'time_slot': time_slot,
                'net_number': 1,
                'is_booked': False,
                'is_disabled': False,
                'booked_by': None,
                'booking_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            bookings.append(new_booking)
            next_id += 1

    save_bookings(bookings)


@app.route('/')
def home():  # put application's code here
    return render_template('home_page.html')


@app.route('/booking')
def booking_default():
    date = datetime.now().strftime('%Y-%m-%d')
    return booking_with_date(date)

@app.route('/booking/<date>')
def booking_with_date(date):
    # Validate date format to avoid conflicts with admin routes
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return redirect(url_for('booking_default'))

    # Ensure slots exist for the requested date
    create_slots_for_date(date)

    # Load bookings from JSON
    all_bookings = load_bookings()
    slots = [
        b for b in all_bookings if b['date'] == date and b['net_number'] == 1
    ]

    # Sort by time slot
    slots.sort(key=lambda x: x['time_slot'])

    # Convert date for display
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%B %d, %Y')

    # Calculate previous and next dates
    prev_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

    return render_template('booking.html',
                           slots=slots,
                           current_date=date,
                           formatted_date=formatted_date,
                           prev_date=prev_date,
                           next_date=next_date)


@app.route('/toggle_booking', methods=['POST'])
def toggle_booking():
    data = request.get_json()
    
    # Handle new booking format with user details and multiple slots
    if 'selected_slots' in data:
        user_name = data.get('user_name')
        user_phone = data.get('user_phone')
        user_room = data.get('user_room')
        selected_slot_ids = data.get('selected_slots', [])
        
        # Load all bookings from JSON
        bookings = load_bookings()
        pending_bookings = load_pending_bookings()
        
        # Get next pending booking ID
        next_pending_id = 1
        if pending_bookings:
            next_pending_id = max([pb.get('id', 0) for pb in pending_bookings]) + 1
        
        # Create pending booking request
        pending_slots = []
        for booking in bookings:
            if (booking['id'] in selected_slot_ids and 
                not booking['is_booked'] and 
                not booking.get('is_disabled', False)):
                pending_slots.append({
                    'slot_id': booking['id'],
                    'date': booking['date'],
                    'time_slot': booking['time_slot'],
                    'net_number': booking['net_number']
                })
        
        if pending_slots:
            # Create pending booking entry
            pending_booking = {
                'id': next_pending_id,
                'user_name': user_name,
                'user_phone': user_phone,
                'user_room': user_room,
                'slots': pending_slots,
                'total_amount': data.get('total_amount', len(pending_slots) * 40),
                'payment_method': data.get('payment_method', 'upi'),
                'request_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'pending'
            }
            
            pending_bookings.append(pending_booking)
            save_pending_bookings(pending_bookings)
            
            # Send email notification to admins
            email_sent = send_booking_notification(
                user_name, user_phone, user_room, pending_slots, pending_booking['total_amount']
            )
            
            message = f'Payment request sent! Your booking is pending admin approval.'
            if not email_sent:
                message += ' (Note: Email notification failed to send)'
            
            return jsonify({
                'success': True,
                'message': message,
                'pending': True
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Selected slots are no longer available'
            })
    
    # Handle legacy single slot toggle format
    else:
        date = data.get('date')
        time_slot = data.get('time_slot')
        net_number = data.get('net_number', 1)

        # Load all bookings from JSON
        bookings = load_bookings()

        # Find the booking to toggle
        found = False
        for booking in bookings:
            if (booking['date'] == date and booking['time_slot'] == time_slot
                    and booking['net_number'] == net_number):
                # Toggle booking status
                new_status = not booking['is_booked']
                booking['is_booked'] = new_status
                booking['booked_by'] = "User" if new_status else None
                booking['booking_time'] = datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S')
                found = True
                break

        if found:
            # Save updated bookings back to JSON
            save_bookings(bookings)

            return jsonify({
                'success': True,
                'is_booked': new_status,
                'message': 'Booking toggled successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Slot not found'}), 404


@app.route('/admin')
def admin():
    """Admin page to view all bookings"""
    return render_template('admin_login.html')


@app.route('/admin', methods=['POST'])
def admin_login():
    """Handle admin login"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'ekanshrushaan' and password == 'rushaanekansh':
        # Load all bookings from JSON
        all_bookings = load_bookings()
        pending_bookings = load_pending_bookings()

        # Filter only booked slots
        booked_slots = [b for b in all_bookings if b['is_booked']]

        # Sort by date and time
        booked_slots.sort(key=lambda x: (x['date'], x['time_slot']))

        # Filter pending requests
        pending_requests = [pb for pb in pending_bookings if pb['status'] == 'pending']

        return render_template('admin.html', bookings=booked_slots, pending_requests=pending_requests)
    else:
        return render_template('admin_login.html', error="Invalid credentials")


@app.route('/clear_all_bookings', methods=['POST'])
def clear_all_bookings():
    """Clear all bookings in the system"""
    # Load all bookings from JSON
    all_bookings = load_bookings()

    # Mark all slots as not booked
    for booking in all_bookings:
        booking['is_booked'] = False
        booking['booked_by'] = None

    # Save the updated bookings
    save_bookings(all_bookings)

    return jsonify({
        'success': True,
        'message': 'All bookings have been cleared successfully'
    })


@app.route('/toggle_disabled_slot', methods=['POST'])
def toggle_disabled_slot():
    """Toggle disabled status of a slot"""
    data = request.get_json()
    slot_id = data.get('slot_id')
    
    # Load all bookings from JSON
    bookings = load_bookings()
    
    # Find the slot and toggle disabled status
    for booking in bookings:
        if booking['id'] == slot_id:
            booking['is_disabled'] = not booking.get('is_disabled', False)
            # If disabling, also clear any existing booking
            if booking['is_disabled']:
                booking['is_booked'] = False
                booking['booked_by'] = None
            break
    
    # Save updated bookings
    save_bookings(bookings)
    
    return jsonify({
        'success': True,
        'message': 'Slot status updated successfully'
    })


@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    """Confirm a pending booking"""
    data = request.get_json()
    pending_id = data.get('pending_id')
    
    # Load pending bookings and regular bookings
    pending_bookings = load_pending_bookings()
    bookings = load_bookings()
    
    # Find the pending booking
    pending_booking = None
    for pb in pending_bookings:
        if pb['id'] == pending_id and pb['status'] == 'pending':
            pending_booking = pb
            break
    
    if not pending_booking:
        return jsonify({'success': False, 'message': 'Pending booking not found'})
    
    # Check if slots are still available
    unavailable_slots = []
    for slot_info in pending_booking['slots']:
        for booking in bookings:
            if (booking['id'] == slot_info['slot_id'] and 
                (booking['is_booked'] or booking.get('is_disabled', False))):
                unavailable_slots.append(slot_info['time_slot'])
                break
    
    if unavailable_slots:
        return jsonify({
            'success': False, 
            'message': f'Some slots are no longer available: {", ".join(unavailable_slots)}'
        })
    
    # Confirm the booking
    for slot_info in pending_booking['slots']:
        for booking in bookings:
            if booking['id'] == slot_info['slot_id']:
                booking['is_booked'] = True
                booking['booked_by'] = f"{pending_booking['user_name']} - Room {pending_booking['user_room']} ({pending_booking['user_phone']})"
                booking['booking_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break
    
    # Update pending booking status
    pending_booking['status'] = 'confirmed'
    pending_booking['confirmed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Save changes
    save_bookings(bookings)
    save_pending_bookings(pending_bookings)
    
    return jsonify({
        'success': True,
        'message': f'Booking confirmed for {pending_booking["user_name"]}'
    })


@app.route('/reject_booking', methods=['POST'])
def reject_booking():
    """Reject a pending booking"""
    data = request.get_json()
    pending_id = data.get('pending_id')
    
    # Load pending bookings
    pending_bookings = load_pending_bookings()
    
    # Find and update the pending booking
    for pb in pending_bookings:
        if pb['id'] == pending_id and pb['status'] == 'pending':
            pb['status'] = 'rejected'
            pb['rejected_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            break
    else:
        return jsonify({'success': False, 'message': 'Pending booking not found'})
    
    # Save changes
    save_pending_bookings(pending_bookings)
    
    return jsonify({
        'success': True,
        'message': 'Booking request rejected'
    })


@app.route('/api/bookings/<date>')
def get_bookings_api(date):
    """API endpoint to get bookings for a specific date"""
    # Load all bookings from JSON
    all_bookings = load_bookings()

    # Filter bookings for the requested date
    slots = [
        b for b in all_bookings if b['date'] == date and b['net_number'] == 1
    ]

    # Sort by time slot
    slots.sort(key=lambda x: x['time_slot'])

    return jsonify(slots)


if __name__ == '__main__':
    # Initialize JSON database on startup
    init_json_db()
    app.run(debug=True)
