from flask import Flask, render_template, request, redirect, url_for, flash
from database.mongo_db import mongo
import random
import string
import qrcode
from flask import send_file
from datetime import datetime, timezone
import os
import io
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_login import login_user, logout_user, login_required, current_user
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4  # Import A4 size

# from flask_dance.contrib.google import make_google_blueprint, google
# from flask_dance.contrib.microsoft import make_microsoft_blueprint, microsoft


app = Flask(__name__)
app.secret_key = 'you are my sonio'
app.config["MONGO_URI"] = "mongodb+srv://surendraphulvasi:Manu7752@cluster0.vlii4ff.mongodb.net/sample_management?retryWrites=true&w=majority&appName=Cluster0"
mongo.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect here if user not logged in

# OAuth setup
# google_bp = make_google_blueprint(client_id='your_google_client_id', client_secret='your_google_client_secret', redirect_to='google_login')
# app.register_blueprint(google_bp, url_prefix='/google_login')

# microsoft_bp = make_microsoft_blueprint(client_id='your_microsoft_client_id', client_secret='your_microsoft_client_secret', redirect_to='microsoft_login')
# app.register_blueprint(microsoft_bp, url_prefix='/microsoft_login')

class User(UserMixin):
    def __init__(self, email, first_name, last_name, role):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role

    def get_id(self):
        return self.email  # or return another unique identifier, like user_id


def create_user(first_name, last_name, email, password, mobile_no, employee_id, department, role, created_by):
    user = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'password': password,
        'mobile_no': mobile_no,
        'employee_id': employee_id,
        'department': department,
        'role': role,
        'created_by': created_by,
        'created_at': datetime.utcnow(),
        'updated_by': None,
        'updated_on': None,
        'profile_image': None  # You can add a default image path if you want
    }
    mongo.db.users.insert_one(user)
    mongo.db.users.create_index('email', unique=True)
    
def update_user(user_id, updated_by):
    mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {
            '$set': {
                'updated_by': updated_by,
                'updated_on': datetime.utcnow()
            }
        }
    )
    
@login_manager.user_loader
def load_user(email):
    user_data = mongo.db.users.find_one({'email': email})
    if user_data:
        return User(
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            role=user_data['role']
        )
    return None

# Define a custom filter to convert ObjectId to string
@app.template_filter('oid_to_string')
def oid_to_string(value):
    if isinstance(value, ObjectId):
        return str(value)
    return value

def generate_sample_id(length=10):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        mobile_no = request.form['mobile_no']
        employee_id = request.form['employee_id']
        department = request.form['department']
        role = request.form['role']
        created_by = email  # Assuming the creator is the user being registered

        # Check if the email is unique
        if mongo.db.users.find_one({'email': email}):
            flash("Email already exists. Please choose a different one.", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        create_user(first_name, last_name, email, hashed_password, mobile_no, employee_id, department, role, created_by)
        flash("Registration successful! You can log in now.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_data = mongo.db.users.find_one({'email': email})

        if user_data and check_password_hash(user_data['password'], password):
            user = User(
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=user_data['role']
            )
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('login.html')


@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Fetch CPP and CCR analysis data for Truck samples
    truck_cpp_analysis = list(mongo.db.truck_samples.find({"analysis_cpp": {"$exists": True}}))
    truck_ccr_analysis = list(mongo.db.truck_samples.find({"analysis_ccr": {"$exists": True}}))

    # Fetch CPP and CCR analysis data for Rake samples
    rake_cpp_analysis = list(mongo.db.rake_samples.find({"analysis_cpp": {"$exists": True}}))
    rake_ccr_analysis = list(mongo.db.rake_samples.find({"analysis_ccr": {"$exists": True}}))

    return render_template('dashboard.html',
                           truck_cpp_analysis=truck_cpp_analysis,
                           truck_ccr_analysis=truck_ccr_analysis,
                           rake_cpp_analysis=rake_cpp_analysis,
                           rake_ccr_analysis=rake_ccr_analysis)




def create_qr_with_label(sample_id, file_path):
    # Generate the QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(sample_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Add sample_id text to the image
    draw = ImageDraw.Draw(img)

    # You might need to specify a font and size
    # Default font
    font = ImageFont.load_default()
    
    # Positioning the text
    text_position = (10, img.size[1] - 30)  # Adjust as needed
    draw.text(text_position, sample_id, fill="black", font=font)

    # Save the image
    img.save(file_path)

@app.route('/add_truck_sample', methods=['GET', 'POST'])
@login_required
def add_truck_sample():
    if request.method == 'POST':
        sample_id = generate_sample_id()
        date_time = request.form.get('date_time')
        transporter_name = request.form.get('transporter_name')
        supplier = request.form.get('supplier')
        quantity = request.form.get('quantity')

        mongo.db.truck_samples.insert_one({
            'sample_id': sample_id,
            'date_time': date_time,
            'transporter_name': transporter_name,
            'supplier': supplier,
            'quantity': quantity
        })

        create_qr_with_label(sample_id, f'static/qrcodes/{sample_id}.png')

        return redirect(url_for('dashboard'))

    return render_template('add_truck_sample.html')

@app.route('/add_rake_sample', methods=['GET', 'POST'])
@login_required
def add_rake_sample():
    if request.method == 'POST':
        sample_id = generate_sample_id()
        date_time = request.form.get('date_time')
        rr_no = request.form.get('rr_no')
        supplier = request.form.get('supplier')
        quantity = request.form.get('quantity')

        mongo.db.rake_samples.insert_one({
            'sample_id': sample_id,
            'date_time': date_time,
            'rr_no': rr_no,
            'supplier': supplier,
            'quantity': quantity
        })

        create_qr_with_label(sample_id, f'static/qrcodes/{sample_id}.png')

        return redirect(url_for('dashboard'))

    return render_template('add_rake_sample.html')

@app.route('/view_truck_samples')
@login_required
def view_truck_samples():
    samples = list(mongo.db.truck_samples.find())
    return render_template('view_truck_samples.html', samples=samples)

@app.route('/view_rake_samples')
@login_required
def view_rake_samples():
    # Fetching Rake samples from the database
    samples = list(mongo.db.rake_samples.find())
    
    return render_template('view_rake_samples.html', samples=samples)


@app.route('/generate_qr_code/<sample_type>/<sample_id>/<format>', methods=['GET'])
@login_required
def generate_qr_code(sample_type, sample_id, format):
    # Generate the QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)

    # Determine the URL based on the sample type
    if sample_type == 'truck':
        qr.add_data(url_for('add_truck_sample_analysis', sample_id=sample_id, _external=True))
    elif sample_type == 'rake':
        qr.add_data(url_for('add_rake_sample_analysis', sample_id=sample_id, _external=True))
    else:
        return "Invalid sample type", 400

    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Draw the sample_id on the QR code
    draw = ImageDraw.Draw(img)

    # Load a default font
    font = ImageFont.load_default()

    # Calculate text bounding box
    bbox = draw.textbbox((0, 0), sample_id, font=font)
    text_width = bbox[2] - bbox[0]  # Right - Left
    text_height = bbox[3] - bbox[1]  # Bottom - Top

    width, height = img.size
    text_position = ((width - text_width) / 2, height - text_height - 10)  # Centered at the bottom

    # Draw the sample_id on the image
    draw.text(text_position, sample_id, fill="black", font=font)

    # Define file paths based on format
    file_path = f"static/qrcodes/{sample_id}.{format}"
    
    # Ensure the static/qrcodes directory exists
    os.makedirs('static/qrcodes', exist_ok=True)

    # Save the image in the requested format
    if format == 'png':
        img.save(file_path)
        return send_file(file_path, mimetype='image/png', as_attachment=True)

    elif format == 'pdf':
        img.save(file_path.replace('.png', '.pdf'))  # Save as PDF
        return send_file(file_path.replace('.png', '.pdf'), mimetype='application/pdf', as_attachment=True)

    return "Invalid format", 400

@app.route('/print_labels', methods=['POST'])
@login_required
def print_labels():
    number_of_prints = int(request.form.get('number_of_prints', 1))
    sample_ids = request.form.getlist('sample_ids')

    print(f"Received sample_ids: {sample_ids}")  # Debug log

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)

    width, height = A4
    x, y = 20, height - 150  # Start position with 100px top margin
    qr_size = 150  # Size of each QR code
    spacing = 10  # Space between QR codes

    for sample_id in sample_ids:
        # Try to find the sample in both collections
        sample = mongo.db.rake_samples.find_one({'sample_id': sample_id})
        
        if sample:
            sample_type = 'rake'
        else:
            sample = mongo.db.truck_samples.find_one({'sample_id': sample_id})
            if sample:
                sample_type = 'truck'
            else:
                print(f"No sample found for sample_id: {sample_id}")
                continue  # Skip to the next sample_id if not found

        # Determine the URL based on the sample type
        if sample_type == 'rake':
            url = url_for('add_rake_sample_analysis', sample_id=sample_id, _external=True)
        else:
            url = url_for('add_truck_sample_analysis', sample_id=sample_id, _external=True)

        for _ in range(number_of_prints):
            # Generate QR code with the URL
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(url)  # Add the constructed URL
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Save QR code to a temporary file
            qr_file_path = f'temp_{sample_id}.png'
            img.save(qr_file_path)

            # Draw the QR code on the PDF
            c.drawImage(qr_file_path, x, y, width=qr_size, height=qr_size)

            # Add sample ID centered below the QR code
            text_width = c.stringWidth(sample_id, "Helvetica", 5)
            c.drawString(x + (qr_size - text_width) / 2, y - (spacing + 10), sample_id)

            # Move right for the next QR code
            x += qr_size + spacing

            # If reaching the end of the row (3 QR codes), reset x and move down to the next row
            if x + qr_size > width - 20:
                x = 20
                y -= (qr_size + spacing + 20)

            # Prevent moving off the page
            if y - (qr_size + spacing + 20) < 20:
                c.showPage()
                x, y = 20, height - 100

            # Clean up the temporary QR code file
            os.remove(qr_file_path)

    c.save()
    pdf_buffer.seek(0)

    filename = f'labels_{sample_ids[0]}.pdf' if sample_ids else 'labels.pdf'
    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')









@app.route('/upload_profile_image', methods=['POST'])
@login_required
def upload_profile_image():
    if 'profile_image' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('profile'))

    file = request.files['profile_image']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('profile'))

    # Save the file
    filename = secure_filename(file.filename)
    file_path = os.path.join('static/profile_images', filename)
    file.save(file_path)

    # Update user profile
    mongo.db.users.update_one(
        {'email': current_user.email},
        {'$set': {'profile_image': file_path}}
    )

    flash('Profile image uploaded successfully.', 'success')
    return redirect(url_for('profile'))


@app.route('/user/<user_id>', methods=['GET', 'POST'])
@login_required
def user_details(user_id):
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    
    if request.method == 'POST':
        # Handle form submission
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        mobile_no = request.form['mobile_no']
        department = request.form['department']
        role = request.form['role']

        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'mobile_no': mobile_no,
                'department': department,
                'role': role
            }}
        )
        flash("User details updated successfully!", "success")
        return redirect(url_for('user_details', user_id=user_id))

    return render_template('user_details.html', user=user)


@app.route('/users')
@login_required
def view_users():
    users = list(mongo.db.users.find())
    return render_template('view_users.html', users=users)

@app.route('/edit_user/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    
    if request.method == 'POST':
        # Update user details
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'first_name': request.form['first_name'],
                    'last_name': request.form['last_name'],
                    'mobile_no': request.form['mobile_no'],
                    'department': request.form['department'],
                    'role': request.form['role']
                }
            }
        )
        flash('User updated successfully!', 'success')
        return redirect(url_for('view_users'))

    return render_template('edit_user.html', user=user_data)

@app.route('/add_rake_sample_analysis/<sample_id>', methods=['GET', 'POST'])
@login_required
def add_rake_sample_analysis(sample_id):
    print(f"Requested sample_id: {sample_id}") 
    # Check user role and redirect if not authorized
    user_role = current_user.role.lower()  # Convert role to lowercase
    if user_role not in ['cpp_user', 'ccr_user']:
        flash("You do not have permission to access this page.", "warning")
        return redirect(url_for('dashboard'))  # Change 'dashboard' to your dashboard route

    # Fetch existing data for the sample ID
    existing_data = mongo.db.rake_sample_analysis.find_one({'sample_id': sample_id})

    if request.method == 'POST':
        # Check if the appropriate analysis data already exists based on user role
        if existing_data:
            if user_role == 'cpp_user' and 'analysis_cpp' in existing_data:
                flash("Error: CPP analysis data for this sample ID is already filled up.", "danger")
                return redirect(url_for('view_sample_analysis', sample_id=sample_id))
            elif user_role == 'ccr_user' and 'analysis_ccr' in existing_data:
                flash("Error: CCR analysis data for this sample ID is already filled up.", "danger")
                return redirect(url_for('view_sample_analysis', sample_id=sample_id))

        # Collect and convert data from the form to float
        try:
            analysis_data = {
                'sample_id': sample_id,
                'inherent_moisture': float(request.form['inherent_moisture']),
                'gcv_adb': float(request.form['gcv_adb']),
                'gcv_arb': float(request.form['gcv_arb']),
                'total_moisture': float(request.form['total_moisture']),
                'volatile_matter': float(request.form['volatile_matter']),
                'ash': float(request.form['ash']),
                'fixed_carbon': float(request.form['fixed_carbon']),
                'created_at': datetime.utcnow()
            }

            # Save data according to user role
            if user_role == 'cpp_user':
                mongo.db.rake_sample_analysis.update_one(
                    {'sample_id': sample_id},
                    {'$set': {'analysis_cpp': analysis_data}},
                    upsert=True
                )
            elif user_role == 'ccr_user':
                mongo.db.rake_sample_analysis.update_one(
                    {'sample_id': sample_id},
                    {'$set': {'analysis_ccr': analysis_data}},
                    upsert=True
                )

            flash("Rake sample analysis submitted successfully!", "success")
            return redirect(url_for('view_rakes_samples',sample_id = sample_id))
        
        except ValueError:
            flash("Invalid input. Please ensure all fields are numeric.", "danger")
            return redirect(url_for('add_rake_sample_analysis', sample_id=sample_id))

    # Render the form, passing existing data if available
    return render_template('add_rake_sample_analysis.html', sample_id=sample_id, existing_data=existing_data or {})



@app.route('/submit_rake_sample_analysis/<sample_id>', methods=['POST'])
@login_required
def submit_rake_sample_analysis(sample_id):
    print("Sample ID:", sample_id)  # Log the sample ID
    print("Form Data:", request.form)  # Log the form data

    # Check user role and redirect if not authorized
    user_role = current_user.role.lower()  # Convert role to lowercase
    if user_role not in ['cpp_user', 'ccr_user']:
        flash("You do not have permission to access this page.", "warning")
        return redirect(url_for('dashboard'))  # Change 'dashboard' to your dashboard route

    # Fetch existing data for the sample ID
    existing_data = mongo.db.rake_samples.find_one({'sample_id': sample_id})

    # Check if the appropriate analysis data already exists based on user role
    if existing_data:
        if user_role == 'cpp_user' and 'analysis_cpp' in existing_data:
            flash("Error: CPP analysis data for this sample ID is already filled up.", "danger")
            return redirect(url_for('view_rake_samples'))
        elif user_role == 'ccr_user' and 'analysis_ccr' in existing_data:
            flash("Error: CCR analysis data for this sample ID is already filled up.", "danger")
            return redirect(url_for('view_rake_samples'))

    # Collect data from the form
    try:
        analysis_data = {
            'sample_id': sample_id,
            'inherent_moisture': float(request.form.get('inherent_moisture')),
            'gcv_adb': float(request.form.get('gcv_adb')),
            'gcv_arb': float(request.form.get('gcv_arb')),
            'total_moisture': float(request.form.get('total_moisture')),
            'volatile_matter': float(request.form.get('volatile_matter')),
            'ash': float(request.form.get('ash')),
            'fixed_carbon': float(request.form.get('fixed_carbon')),
            'created_at': datetime.now(timezone.utc)  # Use timezone-aware datetime
        }
    except ValueError:
        flash("Invalid input. Please ensure all fields are numeric.", "danger")
        return redirect(url_for('view_rake_samples'))

    print("Analysis Data to Update:", analysis_data)  # Log the analysis data

    # Attempt to update the analysis data in the database based on user role
    if user_role == 'cpp_user':
        mongo.db.rake_samples.update_one(
            {'sample_id': sample_id},
            {'$set': {'analysis_cpp': analysis_data}},
            upsert=True
        )
    elif user_role == 'ccr_user':
        mongo.db.rake_samples.update_one(
            {'sample_id': sample_id},
            {'$set': {'analysis_ccr': analysis_data}},
            upsert=True
        )

    flash("Rake sample analysis updated successfully!", "success")
    return redirect(url_for('view_rake_samples'))  # Redirect to the rake samples view


@app.route('/add_truck_sample_analysis/<sample_id>', methods=['GET', 'POST'])
@login_required
def add_truck_sample_analysis(sample_id):
    print(f"Requested sample_id: {sample_id}") 
    # Check user role and redirect if not authorized
    user_role = current_user.role.lower()  # Convert role to lowercase
    if user_role not in ['cpp_user', 'ccr_user']:
        flash("You do not have permission to access this page.", "warning")
        return redirect(url_for('dashboard'))  # Change 'dashboard' to your dashboard route

    # Fetch existing data for the sample ID
    existing_data = mongo.db.truck_samples_analysis.find_one({'sample_id': sample_id})

    if request.method == 'POST':
        # Check if the appropriate analysis data already exists based on user role
        if existing_data:
            if user_role == 'cpp_user' and 'analysis_cpp' in existing_data:
                flash("Error: CPP analysis data for this sample ID is already filled up.", "danger")
                return redirect(url_for('view_sample_analysis', sample_id=sample_id))
            elif user_role == 'ccr_user' and 'analysis_ccr' in existing_data:
                flash("Error: CCR analysis data for this sample ID is already filled up.", "danger")
                return redirect(url_for('view_sample_analysis', sample_id=sample_id))

        # Collect and convert data from the form to float
        try:
            analysis_data = {
                'sample_id': sample_id,
                'inherent_moisture': float(request.form['inherent_moisture']),
                'gcv_adb': float(request.form['gcv_adb']),
                'gcv_arb': float(request.form['gcv_arb']),
                'total_moisture': float(request.form['total_moisture']),
                'volatile_matter': float(request.form['volatile_matter']),
                'ash': float(request.form['ash']),
                'fixed_carbon': float(request.form['fixed_carbon']),
                'created_at': datetime.utcnow()
            }

            # Save data according to user role
            if user_role == 'cpp_user':
                mongo.db.truck_samples_analysis.update_one(
                    {'sample_id': sample_id},
                    {'$set': {'analysis_cpp': analysis_data}},
                    upsert=True
                )
            elif user_role == 'ccr_user':
                mongo.db.truck_samples_analysis.update_one(
                    {'sample_id': sample_id},
                    {'$set': {'analysis_ccr': analysis_data}},
                    upsert=True
                )

            flash("Truck sample analysis submitted successfully!", "success")
            return redirect(url_for('view_truck_samples',sample_id = sample_id))
        
        except ValueError:
            flash("Invalid input. Please ensure all fields are numeric.", "danger")
            return redirect(url_for('add_truck_sample_analysis', sample_id=sample_id))

    # Render the form, passing existing data if available
    return render_template('add_truck_sample_analysis.html', sample_id=sample_id, existing_data=existing_data or {})

@app.route('/submit_truck_sample_analysis/<sample_id>', methods=['POST'])
@login_required
def submit_truck_sample_analysis(sample_id):
    print("Sample ID:", sample_id)  # Log the sample ID
    print("Form Data:", request.form)  # Log the form data

    # Check user role and redirect if not authorized
    user_role = current_user.role.lower()  # Convert role to lowercase
    if user_role not in ['cpp_user', 'ccr_user']:
        flash("You do not have permission to access this page.", "warning")
        return redirect(url_for('dashboard'))  # Change 'dashboard' to your dashboard route

    # Fetch existing data for the sample ID
    existing_data = mongo.db.truck_samples.find_one({'sample_id': sample_id})

    # Check if the appropriate analysis data already exists based on user role
    if existing_data:
        if user_role == 'cpp_user' and 'analysis_cpp' in existing_data:
            flash("Error: CPP analysis data for this sample ID is already filled up.", "danger")
            return redirect(url_for('view_truck_samples'))
        elif user_role == 'ccr_user' and 'analysis_ccr' in existing_data:
            flash("Error: CCR analysis data for this sample ID is already filled up.", "danger")
            return redirect(url_for('view_truck_samples'))

    # Collect data from the form
    try:
        analysis_data = {
            'sample_id': sample_id,
            'inherent_moisture': float(request.form.get('inherent_moisture')),
            'gcv_adb': float(request.form.get('gcv_adb')),
            'gcv_arb': float(request.form.get('gcv_arb')),
            'total_moisture': float(request.form.get('total_moisture')),
            'volatile_matter': float(request.form.get('volatile_matter')),
            'ash': float(request.form.get('ash')),
            'fixed_carbon': float(request.form.get('fixed_carbon')),
            'created_at': datetime.now(timezone.utc)  # Use timezone-aware datetime
        }
    except ValueError:
        flash("Invalid input. Please ensure all fields are numeric.", "danger")
        return redirect(url_for('view_truck_samples'))

    print("Analysis Data to Update:", analysis_data)  # Log the analysis data

    # Attempt to update the analysis data in the database based on user role
    if user_role == 'cpp_user':
        mongo.db.truck_samples.update_one(
            {'sample_id': sample_id},
            {'$set': {'analysis_cpp': analysis_data}},
            upsert=True
        )
    elif user_role == 'ccr_user':
        mongo.db.truck_samples.update_one(
            {'sample_id': sample_id},
            {'$set': {'analysis_ccr': analysis_data}},
            upsert=True
        )

    flash("Rake sample analysis updated successfully!", "success")
    return redirect(url_for('view_truck_samples'))  # Redirect to the rake samples view




@app.route('/view_sample_analysis/<sample_id>', methods=['GET'])
@login_required
def view_sample_analysis(sample_id):
    analysis = mongo.db.sample_analysis.find_one({'sample_id': sample_id})
    return render_template('view_sample_analysis.html', analysis=analysis)




@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

# @app.route('/google_login')
# def google_login():
#     if not google.authorized:
#         return redirect(url_for('google.login'))
    
#     resp = google.get("/plus/v1/people/me")
#     assert resp.ok, resp.text
#     email = resp.json()["emails"][0]["value"]
#     user = User(email)  # Replace this with your user retrieval logic
#     login_user(user)
#     flash("Logged in with Google.", "success")
#     return redirect(url_for('dashboard'))

# @app.route('/microsoft_login')
# def microsoft_login():
#     if not microsoft.authorized:
#         return redirect(url_for('microsoft.login'))
    
#     resp = microsoft.get("/v1.0/me")
#     assert resp.ok, resp.text
#     email = resp.json()["mail"]
#     user = User(email)  # Replace this with your user retrieval logic
#     login_user(user)
#     flash("Logged in with Microsoft.", "success")
#     return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)