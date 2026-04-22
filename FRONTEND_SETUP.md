# Frontend Setup & Deployment Guide

Complete guide for setting up and deploying the AutoQA Pro React frontend.

## Quick Start (5 minutes)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Then open http://localhost:3000 in your browser.

## Full Setup Guide

### 1. Prerequisites

- Node.js 18.x or higher
- npm 9+ (or yarn/pnpm)
- Git
- Backend API running on http://localhost:5000

### 2. Installation

```bash
# Clone or navigate to project
cd frontend

# Install dependencies
npm install
# or: yarn install / pnpm install

# Create environment file
cp .env.example .env.local
```

### 3. Environment Configuration

Edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_APP_NAME=AutoQA Pro
```

**Important**: Environment variables must start with `NEXT_PUBLIC_` to be accessible in the browser.

### 4. Development Server

```bash
npm run dev
```

This starts the Next.js dev server with hot reloading at http://localhost:3000.

## Project Structure

```
frontend/
├── app/                    # Next.js 15 app directory
│   ├── (auth)/            # Auth pages group (login, register)
│   ├── dashboard/         # Main dashboard
│   ├── regression/        # Regression analysis
│   ├── insights/          # AI insights/chat
│   ├── jobs/             # Job monitoring
│   ├── upload/           # Data upload
│   ├── layout.tsx        # Root layout with sidebar
│   ├── globals.css       # Global styles + design tokens
│   └── page.tsx          # Root page redirect
├── components/
│   ├── ui/               # shadcn UI components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── input.tsx
│   └── layout/           # Layout-specific components
│       ├── sidebar.tsx
│       └── topnav.tsx
├── lib/
│   ├── api-client.ts    # Axios API client + interceptors
│   └── utils.ts         # Utility functions (cn, etc)
├── public/              # Static files
├── package.json         # Dependencies
├── tsconfig.json        # TypeScript config
├── tailwind.config.ts   # Tailwind config
├── postcss.config.js    # PostCSS config
└── next.config.js       # Next.js config
```

## Available Scripts

```bash
npm run dev          # Start development server (port 3000)
npm run build        # Build for production
npm start            # Start production server
npm run lint         # Run ESLint
npm run type-check   # Check TypeScript
```

## Key Features

### Pages Included

1. **Dashboard** (`/dashboard`)
   - Real-time metrics (tests, pass rate, failures, duration)
   - Weekly performance chart
   - Recent jobs list
   - AI insights summary

2. **Regression Analysis** (`/regression`)
   - Trend analysis with baseline comparison
   - Failed tests table with severity
   - Regression status indicator

3. **AI Insights** (`/insights`)
   - Chat interface with AI assistant
   - Error explanation and analysis
   - Common issues quick access
   - Analysis history

4. **Job Monitoring** (`/jobs`)
   - Active and queued jobs display
   - Real-time progress tracking
   - Job actions (pause, resume, cancel)
   - Test execution metrics

5. **Data Upload** (`/upload`)
   - Drag & drop file upload
   - Upload history with status
   - Supported formats information
   - Processing status tracking

### Authentication

Login page at `/login` with:
- Email/password form
- Error handling
- Redirect to dashboard on success
- Register link

## API Client Usage

The centralized API client is in `lib/api-client.ts`:

```typescript
import { api } from '@/lib/api-client'

// Login
const response = await api.login('user@example.com', 'password')

// Get jobs
const jobs = await api.getJobs()

// Queue tests
await api.queueTests('project-id')

// AI analysis
const analysis = await api.analyzeError('Error message')
```

### Interceptors

The client includes:
- **Request**: Adds Authorization header with token from localStorage
- **Response**: Auto-redirects to login on 401 Unauthorized

## Design System

### Colors

All colors defined as CSS variables in `globals.css`:

```css
--primary: 217.2 91.2% 59.8%;     /* Blue */
--secondary: 210 40% 96%;         /* Light gray */
--destructive: 0 84.2% 60.2%;    /* Red */
--accent: 0 84.2% 60.2%;         /* Red (alerts) */
```

### Typography

- **Font Family**: System default (sans-serif)
- **Heading**: Bold, larger sizes
- **Body**: Regular weight, readable line height

### Components

- **Button**: Multiple variants (default, ghost, outline, destructive)
- **Card**: Container with header, content, footer
- **Input**: Text input with focus states
- **Badges**: Status indicators

## Deployment Options

### Option 1: Vercel (Recommended)

Vercel is the official Next.js hosting platform.

1. **Push code to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Connect to Vercel**
   - Go to https://vercel.com
   - Click "New Project"
   - Select GitHub repo
   - Vercel auto-detects Next.js

3. **Configure Environment**
   - Add `NEXT_PUBLIC_API_URL` in Project Settings → Environment Variables
   - Set to your production API URL

4. **Deploy**
   - Automatic on push to main branch
   - Preview deployments for PRs

### Option 2: Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

Build and run:
```bash
docker build -t autoqa-frontend .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=https://api.example.com \
  autoqa-frontend
```

### Option 3: Self-Hosted (Linux/Ubuntu)

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone and build
git clone <repo>
cd frontend
npm install
npm run build

# Start with PM2
npm install -g pm2
pm2 start "npm start" --name "autoqa-frontend"
pm2 save
pm2 startup
```

## Performance Tips

1. **Image Optimization** - Next.js auto-optimizes images
2. **Code Splitting** - Automatic per-route splitting
3. **CSS Optimization** - Tailwind PurgeCSS removes unused styles
4. **Prefetching** - Link component auto-prefetches routes

## Troubleshooting

### Issue: "API connection failed"

**Solution**: 
1. Ensure backend is running: `python app.py`
2. Check `NEXT_PUBLIC_API_URL` is correct
3. Verify CORS enabled in backend
4. Check network tab in DevTools

### Issue: "Port 3000 already in use"

**Solution**:
```bash
# Kill process using port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
npm run dev -- -p 3001
```

### Issue: "Styling not applied"

**Solution**:
1. Rebuild: `npm run build`
2. Clear cache: `rm -rf .next && npm run dev`
3. Check Tailwind config in `tailwind.config.ts`

### Issue: "TypeScript errors"

**Solution**:
```bash
npm run type-check  # Check for errors
npm install         # Ensure deps installed
```

## Security Checklist

- [x] HTTPS in production (handled by hosting)
- [x] Auth token in localStorage (consider secure HttpOnly in future)
- [x] API requests authenticated (Bearer token)
- [x] Input validation in forms
- [x] XSS protection (React escapes by default)
- [x] CSRF tokens handled by backend

## Monitoring & Logging

### Browser DevTools

- **Network Tab**: Monitor API calls
- **Console**: Check for errors and debug logs
- **Performance**: Check page load metrics

### Production Monitoring

Consider adding:
- Sentry for error tracking
- Vercel Analytics for performance
- LogRocket for session replay

## Next Steps

1. **Connect Backend**: Ensure API running at configured URL
2. **User Testing**: Test login flow, basic navigation
3. **Performance Testing**: Check load times, memory usage
4. **Deploy**: Follow option above for your hosting choice
5. **Monitor**: Set up error tracking and analytics

## Support

- See `README.md` in frontend directory
- See `PROJECT_OVERVIEW.md` in project root
- Check backend documentation for API details

## Version History

- v1.0.0 - Initial release with all core features
- Compatible with Python backend v1.0.0+
- Next.js 15.0.0+
