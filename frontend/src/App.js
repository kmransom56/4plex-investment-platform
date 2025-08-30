import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import Navbar from './components/Layout/Navbar';
import Dashboard from './pages/Dashboard';
import PropertyDiscovery from './pages/PropertyDiscovery';
import PropertyAnalysis from './pages/PropertyAnalysis';
import InvestmentOpportunities from './pages/InvestmentOpportunities';
import PropertyDetails from './pages/PropertyDetails';
import SystemHealth from './pages/SystemHealth';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      dark: '#115293',
      light: '#42a5f5',
    },
    secondary: {
      main: '#dc004e',
      dark: '#9a0036',
      light: '#e33371',
    },
    success: {
      main: '#2e7d32',
    },
    warning: {
      main: '#ed6c02',
    },
    error: {
      main: '#d32f2f',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          borderRadius: 12,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Router>
          <div className="App">
            <Navbar />
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/discovery" element={<PropertyDiscovery />} />
              <Route path="/analysis" element={<PropertyAnalysis />} />
              <Route path="/opportunities" element={<InvestmentOpportunities />} />
              <Route path="/property/:id" element={<PropertyDetails />} />
              <Route path="/system" element={<SystemHealth />} />
            </Routes>
          </div>
        </Router>
      </LocalizationProvider>
    </ThemeProvider>
  );
}

export default App;