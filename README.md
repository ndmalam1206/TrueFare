# TrueFare AI – Local Transport Fare Intelligence System

A modern single-page web application for finding local transport fares with admin-controlled intelligence and crowd-assisted feedback.

## ✨ Features

- **Single-Page Application**: Everything accessible from one homepage
- **Modern UI**: Startup-style design with hero section, gradients, and smooth interactions
- **Real-time Search**: Google-like autocomplete with dynamic fare results
- **Modal-Based UX**: Feedback submission and admin login via popup modals
- **Admin Dashboard**: Integrated admin panel for route management
- **Responsive Design**: Mobile-friendly with Bootstrap 5
- **AJAX-Powered**: No page reloads, smooth user experience

## 🎨 UI Design

### Hero Section
- Full-screen background image (city/transport theme)
- Gradient overlay for text readability
- Centered branding: "TrueFare AI - Know the Right Fare"

### Search Section
- Clean card layout with shadow effects
- Autocomplete location inputs
- Dynamic result display with fare, route, and confidence indicators

### Interactive Elements
- **Feedback Modal**: Popup form for user submissions
- **Admin Login Modal**: Secure authentication popup
- **Admin Panel**: Hidden dashboard that appears after login
- **Smooth Transitions**: Bootstrap modals and animations

## 🚀 How to Run

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database:**
   ```bash
   # Set ADMIN_PASSWORD in your environment before initializing a new admin account.
   python init_db.py
   ```

3. **Add Sample Data (Optional):**
   ```bash
   python sample_data.py
   ```

4. **Start Application:**
   ```bash
   python app.py
   ```

5. **Access:**
   - Main Application: http://127.0.0.1:5000
   - Admin Access: Click "Admin Login" button
     - Username: the value of `ADMIN_USERNAME` (defaults to `admin`)
     - Password: the value of `ADMIN_PASSWORD`

## 🔧 Technical Architecture

### Backend (Flask + Python)
- **API Endpoints**: JSON responses for AJAX calls
- **Session Management**: Secure admin authentication
- **Database**: SQLite with SQLAlchemy ORM
- **Validation**: Comprehensive input validation and error handling

### Frontend (HTML + Bootstrap + JavaScript)
- **Single Page**: All functionality in one view
- **Modals**: Bootstrap modals for forms and admin panel
- **AJAX**: Fetch API for seamless interactions
- **Autocomplete**: Real-time location suggestions
- **Dynamic UI**: Show/hide elements based on state

### Key API Endpoints
- `POST /search` - Fare calculation
- `POST /feedback` - User feedback submission
- `POST /admin/login` - Admin authentication
- `GET /api/admin/routes` - Route management
- `GET /api/admin/feedback` - Feedback overview
- `POST /api/admin/add_route` - Add new routes
- `POST /api/admin/approve_route` - Approve feedback

## 🎯 User Experience Flow

1. **Landing**: Hero section with clear value proposition
2. **Search**: Enter locations, get instant fare results
3. **Feedback**: Submit fares for unlisted routes via modal
4. **Admin**: Login via modal, access dashboard in same page
5. **Management**: Add routes, view/approve feedback seamlessly

## 🔐 Security Features

- Password hashing with bcrypt
- Session-based authentication
- Input validation and sanitization
- CSRF protection via Flask-WTF (if needed)
- Secure admin routes with authorization checks

## 📱 Responsive Design

- **Mobile-First**: Optimized for all screen sizes
- **Touch-Friendly**: Large buttons and inputs
- **Fast Loading**: Minimal dependencies, efficient code
- **Accessible**: Semantic HTML and ARIA attributes

## 🚀 Production Ready

For production deployment:
- Use a production WSGI server (Gunicorn)
- Configure proper database (PostgreSQL)
- Set up environment variables for secrets
- Enable HTTPS and security headers
- Implement rate limiting and monitoring

## 📈 Performance

- **Fast Autocomplete**: Database-backed suggestions
- **Efficient Queries**: Optimized SQL with indexes
- **Minimal Bundle**: Lightweight frontend dependencies
- **Caching**: Browser caching for static assets

## 🤝 Contributing

This is a demonstration of modern web development practices combining:
- Clean UI/UX design
- RESTful API architecture
- Real-time interactions
- Secure authentication
- Scalable backend logic

Perfect for showcasing in portfolios or as a startup MVP!
- View fare results with confidence levels

### For Admins
- Login at `/admin/login`
- Add verified routes
- View and approve community feedback
- Manage the system

## Security Features

- Password hashing with bcrypt
- Session-based authentication
- Protected admin routes
- Private feedback storage
- Input validation

## API Endpoints

- `/` - Main search page
- `/search` - Fare search (POST)
- `/feedback` - Submit feedback (POST)
- `/autocomplete` - Location suggestions (GET)
- `/admin/*` - Admin panel routes

## Database Schema

- `locations`: Location data
- `routes`: Verified and community routes
- `feedback`: User-submitted fare data
- `admin_users`: Admin authentication

## Production Deployment

For production:
- Set `SECRET_KEY` environment variable
- Use a production WSGI server (gunicorn)
- Configure Google Places API key
- Use a proper database (PostgreSQL)
- Enable HTTPS
- Set up proper logging and monitoring

## License

This project is for educational and demonstration purposes.