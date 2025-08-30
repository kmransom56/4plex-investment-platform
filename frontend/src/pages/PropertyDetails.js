import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Chip,
  Divider,
  Paper,
  LinearProgress,
  Alert,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress
} from '@mui/material';
import {
  Home,
  LocationOn,
  AttachMoney,
  Assessment,
  Warning,
  CheckCircle,
  TrendingUp,
  Timeline,
  Download,
  Share,
  Edit,
  Refresh,
  Schedule,
  Favorite,
  FavoriteBorder
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { formatCurrency, formatPercentage, formatDate, formatAddress, formatBedsBaths } from '../utils/formatters';
import { apiClient } from '../services/api';

const PropertyDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [favorited, setFavorited] = useState(false);
  const [noteDialogOpen, setNoteDialogOpen] = useState(false);
  const [note, setNote] = useState('');

  useEffect(() => {
    if (id) {
      loadPropertyDetails();
    }
  }, [id]);

  const loadPropertyDetails = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(`/api/unified/properties/${id}`);
      setProperty(response.data);
      
      // Try to load latest analysis
      if (response.data.analyzed_at) {
        // Implementation would load analysis data
      }
    } catch (err) {
      setError('Failed to load property details');
      console.error('Property details error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeProperty = async () => {
    setAnalyzing(true);
    try {
      await apiClient.post(`/api/unified/properties/${id}/analyze`, { priority: 'high' });
      // Refresh property data
      await loadPropertyDetails();
    } catch (err) {
      console.error('Analysis error:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleEnrichData = async () => {
    try {
      await apiClient.post(`/api/unified/properties/${id}/enrich`);
      // Refresh property data
      await loadPropertyDetails();
    } catch (err) {
      console.error('Enrichment error:', err);
    }
  };

  const getRiskColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const MetricCard = ({ title, value, subtitle, icon, color = 'primary' }) => (
    <Paper sx={{ p: 2, textAlign: 'center', height: '100%' }}>
      <Avatar sx={{ mx: 'auto', mb: 1, bgcolor: `${color}.light` }}>
        {icon}
      </Avatar>
      <Typography variant="h5" color={color} gutterBottom>
        {value}
      </Typography>
      <Typography variant="body2" color="text.primary">
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="caption" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </Paper>
  );

  if (loading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={loadPropertyDetails}>
            Retry
          </Button>
        }>
          {error}
        </Alert>
      </Container>
    );
  }

  if (!property) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="info">
          Property not found
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="start" mb={4}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            {property.address}
          </Typography>
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <LocationOn fontSize="small" color="action" />
            <Typography variant="body1" color="text.secondary">
              {formatAddress(property.address, property.city, property.state, property.zip_code)}
            </Typography>
          </Box>
          <Box display="flex" gap={1}>
            <Chip label={property.property_type} variant="outlined" />
            <Chip label={`${property.units} Units`} variant="outlined" />
            <Chip 
              label={property.foreclosure_status || 'Active'}
              color={property.foreclosure_status ? 'warning' : 'success'}
              variant="outlined"
            />
          </Box>
        </Box>

        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={favorited ? <Favorite /> : <FavoriteBorder />}
            onClick={() => setFavorited(!favorited)}
          >
            {favorited ? 'Favorited' : 'Add to Favorites'}
          </Button>
          <Button variant="outlined" startIcon={<Share />}>
            Share
          </Button>
          <Button variant="outlined" startIcon={<Download />}>
            Export
          </Button>
          <Button
            variant="contained"
            startIcon={<Schedule />}
            disabled={analyzing}
          >
            Schedule Inspection
          </Button>
        </Box>
      </Box>

      {/* Investment Score Banner */}
      {property.investment_score && (
        <Card sx={{ mb: 4, bgcolor: getRiskColor(property.investment_score) + '.50' }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box display="flex" alignItems="center" gap={2}>
                <Avatar sx={{ bgcolor: getRiskColor(property.investment_score) + '.main' }}>
                  <Assessment />
                </Avatar>
                <Box>
                  <Typography variant="h5">
                    Investment Score: {property.investment_score.toFixed(1)}/100
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {property.investment_score >= 80 ? 'Excellent' : 
                     property.investment_score >= 70 ? 'Very Good' :
                     property.investment_score >= 60 ? 'Good' : 
                     property.investment_score >= 40 ? 'Fair' : 'Poor'} investment opportunity
                  </Typography>
                </Box>
              </Box>
              
              <Box display="flex" gap={2}>
                {!property.analyzed_at && (
                  <Button
                    variant="contained"
                    startIcon={analyzing ? <CircularProgress size={16} /> : <Assessment />}
                    onClick={handleAnalyzeProperty}
                    disabled={analyzing}
                  >
                    {analyzing ? 'Analyzing...' : 'Run Full Analysis'}
                  </Button>
                )}
                <Button variant="outlined" startIcon={<Refresh />} onClick={handleEnrichData}>
                  Enrich Data
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      <Grid container spacing={3}>
        {/* Key Metrics */}
        <Grid item xs={12} md={8}>
          <Grid container spacing={2} mb={3}>
            <Grid item xs={6} md={3}>
              <MetricCard
                title="Assessed Value"
                value={formatCurrency(property.assessed_value)}
                subtitle="County Assessment"
                icon={<AttachMoney />}
                color="success"
              />
            </Grid>
            <Grid item xs={6} md={3}>
              <MetricCard
                title="Amount Owed"
                value={formatCurrency(property.amount_owed)}
                subtitle="Outstanding Debt"
                icon={<Warning />}
                color="error"
              />
            </Grid>
            <Grid item xs={6} md={3}>
              <MetricCard
                title="Cap Rate"
                value={formatPercentage(property.cap_rate)}
                subtitle="Annual Return"
                icon={<TrendingUp />}
                color="primary"
              />
            </Grid>
            <Grid item xs={6} md={3}>
              <MetricCard
                title="Cash Flow"
                value={formatCurrency(property.cash_flow)}
                subtitle="Monthly"
                icon={<Timeline />}
                color="info"
              />
            </Grid>
          </Grid>

          {/* Property Information */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Property Information
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <List dense>
                    <ListItem>
                      <ListItemIcon><Home /></ListItemIcon>
                      <ListItemText 
                        primary="Property Type" 
                        secondary={property.property_type}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Home /></ListItemIcon>
                      <ListItemText 
                        primary="Units" 
                        secondary={property.units}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Home /></ListItemIcon>
                      <ListItemText 
                        primary="Bedrooms/Bathrooms" 
                        secondary={formatBedsBaths(property.bedrooms, property.bathrooms)}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Home /></ListItemIcon>
                      <ListItemText 
                        primary="Square Footage" 
                        secondary={property.square_footage ? `${property.square_footage.toLocaleString()} sq ft` : 'N/A'}
                      />
                    </ListItem>
                  </List>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <List dense>
                    <ListItem>
                      <ListItemIcon><LocationOn /></ListItemIcon>
                      <ListItemText 
                        primary="County" 
                        secondary={property.county}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><LocationOn /></ListItemIcon>
                      <ListItemText 
                        primary="Parcel Number" 
                        secondary={property.parcel_number || 'N/A'}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Home /></ListItemIcon>
                      <ListItemText 
                        primary="Year Built" 
                        secondary={property.year_built || 'N/A'}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><LocationOn /></ListItemIcon>
                      <ListItemText 
                        primary="Lot Size" 
                        secondary={property.lot_size ? `${property.lot_size} acres` : 'N/A'}
                      />
                    </ListItem>
                  </List>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Foreclosure Information */}
          {property.foreclosure_status && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Foreclosure Information
                </Typography>
                <Divider sx={{ mb: 2 }} />
                
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Status</Typography>
                      <Chip label={property.foreclosure_status} color="warning" />
                    </Box>
                    
                    {property.sale_date && (
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Sale Date</Typography>
                        <Typography variant="body1">{formatDate(property.sale_date)}</Typography>
                      </Box>
                    )}
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    {property.auction_minimum_bid && (
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Minimum Bid</Typography>
                        <Typography variant="body1">{formatCurrency(property.auction_minimum_bid)}</Typography>
                      </Box>
                    )}
                    
                    {property.redemption_period && (
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Redemption Period</Typography>
                        <Typography variant="body1">{property.redemption_period}</Typography>
                      </Box>
                    )}
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          )}

          {/* Code Violations */}
          {property.has_code_violations && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                  <Warning color="warning" />
                  <Typography variant="h6">
                    Code Violations ({property.violation_count})
                  </Typography>
                </Box>
                <Divider sx={{ mb: 2 }} />
                
                {property.violation_types && property.violation_types.map((violation, index) => (
                  <Chip key={index} label={violation} color="warning" variant="outlined" sx={{ mr: 1, mb: 1 }} />
                ))}
              </CardContent>
            </Card>
          )}
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Financial Summary */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Financial Summary
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Assessed Value</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {formatCurrency(property.assessed_value)}
                </Typography>
              </Box>
              
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Market Value</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {formatCurrency(property.market_value)}
                </Typography>
              </Box>
              
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Amount Owed</Typography>
                <Typography variant="body2" fontWeight={600} color="error.main">
                  {formatCurrency(property.amount_owed)}
                </Typography>
              </Box>
              
              <Divider sx={{ my: 2 }} />
              
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Gross Income</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {formatCurrency(property.gross_income)}
                </Typography>
              </Box>
              
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Operating Expenses</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {formatCurrency(property.operating_expenses)}
                </Typography>
              </Box>
              
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">NOI</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {formatCurrency(property.noi)}
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {/* Processing Status */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Processing Status
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <CheckCircle color="success" />
                <Box>
                  <Typography variant="body2">Discovery Status</Typography>
                  <Chip label={property.discovery_status} size="small" />
                </Box>
              </Box>
              
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Discovered: {formatDate(property.discovered_at)}
                </Typography>
              </Box>
              
              {property.analyzed_at && (
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">
                    Last Analyzed: {formatDate(property.analyzed_at)}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Actions
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Box display="flex" flexDirection="column" gap={2}>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<Edit />}
                  onClick={() => setNoteDialogOpen(true)}
                >
                  Add Notes
                </Button>
                
                <Button variant="outlined" fullWidth startIcon={<Schedule />}>
                  Schedule Viewing
                </Button>
                
                <Button variant="outlined" fullWidth startIcon={<Download />}>
                  Download Report
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Notes Dialog */}
      <Dialog open={noteDialogOpen} onClose={() => setNoteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Property Notes</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Notes"
            multiline
            rows={4}
            fullWidth
            variant="outlined"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNoteDialogOpen(false)}>Cancel</Button>
          <Button onClick={() => setNoteDialogOpen(false)} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default PropertyDetails;