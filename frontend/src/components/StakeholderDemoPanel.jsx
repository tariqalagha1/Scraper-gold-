import React, { useState, useEffect } from 'react';
import api from '../services/api';

const StakeholderDemoPanel = () => {
  const [demoData, setDemoData] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDemoData();
  }, []);

  const fetchDemoData = async () => {
    try {
      const data = await api.getDemoOverview();
      setDemoData(data);
    } catch (error) {
      console.error('Error fetching demo data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4">Loading demo data...</div>;
  }

  return (
    <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-lg p-8 text-white">
      <h2 className="text-3xl font-bold mb-6">AI-Powered Web Scraping Platform</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white bg-opacity-20 rounded-lg p-6">
          <div className="text-4xl font-bold mb-2">{demoData.total_users || 0}</div>
          <div className="text-lg">Active Users</div>
        </div>
        <div className="bg-white bg-opacity-20 rounded-lg p-6">
          <div className="text-4xl font-bold mb-2">{demoData.total_jobs || 0}</div>
          <div className="text-lg">Scraping Jobs</div>
        </div>
        <div className="bg-white bg-opacity-20 rounded-lg p-6">
          <div className="text-4xl font-bold mb-2">{demoData.total_runs || 0}</div>
          <div className="text-lg">Total Runs</div>
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-4">Key Features</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {demoData.features?.map((feature, index) => (
            <div key={index} className="flex items-center">
              <div className="w-2 h-2 bg-white rounded-full mr-3"></div>
              <span>{feature}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-4">Performance Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(demoData.performance_metrics || {}).map(([key, value]) => (
            <div key={key} className="bg-white bg-opacity-20 rounded-lg p-4">
              <div className="text-2xl font-bold mb-1">{value}</div>
              <div className="text-sm capitalize">{key.replace('_', ' ')}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="text-center">
        <div className="inline-flex items-center px-4 py-2 bg-white bg-opacity-20 rounded-full">
          <div className="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
          <span className="text-sm font-medium">System Status: {demoData.system_status || 'Operational'}</span>
        </div>
      </div>
    </div>
  );
};

export default StakeholderDemoPanel;