import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Chip,
  Button,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Avatar,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  TrendingUp,
  Home,
  Assessment,
  Warning,
  CheckCircle,
  Error,
  Refresh,
  OpenInNew,
  LocationOn,
  AttachMoney,
  Timeline
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { formatCurrency, formatPercentage, formatDate } from '../utils/formatters';
import { apiClient } from '../services/api';

const Dashboard = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [recentActivity, setRecentActivity] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [summaryRes, activityRes, opportunitiesRes] = await Promise.all([
        apiClient.get('/api/unified/dashboard/summary'),
        apiClient.get('/api/unified/dashboard/activity?hours=24'),
        apiClient.get('/api/unified/opportunities?min_score=75&max_results=5')
      ]);

      setSummary(summaryRes.data);
      setRecentActivity(activityRes.data);
      setOpportunities(opportunitiesRes.data.opportunities || []);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  const MetricCard = ({ title, value, subtitle, icon, color = 'primary', progress = null, action = null }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box>
            <Typography variant="h4" color={color}>
              {value}
            </Typography>
            <Typography variant="h6" color="text.primary">
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Avatar sx={{ bgcolor: `${color}.light` }}>
            {icon}
          </Avatar>
        </Box>
        {progress !== null && (
          <LinearProgress 
            variant="determinate" 
            value={progress} 
            sx={{ mb: 1 }}
            color={color}
          />
        )}
        {action && action}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
          <Box textAlign="center">
            <LinearProgress sx={{ mb: 2, width: 200 }} />
            <Typography variant="body1">Loading dashboard...</Typography>
          </Box>
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert 
          severity="error" 
          action={
            <Button color="inherit" size="small" onClick={loadDashboardData}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="between" alignItems="center" mb={4}>
        <Typography variant="h4" component="h1">
          Investment Dashboard
        </Typography>
        <Box display="flex" gap={2}>
          <Tooltip title="Last updated: just now">
            <IconButton onClick={loadDashboardData}>
              <Refresh />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Key Metrics */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Properties"
            value={summary?.total_properties || 0}
            subtitle="Discovered across Georgia"
            icon={<Home />}
            color="primary"
            action={
              <Button size="small" onClick={() => navigate('/discovery')}>
                View All
              </Button>
            }
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="High-Value Opportunities"
            value={summary?.high_value_opportunities || 0}
            subtitle="Score ≥ 70"
            icon={<TrendingUp />}
            color="success"
            action={
              <Button size="small" onClick={() => navigate('/opportunities')}>
                Explore
              </Button>
            }
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Avg Investment Score"
            value={summary?.average_investment_score || 0}
            subtitle="Overall portfolio quality"
            icon={<Assessment />}
            color="info"
            progress={summary?.average_investment_score || 0}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Active Analysis"
            value={recentActivity?.recent_jobs?.length || 0}
            subtitle="Last 24 hours"
            icon={<Timeline />}
            color="warning"
            action={
              <Button size="small" onClick={() => navigate('/analysis')}>
                View Queue
              </Button>
            }
          />
        </Grid>
      </Grid>

      {/* County Distribution */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Properties by County
              </Typography>
              <Box>
                {summary?.county_distribution && Object.entries(summary.county_distribution).map(([county, count]) => (
                  <Box key={county} display="flex" justifyContent="space-between" alignItems="center" py={1}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <LocationOn fontSize="small" color="action" />
                      <Typography>{county} County</Typography>
                    </Box>
                    <Chip label={count} variant="outlined" size="small" />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Processing Status
              </Typography>
              <Box>
                {summary?.status_distribution && Object.entries(summary.status_distribution).map(([status, count]) => (
                  <Box key={status} display="flex" justifyContent="space-between" alignItems="center" py={1}>
                    <Box display="flex" alignItems="center" gap={1}>
                      {status === 'completed' && <CheckCircle fontSize="small" color="success" />}
                      {status === 'failed' && <Error fontSize="small" color="error" />}
                      {status === 'pending' && <Warning fontSize="small" color="warning" />}
                      <Typography sx={{ textTransform: 'capitalize' }}>
                        {status.replace('_', ' ')}
                      </Typography>
                    </Box>
                    <Chip 
                      label={count} 
                      variant="outlined" 
                      size="small"
                      color={status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'default'}
                    />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Top Investment Opportunities */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6">
                  Top Investment Opportunities
                </Typography>
                <Button 
                  variant="outlined" 
                  onClick={() => navigate('/opportunities')}
                  endIcon={<OpenInNew />}
                >
                  View All
                </Button>
              </Box>

              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Property</TableCell>
                      <TableCell>County</TableCell>
                      <TableCell align="right">Investment Score</TableCell>
                      <TableCell align="right">Est. Value</TableCell>
                      <TableCell align="right">Projected ROI</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {opportunities.map((opportunity) => (
                      <TableRow key={opportunity.id} hover>
                        <TableCell>
                          <Box>
                            <Typography variant="body2" fontWeight={600}>
                              {opportunity.address}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {opportunity.property_type} • {opportunity.units} units
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip label={opportunity.county} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell align="right">
                          <Chip 
                            label={opportunity.investment_score?.toFixed(1) || 'N/A'}
                            color="success"
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(opportunity.assessed_value || opportunity.market_value)}
                        </TableCell>
                        <TableCell align="right">
                          {formatPercentage(opportunity.irr)}
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={opportunity.discovery_status}
                            size="small"
                            color={opportunity.discovery_status === 'analyzed' ? 'success' : 'warning'}
                          />
                        </TableCell>
                        <TableCell>
                          <IconButton 
                            size="small" 
                            onClick={() => navigate(`/property/${opportunity.id}`)}
                          >
                            <OpenInNew fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {opportunities.length === 0 && (
                <Box textAlign="center" py={4}>
                  <Typography color="text.secondary">
                    No high-scoring opportunities found. Check back soon!
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Activity */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Activity (Last 24 Hours)
              </Typography>

              <Box mb={3}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  New Discoveries: {recentActivity?.recent_discoveries?.length || 0} properties
                </Typography>
                <Typography variant="subtitle2" color="text.secondary">
                  Analyses Completed: {recentActivity?.recent_analyses?.length || 0} properties
                </Typography>
              </Box>

              {recentActivity?.recent_discoveries?.slice(0, 3).map((discovery, index) => (
                <Box key={discovery.id} display="flex" alignItems="center" py={2} borderBottom="1px solid #f0f0f0">
                  <Avatar sx={{ bgcolor: 'primary.light', mr: 2 }}>
                    <Home />
                  </Avatar>
                  <Box flexGrow={1}>
                    <Typography variant="body2" fontWeight={600}>
                      New 4-plex discovered: {discovery.address}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {discovery.county} County • Score: {discovery.investment_score || 'Pending'} • {formatDate(discovery.discovered_at)}
                    </Typography>
                  </Box>
                  <Button 
                    size="small" 
                    variant="outlined"
                    onClick={() => navigate(`/property/${discovery.id}`)}
                  >
                    View
                  </Button>
                </Box>
              ))}

              {(!recentActivity?.recent_discoveries || recentActivity.recent_discoveries.length === 0) && (
                <Box textAlign="center" py={4}>
                  <Typography color="text.secondary">
                    No recent activity to display.
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Dashboard;