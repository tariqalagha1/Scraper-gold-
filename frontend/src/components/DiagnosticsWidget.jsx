import React, { useState, useEffect } from 'react';
import api from '../services/api';

const DiagnosticsWidget = () => {
  const [diagnostics, setDiagnostics] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  const fetchDiagnostics = async () => {
    try {
      const data = await api.getSystemDiagnostics();
      setDiagnostics(data);
    } catch (error) {
      console.error('Error fetching diagnostics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4">Loading diagnostics...</div>;
  }

  const { system = {}, process = {}, database = {} } = diagnostics;

  return (
    <div className="rounded-2xl border border-white/10 bg-surface p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4 text-white">System Diagnostics</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* System Info */}
        <div className="space-y-2">
          <h4 className="font-medium text-white">System</h4>
          <div className="text-sm text-[#D3C4B5] space-y-1">
            <div>Platform: {system.platform}</div>
            <div>Python: {system.python_version}</div>
            <div>CPU Cores: {system.cpu_count}</div>
            <div>Memory: {(system.memory_total / (1024**3)).toFixed(1)} GB</div>
            <div>Disk: {(system.disk_total / (1024**3)).toFixed(1)} GB</div>
          </div>
        </div>

        {/* Process Info */}
        <div className="space-y-2">
          <h4 className="font-medium text-white">Process</h4>
          <div className="text-sm text-[#D3C4B5] space-y-1">
            <div>PID: {process.pid}</div>
            <div>CPU: {process.cpu_percent?.toFixed(1)}%</div>
            <div>Memory: {process.memory_mb?.toFixed(1)} MB</div>
            <div>Threads: {process.threads}</div>
          </div>
        </div>

        {/* Database Info */}
        <div className="space-y-2">
          <h4 className="font-medium text-white">Database</h4>
          <div className="text-sm text-[#D3C4B5] space-y-1">
            <div>Users: {database.users}</div>
            <div>Jobs: {database.jobs}</div>
            <div>Runs: {database.runs}</div>
            <div>Active Runs: {database.active_runs}</div>
            <div className="flex items-center">
              <div className={`w-2 h-2 rounded-full mr-2 ${
                database.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className="capitalize">{database.status}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-white/10">
        <button
          onClick={fetchDiagnostics}
          className="px-4 py-2 bg-[#FFD3A0] text-[#121415] rounded-md hover:bg-[#F0BD7F] focus:outline-none focus:ring-2 focus:ring-[#FFD3A0]"
        >
          Refresh Diagnostics
        </button>
      </div>
    </div>
  );
};

export default DiagnosticsWidget;