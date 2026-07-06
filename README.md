# CourseFinder 🎓

A full-stack web app that collects the best courses from YouTube, Coursera, and other platforms — all in one place. No more jumping between 15 tabs trying to find a good tutorial.

## What's Inside

- **13 tech categories** — Web Dev, Data Science, AI, ML, Cyber Security, Blockchain, Cloud, DevOps, VR/AR, Robotics, and more
- **60+ curated courses** — hand-picked links to actual courses, not random blog posts
- **User accounts** — sign up with email or Google, track your progress, save favorites, rate courses
- **Progress tracking** — mark courses as Not Started / Started / Completed, set custom progress percentages
- **Ratings & reviews** — leave 1-5 star ratings and written reviews for courses you've tried
- **Learning goals** — set targets like "Complete 5 Web Dev courses this month"
- **Daily streaks** — get a fire emoji 🔥 for visiting every day (because gamification works)
- **Dark mode** — because your eyes deserve a break
- **Fully responsive** — works on phone, tablet, desktop

## Tech Stack

| Layer | What's Used |
|-------|-------------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python Flask |
| Auth | Flask-Login + Google OAuth (Authlib) |
| Database | SQLite (built into Python, zero config) |
| Styling | Custom CSS with dark mode support |

## How to Run This Thing

### Prerequisites

- Python 3.8 or higher
- pip (comes with Python, usually)

### Step 1: Clone or Download

If you're reading this on GitHub, hit the green "Code" button → Download ZIP. Or if you're fancy with git:

```bash
git clone https://github.com/PredictiveManish/datadreamer-coursefinder.git
cd datadreamer-coursefinder
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You'll see `(venv)` at the start of your terminal. That means it's working.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, Flask-Login, Authlib (for Google OAuth), and a few other packages. If you don't plan to use Google sign-in, you can skip Authlib — the app still works with email/password only.

### Step 4: Set Up Google OAuth (Optional)

If you want Google sign-in, you need API keys. Here's how:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable the **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Set the authorized redirect URI to: `http://localhost:5000/api/auth/google/callback`
6. Copy your **Client ID** and **Client Secret**

Now open the `.env` file in the project root and paste them in:

```env
GOOGLE_CLIENT_ID=your-client-id-here
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

**Don't have API keys?** No problem. The app works perfectly fine without Google OAuth — you can still sign up with email and password. The Google button just won't work until you add the keys.

### Step 5: Run the Server

```bash
python backend/app.py
```

You should see something like:

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

Open `http://localhost:5000` in your browser. That's it. You're running CourseFinder.

## What Each Page Does

| Page | URL | What Happens |
|------|-----|--------------|
| Home | `/` | Browse all courses, search, filter, save favorites |
| Login | `/login` | Sign in with email/password or Google |
| Register | `/register` | Create a new account |
| Dashboard | `/dashboard` | Your stats, progress, goals, and reviews |
| Profile | `/profile` | Edit your name and bio |

## API Endpoints (for the nerds)

### Auth
- `POST /api/auth/register` — Create account
- `POST /api/auth/login` — Sign in
- `GET /api/auth/google` — Start Google OAuth
- `GET /api/auth/google/callback` — Google OAuth callback
- `GET /api/auth/logout` — Sign out
- `GET /api/auth/me` — Get current user info

### Courses
- `GET /api/courses?category=&search=&difficulty=&free=` — Browse/filter courses
- `GET /api/categories` — List all categories
- `GET /api/stats` — App-wide stats

### User Data (requires login)
- `GET /api/favorites` — Your saved courses
- `POST /api/favorites` — Add to favorites
- `DELETE /api/favorites/<url>` — Remove from favorites
- `GET /api/progress` — Your course progress
- `POST /api/progress` — Update progress
- `GET /api/reviews` — Your reviews
- `POST /api/reviews` — Submit a review
- `DELETE /api/reviews/<url>` — Delete a review
- `GET /api/goals` — Your learning goals
- `POST /api/goals` — Set a goal
- `PUT /api/profile` — Update profile

### Health
- `GET /api/health` — Check if the API is alive

## Database Structure

Everything's stored in SQLite (one file: `coursefinder.db`). Here's what's in it:

- **users** — email, name, avatar, password hash, Google ID, join date, bio, streak
- **favorites** — which courses each user saved
- **progress** — course status (not_started/started/completed), percentage, notes
- **reviews** — star ratings and text reviews per course
- **goals** — learning targets per category

No external database needed. SQLite is built into Python. It's perfect for small-to-medium apps and doesn't require any setup.

## Project Structure

```
datadreamer-coursefinder/
├── backend/
│   └── app.py              # Flask app + all API routes
├── templates/
│   ├── index.html          # Main page with course grid
│   ├── login.html          # Login form
│   ├── register.html       # Registration form
│   ├── dashboard.html      # User dashboard
│   └── profile.html        # Edit profile page
├── static/
│   ├── css/
│   │   └── style.css       # All styles (light + dark mode)
│   ├── js/
│   │   └── app.js          # Frontend logic (search, auth, progress, reviews)
│   └── images/             # Logo and course category icons
├── .env                    # Google OAuth keys (add your own)
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Customization Ideas

- Add more categories and courses by editing the `COURSES` list in `backend/app.py`
- Change the color scheme by editing CSS variables in `static/css/style.css`
- Add more social login options (GitHub, Twitter, etc.)
- Connect to PostgreSQL or MySQL for production use
- Add Docker support for easy deployment
- Add email verification for new accounts

## Known Issues

- The `.env` file isn't loaded if `python-dotenv` isn't installed. Install it with `pip install python-dotenv` if you want `.env` support.
- Google OAuth requires setting up a project in Google Cloud Console. If you don't have API keys, Google sign-in won't work (but email/password still does).
- SQLite isn't ideal for high-traffic production apps. Consider PostgreSQL or MySQL if you expect lots of users.

## License

This project is open source. Do whatever you want with it. Just don't blame me if it breaks your computer.

## Credits

Built by someone who was tired of opening 20 tabs to find a good course. Now all those tabs are in one place. You're welcome.

---

Questions? Found a bug? Want to contribute? Open an issue or submit a pull request. Happy learning! 🚀
