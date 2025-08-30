/**
 * Utility functions for formatting data in the UI
 */

export const formatCurrency = (value, options = {}) => {
  if (value == null || value === '' || isNaN(value)) {
    return 'N/A';
  }

  const defaultOptions = {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
    ...options
  };

  return new Intl.NumberFormat('en-US', defaultOptions).format(value);
};

export const formatPercentage = (value, options = {}) => {
  if (value == null || value === '' || isNaN(value)) {
    return 'N/A';
  }

  const defaultOptions = {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
    ...options
  };

  return new Intl.NumberFormat('en-US', defaultOptions).format(value);
};

export const formatNumber = (value, options = {}) => {
  if (value == null || value === '' || isNaN(value)) {
    return 'N/A';
  }

  const defaultOptions = {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
    ...options
  };

  return new Intl.NumberFormat('en-US', defaultOptions).format(value);
};

export const formatDate = (dateString, options = {}) => {
  if (!dateString) {
    return 'N/A';
  }

  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options
  };

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }
    return date.toLocaleDateString('en-US', defaultOptions);
  } catch (error) {
    return 'Invalid Date';
  }
};

export const formatDateTime = (dateString, options = {}) => {
  if (!dateString) {
    return 'N/A';
  }

  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...options
  };

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }
    return date.toLocaleString('en-US', defaultOptions);
  } catch (error) {
    return 'Invalid Date';
  }
};

export const formatRelativeTime = (dateString) => {
  if (!dateString) {
    return 'N/A';
  }

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }

    const now = new Date();
    const diffInMilliseconds = now.getTime() - date.getTime();
    const diffInSeconds = Math.floor(diffInMilliseconds / 1000);
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    const diffInHours = Math.floor(diffInMinutes / 60);
    const diffInDays = Math.floor(diffInHours / 24);

    if (diffInSeconds < 60) {
      return 'Just now';
    } else if (diffInMinutes < 60) {
      return `${diffInMinutes} minute${diffInMinutes !== 1 ? 's' : ''} ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours} hour${diffInHours !== 1 ? 's' : ''} ago`;
    } else if (diffInDays < 7) {
      return `${diffInDays} day${diffInDays !== 1 ? 's' : ''} ago`;
    } else {
      return formatDate(dateString);
    }
  } catch (error) {
    return 'Invalid Date';
  }
};

export const formatAddress = (address, city, state = 'GA', zipCode) => {
  const parts = [address];
  
  if (city) {
    parts.push(city);
  }
  
  if (state) {
    parts.push(state);
  }
  
  if (zipCode) {
    parts.push(zipCode);
  }
  
  return parts.filter(Boolean).join(', ');
};

export const formatPhoneNumber = (phoneNumber) => {
  if (!phoneNumber) {
    return 'N/A';
  }

  // Remove all non-digit characters
  const digits = phoneNumber.replace(/\D/g, '');
  
  // Format as (XXX) XXX-XXXX if we have 10 digits
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  
  // Return original if not 10 digits
  return phoneNumber;
};

export const formatSquareFootage = (sqft) => {
  if (sqft == null || sqft === '' || isNaN(sqft)) {
    return 'N/A';
  }
  
  return `${formatNumber(sqft)} sq ft`;
};

export const formatLotSize = (acres) => {
  if (acres == null || acres === '' || isNaN(acres)) {
    return 'N/A';
  }
  
  if (acres < 1) {
    // Convert to square feet if less than an acre
    const sqft = acres * 43560;
    return `${formatNumber(sqft)} sq ft`;
  }
  
  return `${formatNumber(acres, { minimumFractionDigits: 2 })} acres`;
};

export const formatBedsBaths = (beds, baths) => {
  const bedsStr = beds != null ? `${beds} bed${beds !== 1 ? 's' : ''}` : '';
  const bathsStr = baths != null ? `${baths} bath${baths !== 1 ? 's' : ''}` : '';
  
  if (bedsStr && bathsStr) {
    return `${bedsStr}, ${bathsStr}`;
  } else if (bedsStr) {
    return bedsStr;
  } else if (bathsStr) {
    return bathsStr;
  }
  
  return 'N/A';
};

export const formatPropertyType = (type) => {
  if (!type) return 'N/A';
  
  const typeMap = {
    '4plex': '4-Plex',
    'fourplex': '4-Plex',
    'multifamily': 'Multifamily',
    'commercial': 'Commercial',
    'mixed_use': 'Mixed Use',
    'other': 'Other'
  };
  
  return typeMap[type.toLowerCase()] || type;
};

export const formatForeclosureStatus = (status) => {
  if (!status || status === 'none') return 'Active';
  
  const statusMap = {
    'pre_foreclosure': 'Pre-Foreclosure',
    'notice_of_default': 'Notice of Default',
    'lis_pendens': 'Lis Pendens',
    'auction_scheduled': 'Auction Scheduled',
    'auction_completed': 'Auction Completed',
    'reo': 'REO',
    'tax_sale': 'Tax Sale'
  };
  
  return statusMap[status.toLowerCase()] || status;
};

export const formatProcessingStatus = (status) => {
  if (!status) return 'Unknown';
  
  const statusMap = {
    'discovered': 'Discovered',
    'validated': 'Validated',
    'enriched': 'Enriched',
    'analyzed': 'Analyzed',
    'completed': 'Completed',
    'failed': 'Failed'
  };
  
  return statusMap[status.toLowerCase()] || status;
};

export const formatRiskLevel = (risk) => {
  if (!risk) return 'Unknown';
  
  const riskMap = {
    'low': 'Low Risk',
    'medium': 'Medium Risk',
    'high': 'High Risk',
    'critical': 'Critical Risk'
  };
  
  return riskMap[risk.toLowerCase()] || risk;
};

export const formatCapRate = (capRate) => {
  return formatPercentage(capRate, { minimumFractionDigits: 1, maximumFractionDigits: 2 });
};

export const formatIRR = (irr) => {
  return formatPercentage(irr, { minimumFractionDigits: 1, maximumFractionDigits: 2 });
};

export const formatCashOnCash = (coc) => {
  return formatPercentage(coc, { minimumFractionDigits: 1, maximumFractionDigits: 2 });
};

export const formatMonthlyRent = (rent) => {
  return formatCurrency(rent, { maximumFractionDigits: 0 });
};

export const formatAnnualIncome = (income) => {
  return formatCurrency(income, { maximumFractionDigits: 0 });
};

export const formatInvestmentScore = (score) => {
  if (score == null || isNaN(score)) {
    return 'N/A';
  }
  
  return `${Math.round(score)}/100`;
};

export const truncateText = (text, maxLength = 100) => {
  if (!text) return '';
  
  if (text.length <= maxLength) {
    return text;
  }
  
  return text.substring(0, maxLength) + '...';
};

export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};