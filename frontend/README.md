# 4-Plex Foreclosure Research Dashboard

A comprehensive React-based dashboard for the integrated 4-plex foreclosure research and investment analysis platform.

## Features

### 🏠 Property Discovery & Management
- Real-time property discovery across Georgia counties
- Advanced filtering and search capabilities
- Property status tracking through the full pipeline
- Batch operations and exports

### 📊 Investment Analysis
- Comprehensive investment scoring (0-100)
- Financial projections and ROI calculations
- Risk assessment and mitigation strategies
- Comparative market analysis

### 🎯 Opportunity Identification
- High-value opportunity highlighting
- Customizable investment criteria
- Alert system for urgent opportunities
- Portfolio performance tracking

### 📈 Dashboard & Analytics
- Real-time system metrics
- County-based performance breakdown
- Recent activity monitoring
- Processing pipeline visualization

## Technology Stack

- **Frontend**: React 18 with Material-UI v5
- **State Management**: React Hooks and Context
- **HTTP Client**: Axios with interceptors
- **Routing**: React Router v6
- **Charts**: Recharts
- **Date Handling**: date-fns
- **Build Tool**: Create React App

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn
- Integration API server running on port 11060

### Installation

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your API endpoints

# Start development server
npm start
```

The application will be available at `http://localhost:3000`.

### Environment Variables

```env
REACT_APP_FORECLOSURE_API=http://localhost:11050
REACT_APP_VALUATION_API=http://localhost:3000
REACT_APP_INTEGRATION_API=http://localhost:11060
REACT_APP_NEO4J_URL=http://localhost:7475
```

## Project Structure

```
src/
├── components/
│   └── Layout/
│       └── Navbar.js           # Main navigation
├── pages/
│   ├── Dashboard.js            # Main dashboard
│   ├── PropertyDiscovery.js    # Property search & discovery
│   ├── PropertyAnalysis.js     # Analysis queue management
│   ├── InvestmentOpportunities.js # High-value opportunities
│   ├── PropertyDetails.js      # Detailed property view
│   └── SystemHealth.js         # System monitoring
├── services/
│   └── api.js                  # API client and services
├── utils/
│   └── formatters.js           # Data formatting utilities
├── App.js                      # Main app component
└── index.js                    # Entry point
```

## API Integration

The dashboard integrates with the Unified API (`/api/unified/*`) endpoints:

### Core Endpoints
- `GET /api/unified/health` - System health check
- `GET /api/unified/dashboard/summary` - Dashboard metrics
- `GET /api/unified/opportunities` - Investment opportunities
- `GET /api/unified/properties` - Property listings
- `POST /api/unified/discovery/start` - Start discovery job

### Property Management
- `GET /api/unified/properties/{id}` - Property details
- `POST /api/unified/properties/{id}/analyze` - Trigger analysis
- `POST /api/unified/properties/{id}/enrich` - Enrich data

### Analysis & Jobs
- `GET /api/unified/analysis/queue` - Analysis queue status
- `GET /api/unified/analysis/{id}/results` - Analysis results

## Key Components

### Dashboard
- **Metrics Overview**: Total properties, high-value opportunities, avg scores
- **County Distribution**: Properties by Georgia county
- **Processing Status**: Pipeline status breakdown
- **Recent Activity**: Latest discoveries and analyses
- **Top Opportunities**: Highest-scoring properties

### Investment Opportunities
- **Advanced Filtering**: Score thresholds, county, price ranges
- **Opportunity Cards**: Detailed property summaries
- **Investment Metrics**: ROI, cap rate, cash flow projections
- **Batch Actions**: Multi-property operations

### Property Details
- **Comprehensive View**: All property data in one place
- **Financial Analysis**: Complete investment calculations
- **Foreclosure Info**: Status, dates, legal details
- **Action Center**: Schedule inspections, add notes, export reports

## Development

### Available Scripts

```bash
npm start          # Development server
npm test           # Run test suite
npm run build      # Production build
npm run lint       # Code linting
npm run format     # Code formatting
```

### Code Style
- ESLint + Prettier for consistent formatting
- Material-UI design system compliance
- Responsive design principles
- Accessibility best practices

### Testing Strategy
- Unit tests for utilities and services
- Component testing with React Testing Library
- Integration tests for API interactions
- E2E tests for critical user flows

## Deployment

### Docker Deployment

```bash
# Build image
docker build -f Dockerfile.unified -t 4plex-dashboard .

# Run container
docker run -p 3000:3000 \
  -e REACT_APP_INTEGRATION_API=http://localhost:11060 \
  4plex-dashboard
```

### Production Build

```bash
npm run build
# Serve build/ directory with your preferred web server
```

## Features by Page

### Dashboard (`/`)
- System health overview
- Key performance indicators
- County and status distributions
- Recent activity feed
- Top investment opportunities

### Property Discovery (`/discovery`)
- Start new discovery jobs
- Monitor discovery progress
- Filter discovered properties
- Bulk actions and exports

### Investment Opportunities (`/opportunities`)
- High-scoring property listings
- Advanced filtering options
- Investment metrics display
- Opportunity rating system

### Property Details (`/property/:id`)
- Complete property information
- Financial projections
- Foreclosure status tracking
- Action buttons (analyze, inspect, etc.)

### System Health (`/system`)
- API health monitoring
- Service status indicators
- Performance metrics
- Integration health checks

## Integration Points

### Foreclosure Research System
- Property discovery data
- Foreclosure status updates
- Code violation information
- County-specific data collection

### Multifamily Valuation System
- Investment analysis results
- Financial projections
- Market comparisons
- Renovation estimates

### Neo4j Graph Database
- Property relationship mapping
- Market analysis data
- Neighborhood insights

## Performance Optimization

- **Code Splitting**: Route-based lazy loading
- **Image Optimization**: Responsive images with WebP
- **API Caching**: Request deduplication and caching
- **Virtual Scrolling**: Large dataset handling
- **Progressive Loading**: Skeleton screens and loading states

## Security Considerations

- **API Authentication**: Token-based authentication
- **Input Validation**: Client and server-side validation
- **XSS Protection**: Sanitized data rendering
- **CSRF Protection**: Request token validation
- **Secure Headers**: Content security policy implementation

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Ensure all tests pass
6. Submit a pull request

## License

This project is proprietary software for 4-plex investment research.