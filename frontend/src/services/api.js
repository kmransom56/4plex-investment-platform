import axios from 'axios';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_INTEGRATION_API || 'http://localhost:11060';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth tokens, logging, etc.
apiClient.interceptors.request.use(
  (config) => {
    // Add authentication token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Log API calls in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    }
    
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle common error scenarios
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    } else if (error.response?.status === 503) {
      // Service unavailable
      console.error('Service temporarily unavailable');
    }
    
    // Log errors in development
    if (process.env.NODE_ENV === 'development') {
      console.error('API Response Error:', error.response?.data || error.message);
    }
    
    return Promise.reject(error);
  }
);

// API Service Methods
export const apiService = {
  // Health Check
  async checkHealth() {
    const response = await apiClient.get('/api/unified/health');
    return response.data;
  },

  // Property Discovery
  async startDiscovery(counties = ['Fulton', 'DeKalb', 'Clayton', 'Cobb', 'Atlanta']) {
    const response = await apiClient.post('/api/unified/discovery/start', { counties });
    return response.data;
  },

  async getDiscoveryStatus(jobId) {
    const response = await apiClient.get(`/api/unified/discovery/${jobId}/status`);
    return response.data;
  },

  async getDiscoveryResults(params = {}) {
    const queryParams = new URLSearchParams(params);
    const response = await apiClient.get(`/api/unified/discovery/results?${queryParams}`);
    return response.data;
  },

  // Property Management
  async getProperties(params = {}) {
    const queryParams = new URLSearchParams(params);
    const response = await apiClient.get(`/api/unified/properties?${queryParams}`);
    return response.data;
  },

  async getProperty(propertyId) {
    const response = await apiClient.get(`/api/unified/properties/${propertyId}`);
    return response.data;
  },

  async triggerPropertyAnalysis(propertyId, priority = 'normal') {
    const response = await apiClient.post(`/api/unified/properties/${propertyId}/analyze`, { priority });
    return response.data;
  },

  async enrichPropertyData(propertyId, sources = ['propertyradar', 'realestate_api', 'attom']) {
    const response = await apiClient.post(`/api/unified/properties/${propertyId}/enrich`, { sources });
    return response.data;
  },

  // Analysis & Jobs
  async getAnalysisQueue(status = null) {
    const params = status ? { status } : {};
    const queryParams = new URLSearchParams(params);
    const response = await apiClient.get(`/api/unified/analysis/queue?${queryParams}`);
    return response.data;
  },

  async getAnalysisStatus(jobId) {
    const response = await apiClient.get(`/api/unified/analysis/${jobId}/status`);
    return response.data;
  },

  async getAnalysisResults(jobId) {
    const response = await apiClient.get(`/api/unified/analysis/${jobId}/results`);
    return response.data;
  },

  // Investment Opportunities
  async getInvestmentOpportunities(params = {}) {
    const queryParams = new URLSearchParams(params);
    const response = await apiClient.get(`/api/unified/opportunities?${queryParams}`);
    return response.data;
  },

  // Batch Operations
  async batchAnalyzeProperties(propertyIds, priority = 'normal') {
    const response = await apiClient.post('/api/unified/batch/analyze', {
      property_ids: propertyIds,
      priority
    });
    return response.data;
  },

  // System Integration
  async syncDataSources(sources = ['foreclosure_system', 'valuation_system']) {
    const response = await apiClient.post('/api/unified/integration/sync', { sources });
    return response.data;
  },

  async getIntegrationMetrics() {
    const response = await apiClient.get('/api/unified/integration/metrics');
    return response.data;
  },

  // Dashboard
  async getDashboardSummary() {
    const response = await apiClient.get('/api/unified/dashboard/summary');
    return response.data;
  },

  async getRecentActivity(hours = 24) {
    const response = await apiClient.get(`/api/unified/dashboard/activity?hours=${hours}`);
    return response.data;
  },

  // Export
  async exportProperties(format = 'json', filters = {}) {
    const queryParams = new URLSearchParams({
      format,
      filters: JSON.stringify(filters)
    });
    const response = await apiClient.get(`/api/unified/export/properties?${queryParams}`);
    return response.data;
  }
};

export default apiService;