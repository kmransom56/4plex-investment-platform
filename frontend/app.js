/**
 * 4-Plex Investment Platform - Frontend Application Logic
 * Connects to real backend API endpoints for live functionality
 */

class InvestmentPlatform {
    constructor() {
        this.apiBase = 'http://localhost:11050/api';
        this.activeJobs = new Map();
        this.properties = [];
        this.init();
    }

    async init() {
        await this.loadDashboardMetrics();
        await this.loadRecentActivity();
        this.startPeriodicUpdates();
        console.log('4-Plex Investment Platform initialized');
    }

    // API Helper Methods
    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            if (data) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(`${this.apiBase}${endpoint}`, options);
            
            if (!response.ok) {
                throw new Error(`API call failed: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API call error:', error);
            throw error;
        }
    }

    // Dashboard Metrics
    async loadDashboardMetrics() {
        try {
            const metrics = await this.apiCall('/metrics');
            this.updateMetricsDisplay(metrics);
        } catch (error) {
            console.error('Failed to load metrics:', error);
        }
    }

    updateMetricsDisplay(metrics) {
        const elements = {
            'propertiesCount': metrics.properties_analyzed,
            'opportunitiesCount': metrics.investment_opportunities,
            'avgROI': `${metrics.average_roi}%`,
            'countiesActive': metrics.counties_active
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        console.log('Dashboard metrics updated:', metrics);
    }

    // Property Discovery
    async startPropertyDiscovery() {
        try {
            this.showLoadingState('Starting multi-agent property discovery...');

            const request = {
                counties: ["Fulton", "DeKalb", "Gwinnett", "Cobb", "Clayton", "Cherokee"],
                property_types: ["4-plex", "quadplex", "fourplex"],
                max_results: 50
            };

            const response = await this.apiCall('/discover-properties', 'POST', request);
            
            this.showJobProgress(response.job_id, 'Property Discovery');
            this.trackJob(response.job_id);

            return response;
        } catch (error) {
            this.showError('Property Discovery Failed', error.message);
        }
    }

    // Property Analysis
    async analyzeProperty(propertyId = null) {
        try {
            // If no property ID provided, use a demo property or prompt user
            if (!propertyId) {
                if (this.properties.length === 0) {
                    alert('No properties available for analysis. Please discover properties first.');
                    return;
                }
                propertyId = this.properties[0].id; // Use first available property
            }

            this.showLoadingState('Starting AI-powered investment analysis...');

            const request = {
                property_id: propertyId,
                analysis_type: "investment",
                include_projections: true
            };

            const response = await this.apiCall('/analyze-property', 'POST', request);
            
            this.showJobProgress(response.job_id, 'Investment Analysis');
            this.trackJob(response.job_id);

            return response;
        } catch (error) {
            this.showError('Property Analysis Failed', error.message);
        }
    }

    // Report Generation
    async generateReport(propertyId = null) {
        try {
            if (!propertyId && this.properties.length === 0) {
                alert('No properties available for report generation. Please discover properties first.');
                return;
            }

            propertyId = propertyId || this.properties[0].id;

            this.showLoadingState('Creating comprehensive investment report...');

            const response = await this.apiCall(`/generate-report/${propertyId}`, 'POST');
            
            this.showJobProgress(response.job_id, 'Report Generation');
            this.trackJob(response.job_id);

            return response;
        } catch (error) {
            this.showError('Report Generation Failed', error.message);
        }
    }

    // Portfolio Management
    async loadPortfolio() {
        try {
            const response = await this.apiCall('/properties?min_score=70');
            this.properties = response.properties;
            
            this.showPortfolioModal(response);
            return response;
        } catch (error) {
            this.showError('Portfolio Load Failed', error.message);
        }
    }

    // Job Tracking
    trackJob(jobId) {
        if (this.activeJobs.has(jobId)) return;

        this.activeJobs.set(jobId, {
            id: jobId,
            startTime: Date.now(),
            interval: null
        });

        const interval = setInterval(async () => {
            await this.checkJobStatus(jobId);
        }, 2000);

        this.activeJobs.get(jobId).interval = interval;
    }

    async checkJobStatus(jobId) {
        try {
            const status = await this.apiCall(`/jobs/${jobId}/status`);
            
            this.updateJobProgress(jobId, status);

            if (status.status === 'completed' || status.status === 'failed') {
                this.completeJob(jobId, status);
            }
        } catch (error) {
            console.error(`Failed to check job ${jobId} status:`, error);
            this.completeJob(jobId, { status: 'error', message: error.message });
        }
    }

    updateJobProgress(jobId, status) {
        // Update progress in any open modals or status displays
        const progressElement = document.getElementById(`job-progress-${jobId}`);
        if (progressElement) {
            progressElement.style.width = `${status.progress}%`;
        }

        const messageElement = document.getElementById(`job-message-${jobId}`);
        if (messageElement) {
            messageElement.textContent = status.message;
        }
    }

    completeJob(jobId, status) {
        const job = this.activeJobs.get(jobId);
        if (job && job.interval) {
            clearInterval(job.interval);
        }
        this.activeJobs.delete(jobId);

        if (status.status === 'completed') {
            this.showJobComplete(jobId, status);
            // Refresh dashboard metrics
            this.loadDashboardMetrics();
            this.loadRecentActivity();
        } else {
            this.showJobError(jobId, status);
        }
    }

    // Recent Activity
    async loadRecentActivity() {
        try {
            const response = await this.apiCall('/activity');
            this.updateActivityDisplay(response.activities);
        } catch (error) {
            console.error('Failed to load recent activity:', error);
        }
    }

    updateActivityDisplay(activities) {
        const activityContainer = document.querySelector('.activity-timeline');
        if (!activityContainer) return;

        activityContainer.innerHTML = activities.map(activity => `
            <div class="flex items-start space-x-4 mb-4">
                <div class="w-2 h-2 ${this.getActivityColor(activity.type)} rounded-full mt-2 flex-shrink-0"></div>
                <div class="flex-1 space-y-1">
                    <p class="text-sm font-medium">${activity.message}</p>
                    <p class="text-sm text-muted-foreground">${activity.details} • ${this.formatTime(activity.timestamp)}</p>
                </div>
            </div>
        `).join('');
    }

    getActivityColor(type) {
        const colors = {
            'discovery': 'bg-primary',
            'analysis': 'bg-green-500',
            'report': 'bg-blue-500',
            'error': 'bg-red-500'
        };
        return colors[type] || 'bg-gray-500';
    }

    formatTime(timestamp) {
        const time = new Date(timestamp);
        const now = new Date();
        const diff = now - time;
        
        if (diff < 60000) return 'just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
        return `${Math.floor(diff / 86400000)} days ago`;
    }

    // UI Helper Methods
    showLoadingState(message) {
        // Create and show loading modal
        const modal = document.createElement('div');
        modal.id = 'loading-modal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <div class="flex items-center space-x-3">
                    <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                    <span class="text-lg font-medium">${message}</span>
                </div>
                <div class="mt-4">
                    <div class="bg-gray-200 rounded-full h-2">
                        <div class="bg-primary h-2 rounded-full transition-all duration-300" style="width: 0%" id="loading-progress"></div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    showJobProgress(jobId, jobName) {
        this.hideLoadingState();
        
        const modal = document.createElement('div');
        modal.id = `job-modal-${jobId}`;
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <h3 class="text-lg font-semibold mb-4">${jobName}</h3>
                <div class="space-y-4">
                    <div class="bg-gray-200 rounded-full h-3">
                        <div class="bg-primary h-3 rounded-full transition-all duration-500" style="width: 0%" id="job-progress-${jobId}"></div>
                    </div>
                    <p class="text-sm text-gray-600" id="job-message-${jobId}">Starting...</p>
                </div>
                <button onclick="window.platform.closeJobModal('${jobId}')" class="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 transition-colors">
                    Run in Background
                </button>
            </div>
        `;
        document.body.appendChild(modal);
    }

    showJobComplete(jobId, status) {
        const modal = document.getElementById(`job-modal-${jobId}`);
        if (modal) {
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                    <div class="text-center">
                        <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                            <svg class="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                        <h3 class="text-lg font-semibold text-green-800 mb-2">Task Complete!</h3>
                        <p class="text-sm text-gray-600 mb-4">${status.message}</p>
                        ${status.results_count ? `<p class="text-sm text-primary font-medium">Found ${status.results_count} results</p>` : ''}
                    </div>
                    <button onclick="window.platform.closeJobModal('${jobId}')" class="w-full mt-4 px-4 py-2 bg-primary text-white rounded hover:bg-primary/90 transition-colors">
                        Close
                    </button>
                </div>
            `;
            
            // Auto-close after 3 seconds
            setTimeout(() => this.closeJobModal(jobId), 3000);
        }
    }

    showJobError(jobId, status) {
        const modal = document.getElementById(`job-modal-${jobId}`);
        if (modal) {
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                    <div class="text-center">
                        <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                            <svg class="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z"></path>
                            </svg>
                        </div>
                        <h3 class="text-lg font-semibold text-red-800 mb-2">Task Failed</h3>
                        <p class="text-sm text-gray-600 mb-4">${status.message}</p>
                    </div>
                    <button onclick="window.platform.closeJobModal('${jobId}')" class="w-full mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors">
                        Close
                    </button>
                </div>
            `;
        }
    }

    showPortfolioModal(portfolioData) {
        const modal = document.createElement('div');
        modal.id = 'portfolio-modal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[80vh] overflow-y-auto">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-semibold">Investment Portfolio</h3>
                    <button onclick="window.platform.closePortfolioModal()" class="text-gray-500 hover:text-gray-700">
                        <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    ${portfolioData.properties.map(property => `
                        <div class="border rounded-lg p-4 hover:shadow-lg transition-shadow">
                            <div class="flex items-center justify-between mb-2">
                                <span class="text-sm font-medium text-primary">${property.county} County</span>
                                <span class="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">${property.investment_score}%</span>
                            </div>
                            <p class="font-medium mb-1">${property.address}</p>
                            <p class="text-sm text-gray-600 mb-2">${property.city}, ${property.state} ${property.zip_code}</p>
                            <div class="space-y-1 text-sm">
                                <div class="flex justify-between">
                                    <span>Est. Value:</span>
                                    <span class="font-medium">$${property.estimated_value.toLocaleString()}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>ROI:</span>
                                    <span class="font-medium text-green-600">${property.roi_estimate}%</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Stage:</span>
                                    <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">${property.foreclosure_stage}</span>
                                </div>
                            </div>
                            <button onclick="window.platform.analyzeProperty('${property.id}')" class="w-full mt-3 px-3 py-2 bg-primary text-white text-sm rounded hover:bg-primary/90 transition-colors">
                                Analyze Property
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    showError(title, message) {
        alert(`${title}\n\n${message}`);
    }

    // Modal Management
    closeJobModal(jobId) {
        const modal = document.getElementById(`job-modal-${jobId}`);
        if (modal) {
            modal.remove();
        }
    }

    closePortfolioModal() {
        const modal = document.getElementById('portfolio-modal');
        if (modal) {
            modal.remove();
        }
    }

    hideLoadingState() {
        const modal = document.getElementById('loading-modal');
        if (modal) {
            modal.remove();
        }
    }

    // Periodic Updates
    startPeriodicUpdates() {
        // Update metrics every 30 seconds
        setInterval(() => {
            this.loadDashboardMetrics();
        }, 30000);

        // Update activity every 60 seconds
        setInterval(() => {
            this.loadRecentActivity();
        }, 60000);
    }
}

// Global platform instance
window.platform = new InvestmentPlatform();

// Global functions for onclick handlers
window.startForeclosureDiscovery = () => window.platform.startPropertyDiscovery();
window.analyzeProperty = (propertyId) => window.platform.analyzeProperty(propertyId);
window.generateReport = (propertyId) => window.platform.generateReport(propertyId);
window.viewPortfolio = () => window.platform.loadPortfolio();