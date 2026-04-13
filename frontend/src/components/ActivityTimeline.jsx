import React, { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import api from '../services/api';

const ActivityTimeline = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchActivities();
  }, []);

  const fetchActivities = async () => {
    try {
      const data = await api.getUserActivity({ limit: 20 });
      setActivities(data.activities || []);
    } catch (error) {
      console.error('Error fetching activities:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4">Loading activities...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
      <div className="space-y-4">
        {activities.map((activity, index) => (
          <div key={activity.id} className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className={`w-2 h-2 rounded-full mt-2 ${
                activity.status === 'completed' ? 'bg-green-500' :
                activity.status === 'running' ? 'bg-blue-500' :
                activity.status === 'failed' ? 'bg-red-500' : 'bg-gray-500'
              }`} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900">{activity.action}</p>
              <p className="text-xs text-gray-500">
                {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
              </p>
            </div>
          </div>
        ))}
        {activities.length === 0 && (
          <p className="text-gray-500 text-center py-4">No recent activity</p>
        )}
      </div>
    </div>
  );
};

export default ActivityTimeline;