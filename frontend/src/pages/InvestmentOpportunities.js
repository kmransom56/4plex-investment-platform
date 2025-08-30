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
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Avatar
} from '@mui/material';
import {
  TrendingUp,
  FilterList,
  Refresh,
  Download,
  OpenInNew,
  Star,
  Warning,
  CheckCircle,
  LocationOn,
  Home,
  Assessment
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { formatCurrency, formatPercentage, formatDate } from '../utils/formatters';
import { apiClient } from '../services/api';

const InvestmentOpportunities = () => {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Filters
  const [filters, setFilters] = useState({
    minScore: 70,
    maxResults: 50,
    county: '',
    maxPrice: ''
  });
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);

  useEffect(() => {
    loadOpportunities();
  }, [filters, page, rowsPerPage]);

  const loadOpportunities = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        min_score: filters.minScore.toString(),
        max_results: (rowsPerPage * (page + 1)).toString(),
        ...(filters.county && { county: filters.county }),
        ...(filters.maxPrice && { max_price: filters.maxPrice })
      });

      const response = await apiClient.get(`/api/unified/opportunities?${params}`);
      setOpportunities(response.data.opportunities || []);
    } catch (err) {
      setError('Failed to load investment opportunities');
      console.error('Opportunities error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setPage(0); // Reset to first page when filters change
  };

  const applyFilters = () => {
    setFilterDialogOpen(false);
    loadOpportunities();
  };

  const resetFilters = () => {
    setFilters({
      minScore: 70,
      maxResults: 50,
      county: '',
      maxPrice: ''
    });
    setPage(0);
  };

  const getRiskColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const getOpportunityRating = (score) => {
    if (score >= 90) return { label: 'Excellent', icon: <Star />, color: 'success' };
    if (score >= 80) return { label: 'Very Good', icon: <TrendingUp />, color: 'success' };
    if (score >= 70) return { label: 'Good', icon: <CheckCircle />, color: 'primary' };
    if (score >= 60) return { label: 'Fair', icon: <Warning />, color: 'warning' };
    return { label: 'Poor', icon: <Warning />, color: 'error' };
  };

  const OpportunityCard = ({ opportunity }) => {
    const rating = getOpportunityRating(opportunity.investment_score || 0);
    
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={8}>
              <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                <Box>
                  <Typography variant="h6" component="h3">
                    {opportunity.address}
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1} mt={1}>
                    <LocationOn fontSize="small" color="action" />
                    <Typography variant="body2" color="text.secondary">
                      {opportunity.city}, {opportunity.county} County, GA
                    </Typography>
                  </Box>
                </Box>
                <Box display="flex" gap={1}>
                  <Chip 
                    icon={rating.icon}
                    label={rating.label}
                    color={rating.color}
                    size="small"
                  />
                  <Chip 
                    label={`Score: ${opportunity.investment_score?.toFixed(1) || 'N/A'}`}
                    color={getRiskColor(opportunity.investment_score || 0)}
                    size="small"
                  />
                </Box>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    Estimated Value
                  </Typography>
                  <Typography variant="body1" fontWeight={600}>
                    {formatCurrency(opportunity.assessed_value || opportunity.market_value)}
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    Projected ROI
                  </Typography>
                  <Typography variant="body1" fontWeight={600}>
                    {formatPercentage(opportunity.irr)}
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    Monthly Cash Flow
                  </Typography>
                  <Typography variant="body1" fontWeight={600}>
                    {formatCurrency(opportunity.cash_flow)}
                  </Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="caption" color="text.secondary">
                    Cap Rate
                  </Typography>
                  <Typography variant="body1" fontWeight={600}>
                    {formatPercentage(opportunity.cap_rate)}
                  </Typography>
                </Grid>
              </Grid>

              <Box mt={2}>
                <Typography variant="caption" color="text.secondary">
                  Key Features
                </Typography>
                <Box display="flex" gap={1} mt={1}>
                  <Chip label={`${opportunity.units} Units`} size="small" variant="outlined" />
                  <Chip label={opportunity.foreclosure_status || 'Active'} size="small" variant="outlined" />
                  {opportunity.has_code_violations && (
                    <Chip label="Code Issues" size="small" color="warning" variant="outlined" />
                  )}
                </Box>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box display="flex" flexDirection="column" gap={2} alignItems="stretch">
                <Button
                  variant="contained"
                  fullWidth
                  onClick={() => navigate(`/property/${opportunity.id}`)}
                  endIcon={<OpenInNew />}
                >
                  View Details
                </Button>
                
                <Box display="flex" gap={1}>
                  <Button variant="outlined" size="small" fullWidth>
                    Schedule Inspection
                  </Button>
                  <Button variant="outlined" size="small" fullWidth>
                    Add to Watchlist
                  </Button>
                </Box>

                <Paper variant="outlined" sx={{ p: 1.5 }}>
                  <Typography variant="caption" color="text.secondary">
                    Discovered
                  </Typography>
                  <Typography variant="body2">
                    {formatDate(opportunity.discovered_at)}
                  </Typography>
                  
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                    Status
                  </Typography>
                  <Chip 
                    label={opportunity.discovery_status}
                    size="small"
                    color={opportunity.discovery_status === 'analyzed' ? 'success' : 'default'}
                  />
                </Paper>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" component="h1">
          Investment Opportunities
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<FilterList />}
            onClick={() => setFilterDialogOpen(true)}
          >
            Filters
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={loadOpportunities}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={() => {/* Implement export */}}
          >
            Export
          </Button>
        </Box>
      </Box>

      {/* Active Filters Summary */}
      {(filters.minScore > 70 || filters.county || filters.maxPrice) && (
        <Card sx={{ mb: 3, backgroundColor: 'primary.50' }}>
          <CardContent sx={{ py: 2 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" gap={1} alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  Active Filters:
                </Typography>
                {filters.minScore > 70 && (
                  <Chip label={`Min Score: ${filters.minScore}`} size="small" onDelete={() => handleFilterChange('minScore', 70)} />
                )}
                {filters.county && (
                  <Chip label={`County: ${filters.county}`} size="small" onDelete={() => handleFilterChange('county', '')} />
                )}
                {filters.maxPrice && (
                  <Chip label={`Max Price: ${formatCurrency(filters.maxPrice)}`} size="small" onDelete={() => handleFilterChange('maxPrice', '')} />
                )}
              </Box>
              <Button size="small" onClick={resetFilters}>
                Clear All
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Results Summary */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="text.secondary">
            Found {opportunities.length} investment opportunities
            {filters.minScore > 70 && ` with score ≥ ${filters.minScore}`}
          </Typography>
          <Box display="flex" alignItems="center" gap={2}>
            {loading && <CircularProgress size={20} />}
            <Typography variant="caption" color="text.secondary">
              Last updated: {new Date().toLocaleTimeString()}
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Opportunities List */}
      <Box>
        {opportunities.map((opportunity) => (
          <OpportunityCard key={opportunity.id} opportunity={opportunity} />
        ))}
        
        {opportunities.length === 0 && !loading && (
          <Paper sx={{ p: 8, textAlign: 'center' }}>
            <Avatar sx={{ mx: 'auto', mb: 2, bgcolor: 'grey.100' }}>
              <TrendingUp />
            </Avatar>
            <Typography variant="h6" gutterBottom>
              No opportunities found
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={3}>
              Try adjusting your filters or check back later for new discoveries.
            </Typography>
            <Button variant="outlined" onClick={() => navigate('/discovery')}>
              Start Discovery
            </Button>
          </Paper>
        )}
      </Box>

      {/* Pagination */}
      {opportunities.length > 0 && (
        <TablePagination
          component="div"
          count={-1} // Unknown total, using -1 for "more" behavior
          page={page}
          onPageChange={(event, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(event) => {
            setRowsPerPage(parseInt(event.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[10, 25, 50]}
        />
      )}

      {/* Filter Dialog */}
      <Dialog open={filterDialogOpen} onClose={() => setFilterDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Filter Investment Opportunities</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box>
              <Typography gutterBottom>Minimum Investment Score: {filters.minScore}</Typography>
              <Slider
                value={filters.minScore}
                onChange={(e, value) => handleFilterChange('minScore', value)}
                min={0}
                max={100}
                step={5}
                marks
                valueLabelDisplay="auto"
              />
            </Box>

            <FormControl fullWidth>
              <InputLabel>County</InputLabel>
              <Select
                value={filters.county}
                label="County"
                onChange={(e) => handleFilterChange('county', e.target.value)}
              >
                <MenuItem value="">All Counties</MenuItem>
                <MenuItem value="Fulton">Fulton</MenuItem>
                <MenuItem value="DeKalb">DeKalb</MenuItem>
                <MenuItem value="Clayton">Clayton</MenuItem>
                <MenuItem value="Cobb">Cobb</MenuItem>
                <MenuItem value="Atlanta">Atlanta</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Maximum Price"
              type="number"
              value={filters.maxPrice}
              onChange={(e) => handleFilterChange('maxPrice', e.target.value)}
              InputProps={{
                startAdornment: '$'
              }}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFilterDialogOpen(false)}>Cancel</Button>
          <Button onClick={resetFilters}>Reset</Button>
          <Button onClick={applyFilters} variant="contained">Apply Filters</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default InvestmentOpportunities;