/**
 * DashboardContainer.jsx - Main dynamic dashboard with real-time monitoring
 * No hardcoded templates - all data from backend
 */

import React, { useState, useEffect, useCallback } from 'react';
import './dashboard.css';

/**
 * Dynamic Widget - Renders any dashboard component dynamically
 */
const DynamicWidget = ({ 
  id, 
  type, 
  title, 
  config = {}, 
  onRemove, 
  onResize,
  refreshRate = 5000 
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Fetch widget data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/dashboard/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (!response.ok) throw new Error('Fetch failed');
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
      logger.error(`Widget fetch error (${type}):`, err);
    } finally {
      setLoading(false);
    }
  }, [type, config]);

  // Auto-refresh
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshRate);
    return () => clearInterval(interval);
  }, [fetchData, refreshRate]);

  return (
    <div className={`dashboard-widget ${type} ${isExpanded ? 'expanded' : ''}`} data-widget-id={id}>
      <div className="widget-header">
        <h3 className="widget-title">{title}</h3>
        <div className="widget-controls">
          <button 
            className="widget-btn expand-btn"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Collapse' : 'Expand'}
            aria-label="Toggle expand"
          >
            ⛶
          </button>
          <button 
            className="widget-btn refresh-btn"
            onClick={fetchData}
            disabled={loading}
            title="Refresh"
            aria-label="Refresh widget"
          >
            ⟲
          </button>
          <button 
            className="widget-btn close-btn"
            onClick={() => onRemove(id)}
            title="Remove"
            aria-label="Remove widget"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="widget-content">
        {loading && !data && <div className="widget-loading">Loading...</div>}
        {error && <div className="widget-error">Error: {error}</div>}
        {data && <WidgetContent type={type} data={data} config={config} />}
      </div>
    </div>
  );
};

/**
 * Render widget content based on type
 */
const WidgetContent = ({ type, data, config }) => {
  switch (type) {
    case 'metrics':
      return <MetricsContent data={data} />;
    case 'health':
      return <HealthContent data={data} />;
    case 'performance':
      return <PerformanceContent data={data} />;
    case 'activity':
      return <ActivityContent data={data} />;
    case 'web-access':
      return <WebAccessContent data={data} />;
    case 'agent-status':
      return <AgentStatusContent data={data} />;
    case 'training-status':
      return <TrainingStatusContent data={data} />;
    default:
      return <div className="widget-default">Widget type: {type}</div>;
  }
};

/**
 * Metrics Content - System metrics
 */
const MetricsContent = ({ data }) => (
  <div className="metrics-grid">
    {data.metrics && data.metrics.map((metric, idx) => (
      <div key={idx} className="metric-item">
        <div className="metric-label">{metric.label}</div>
        <div className={`metric-value ${metric.status || ''}`}>
          {metric.value}
        </div>
        {metric.change && (
          <div className={`metric-change ${metric.change > 0 ? 'positive' : 'negative'}`}>
            {metric.change > 0 ? '↑' : '↓'} {Math.abs(metric.change)}%
          </div>
        )}
      </div>
    ))}
  </div>
);

/**
 * Health Content - System health monitoring
 */
const HealthContent = ({ data }) => (
  <div className="health-container">
    {data.components && data.components.map((component, idx) => (
      <div key={idx} className={`health-item health-${component.status}`}>
        <span className="health-indicator"></span>
        <div className="health-info">
          <div className="health-name">{component.name}</div>
          <div className="health-status">{component.status}</div>
        </div>
        {component.uptime && (
          <div className="health-meta">{component.uptime}</div>
        )}
      </div>
    ))}
  </div>
);

/**
 * Performance Content - Performance charts and stats
 */
const PerformanceContent = ({ data }) => (
  <div className="performance-container">
    <div className="performance-summary">
      {data.summary && (
        <>
          <div className="perf-stat">
            <div className="perf-label">Avg Response</div>
            <div className="perf-value">{data.summary.avg_response}ms</div>
          </div>
          <div className="perf-stat">
            <div className="perf-label">Success Rate</div>
            <div className="perf-value">{data.summary.success_rate}%</div>
          </div>
          <div className="perf-stat">
            <div className="perf-label">Throughput</div>
            <div className="perf-value">{data.summary.throughput} req/s</div>
          </div>
        </>
      )}
    </div>
    {data.timeline && (
      <div className="performance-chart">
        <div className="chart-placeholder">
          [Performance timeline would render here]
        </div>
      </div>
    )}
  </div>
);

/**
 * Activity Content - Real-time activity log
 */
const ActivityContent = ({ data }) => (
  <div className="activity-list">
    {data.activities && data.activities.length > 0 ? (
      data.activities.map((activity, idx) => (
        <div key={idx} className={`activity-item activity-${activity.type}`}>
          <div className="activity-time">{activity.time}</div>
          <div className="activity-message">{activity.message}</div>
          {activity.details && (
            <div className="activity-details">{activity.details}</div>
          )}
        </div>
      ))
    ) : (
      <div className="activity-empty">No recent activity</div>
    )}
  </div>
);

/**
 * Web Access Content - Monitor web searches and data sources
 */
const WebAccessContent = ({ data }) => (
  <div className="web-access-container">
    <div className="web-stats">
      <div className="web-stat">
        <div className="web-stat-label">Searches</div>
        <div className="web-stat-value">{data.total_searches || 0}</div>
      </div>
      <div className="web-stat">
        <div className="web-stat-label">Sources</div>
        <div className="web-stat-value">{data.total_sources || 0}</div>
      </div>
      <div className="web-stat">
        <div className="web-stat-label">Freshness</div>
        <div className="web-stat-value">{data.avg_freshness || 'N/A'}</div>
      </div>
    </div>
    {data.recent_searches && (
      <div className="web-searches">
        <h4>Recent Searches</h4>
        {data.recent_searches.map((search, idx) => (
          <div key={idx} className="web-search-item">
            <div className="search-query">{search.query}</div>
            <div className="search-count">{search.result_count} results</div>
          </div>
        ))}
      </div>
    )}
  </div>
);

/**
 * Agent Status Content
 */
const AgentStatusContent = ({ data }) => (
  <div className="agent-status-container">
    {data.agents && data.agents.map((agent, idx) => (
      <div key={idx} className={`agent-card agent-${agent.status}`}>
        <div className="agent-name">{agent.name}</div>
        <div className="agent-status">{agent.status}</div>
        {agent.current_task && (
          <div className="agent-task">Task: {agent.current_task}</div>
        )}
        {agent.progress !== undefined && (
          <div className="agent-progress">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${agent.progress}%` }}
              ></div>
            </div>
            <span className="progress-text">{agent.progress}%</span>
          </div>
        )}
      </div>
    ))}
  </div>
);

/**
 * Training Status Content
 */
const TrainingStatusContent = ({ data }) => (
  <div className="training-status-container">
    {data.trainings && data.trainings.length > 0 ? (
      data.trainings.map((training, idx) => (
        <div key={idx} className={`training-item training-${training.status}`}>
          <div className="training-name">{training.name}</div>
          <div className="training-status">{training.status}</div>
          {training.progress !== undefined && (
            <div className="training-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${training.progress}%` }}
                ></div>
              </div>
              {training.eta && <span className="training-eta">ETA: {training.eta}</span>}
            </div>
          )}
          {training.metrics && (
            <div className="training-metrics">
              {Object.entries(training.metrics).map(([key, value]) => (
                <div key={key} className="metric-line">
                  {key}: {value}
                </div>
              ))}
            </div>
          )}
        </div>
      ))
    ) : (
      <div className="training-empty">No active trainings</div>
    )}
  </div>
);

/**
 * Widget Manager - Manage available widgets
 */
const WidgetManager = ({ onAddWidget, availableWidgets }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="widget-manager">
      <button 
        className="add-widget-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Add widget"
      >
        + Add Widget
      </button>
      
      {isOpen && (
        <div className="widget-menu">
          {availableWidgets.map((widget) => (
            <button
              key={widget.type}
              className="widget-menu-item"
              onClick={() => {
                onAddWidget(widget);
                setIsOpen(false);
              }}
            >
              {widget.title}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Main Dashboard Container
 */
const DashboardContainer = () => {
  const [widgets, setWidgets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Available widget types
  const availableWidgets = [
    { type: 'metrics', title: 'System Metrics' },
    { type: 'health', title: 'System Health' },
    { type: 'performance', title: 'Performance' },
    { type: 'activity', title: 'Activity Log' },
    { type: 'web-access', title: 'Web Access Monitor' },
    { type: 'agent-status', title: 'Agent Status' },
    { type: 'training-status', title: 'Training Status' }
  ];

  // Load saved widgets on mount
  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const response = await fetch('/api/dashboard/config');
        if (response.ok) {
          const config = await response.json();
          if (config.widgets) {
            setWidgets(config.widgets);
          } else {
            // Default widgets if none configured
            initializeDefaultWidgets();
          }
        } else {
          initializeDefaultWidgets();
        }
      } catch (err) {
        logger.warn('Could not load dashboard config, using defaults');
        initializeDefaultWidgets();
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboard();
  }, []);

  // Initialize default widgets
  const initializeDefaultWidgets = () => {
    const defaults = [
      { id: 'metrics-1', type: 'metrics', title: 'System Metrics' },
      { id: 'health-1', type: 'health', title: 'System Health' },
      { id: 'performance-1', type: 'performance', title: 'Performance' },
      { id: 'activity-1', type: 'activity', title: 'Recent Activity' }
    ];
    setWidgets(defaults);
  };

  // Add widget
  const handleAddWidget = (widgetType) => {
    const newWidget = {
      id: `${widgetType.type}-${Date.now()}`,
      type: widgetType.type,
      title: widgetType.title,
      config: {}
    };
    
    const updatedWidgets = [...widgets, newWidget];
    setWidgets(updatedWidgets);
    saveDashboard(updatedWidgets);
  };

  // Remove widget
  const handleRemoveWidget = (widgetId) => {
    const updatedWidgets = widgets.filter(w => w.id !== widgetId);
    setWidgets(updatedWidgets);
    saveDashboard(updatedWidgets);
  };

  // Save dashboard configuration
  const saveDashboard = async (widgetsConfig) => {
    try {
      await fetch('/api/dashboard/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ widgets: widgetsConfig })
      });
    } catch (err) {
      logger.error('Failed to save dashboard config:', err);
    }
  };

  if (isLoading) {
    return <div className="dashboard-loading">Loading dashboard...</div>;
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>System Dashboard</h1>
        <div className="dashboard-meta">
          <span className="dashboard-timestamp">
            Last updated: {new Date().toLocaleTimeString()}
          </span>
          <WidgetManager 
            onAddWidget={handleAddWidget}
            availableWidgets={availableWidgets}
          />
        </div>
      </div>

      {error && (
        <div className="dashboard-error">
          Error: {error}
        </div>
      )}

      <div className="dashboard-grid">
        {widgets.length > 0 ? (
          widgets.map((widget) => (
            <DynamicWidget
              key={widget.id}
              id={widget.id}
              type={widget.type}
              title={widget.title}
              config={widget.config || {}}
              onRemove={handleRemoveWidget}
              refreshRate={widget.refreshRate || 5000}
            />
          ))
        ) : (
          <div className="dashboard-empty">
            <p>No widgets configured</p>
            <p>Click "Add Widget" to get started</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardContainer;
