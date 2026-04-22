# AutoQA Pro - Modern React Frontend

A modern, responsive SaaS frontend for performance analysis and QA automation built with Next.js 15, TypeScript, and Tailwind CSS.

## Features

- **Dashboard** - Real-time metrics and performance overview
- **Regression Analysis** - Track performance changes and identify regressions
- **AI Insights** - Chat with AI assistant for error analysis and recommendations
- **Job Monitor** - Track and manage test execution jobs
- **Data Upload** - Upload test results and performance data
- **Responsive Design** - Works perfectly on desktop, tablet, and mobile

## Tech Stack

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Accessible UI components
- **Recharts** - Data visualization library
- **Axios** - HTTP client for API calls
- **Lucide React** - Beautiful icons

## Getting Started

### Prerequisites

- Node.js 18+
- npm, yarn, or pnpm

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env.local` file:
```bash
cp .env.example .env.local
```

3. Configure environment variables:
```
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_APP_NAME=AutoQA Pro
```

### Development

Start the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── app/
│   ├── (auth)/          # Authentication pages
│   ├── dashboard/       # Main dashboard page
│   ├── regression/      # Regression analysis page
│   ├── insights/        # AI insights and chat
│   ├── jobs/           # Job monitoring
│   ├── upload/         # Data upload page
│   ├── layout.tsx      # Root layout
│   └── globals.css     # Global styles
├── components/
│   ├── ui/            # shadcn UI components
│   └── layout/        # Layout components (sidebar, nav)
├── lib/
│   ├── api-client.ts  # Axios API client
│   └── utils.ts       # Utility functions
└── public/            # Static assets
```

## Key Components

### Layout Components
- **Sidebar** - Navigation sidebar with active state
- **TopNav** - Top navigation bar with user menu

### Pages
- **Dashboard** - Metrics cards, charts, recent jobs
- **Regression** - Trend analysis, failed tests table
- **Insights** - AI chat interface with message history
- **Jobs** - Job queue with progress tracking
- **Upload** - File upload with history

### UI Components
- Button - Multiple variants (default, ghost, outline, etc.)
- Card - Container with header and content sections
- Input - Text input field

## API Integration

The frontend connects to the Python backend via REST API. All API calls go through the centralized API client in `lib/api-client.ts`.

### Key Endpoints Used

- `POST /api/auth/login` - User authentication
- `GET /api/jobs` - List all jobs
- `POST /api/jobs/projects/{id}/run-tests` - Queue tests
- `POST /api/ai/explain-error` - AI error analysis
- `GET /api/monitoring/jobs/stats` - Dashboard metrics

## Styling

The app uses Tailwind CSS with a custom color scheme:
- **Primary**: Blue (#2563eb)
- **Secondary**: Light gray
- **Accent**: Red (destructive/alerts)
- **Background**: White

All colors are defined as CSS variables in `globals.css` for easy customization.

## Performance

- Server-side rendering for fast initial loads
- Image optimization
- Code splitting by route
- Tailwind CSS optimization for minimal bundle size

## Deployment

### Vercel (Recommended)

1. Push code to GitHub
2. Connect repo to Vercel
3. Set environment variables
4. Deploy with automatic builds

### Self-Hosted

1. Build the project:
```bash
npm run build
```

2. Start production server:
```bash
npm start
```

## Testing

The frontend is ready for integration testing. Key areas to test:
- Login/logout flow
- Dashboard metrics loading
- Job status updates
- AI chat interaction
- File upload functionality

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | http://localhost:5000 | Backend API URL |
| `NEXT_PUBLIC_APP_NAME` | No | AutoQA Pro | Application name |

## Troubleshooting

### API connection errors
- Ensure backend is running on `NEXT_PUBLIC_API_URL`
- Check CORS settings in backend
- Verify credentials in browser console

### Build errors
- Delete `.next` and `node_modules`
- Run `npm install` and `npm run build`

### Styling issues
- Clear browser cache
- Check Tailwind config matches your design tokens
- Verify CSS is being imported in `layout.tsx`

## Documentation

- See `ARCHITECTURE.md` for system design
- See `QUICK_START.md` for rapid setup guide
- Backend docs available in parent directory

## License

This project is part of AutoQA Pro SaaS platform.
