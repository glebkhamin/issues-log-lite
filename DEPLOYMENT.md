# Deployment Guide

## Option 1: Railway (Recommended)

1. **Create GitHub Repository:**
   - Go to https://github.com/new
   - Create a new repository called `issues-log-lite`
   - Don't initialize with README (we already have files)

2. **Push to GitHub:**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/issues-log-lite.git
   git branch -M main
   git push -u origin main
   ```

3. **Deploy to Railway:**
   - Go to https://railway.app
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your `issues-log-lite` repository
   - Railway will automatically detect it's a Python app

4. **Set Environment Variables:**
   - In Railway dashboard, go to your project
   - Click on "Variables" tab
   - Add: `APP_PASSWORD` = `your-secure-password-here`
   - Add: `SECRET_KEY` = `your-secret-key-here`

5. **Access Your App:**
   - Railway will provide a URL like `https://your-app.railway.app`
   - Share this URL with your team!

## Option 2: Render

1. **Push to GitHub** (same as above)

2. **Deploy to Render:**
   - Go to https://render.com
   - Sign up with GitHub
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Set:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `python app.py`
   - Add environment variables: `APP_PASSWORD` and `SECRET_KEY`

## Option 3: Heroku

1. **Push to GitHub** (same as above)

2. **Deploy to Heroku:**
   - Install Heroku CLI
   - `heroku create your-app-name`
   - `heroku config:set APP_PASSWORD=your-password`
   - `heroku config:set SECRET_KEY=your-secret-key`
   - `git push heroku main`

## Local Development

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/issues-log-lite.git
cd issues-log-lite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export APP_PASSWORD=your-password
export SECRET_KEY=your-secret-key

# Run the app
python app.py
```

## Environment Variables

- `APP_PASSWORD`: Admin password for login
- `SECRET_KEY`: Flask secret key for sessions
- `PORT`: Port number (automatically set by hosting platform)
