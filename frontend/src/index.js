/**
 * React application entry point.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import initializeSentry from './utils/sentry';

// Initialize Sentry
initializeSentry();

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
