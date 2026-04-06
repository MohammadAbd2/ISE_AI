/**
 * TrainingContainer.jsx - Main training interface for AI model fine-tuning
 * Supports dataset upload, prompt optimization, deep learning training
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import './training.css';

/**
 * Tab Navigation
 */
const TrainingTabs = ({ activeTab, onTabChange, tabs }) => (
  <div className="training-tabs">
    {tabs.map((tab) => (
      <button
        key={tab.id}
        className={`training-tab ${activeTab === tab.id ? 'active' : ''}`}
        onClick={() => onTabChange(tab.id)}
        aria-label={tab.label}
      >
        {tab.icon} {tab.label}
      </button>
    ))}
  </div>
);

/**
 * Dataset Manager - Upload and manage datasets
 */
const DatasetManager = () => {
  const [datasets, setDatasets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/training/dataset/upload', {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          const dataset = await response.json();
          setDatasets(prev => [...prev, dataset]);
        }
      }
    } catch (err) {
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDataset = async (datasetId) => {
    try {
      await fetch(`/api/training/dataset/${datasetId}`, { method: 'DELETE' });
      setDatasets(prev => prev.filter(d => d.id !== datasetId));
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  return (
    <div className="dataset-manager">
      <div className="manager-header">
        <h3>Dataset Management</h3>
        <button 
          className="upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? 'Uploading...' : '📁 Upload Dataset'}
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".csv,.json,.parquet,.xlsx"
        onChange={handleFileUpload}
        style={{ display: 'none' }}
        aria-label="Upload dataset"
      />

      <div className="datasets-list">
        {datasets.length > 0 ? (
          datasets.map((dataset) => (
            <div key={dataset.id} className="dataset-card">
              <div className="dataset-icon">📊</div>
              <div className="dataset-info">
                <div className="dataset-name">{dataset.name}</div>
                <div className="dataset-meta">
                  <span className="dataset-size">{dataset.size}</span>
                  <span className="dataset-records">{dataset.records} records</span>
                  <span className="dataset-type">{dataset.type}</span>
                </div>
              </div>
              <div className="dataset-actions">
                <button 
                  className="action-btn preview-btn"
                  onClick={() => window.open(`/api/training/dataset/${dataset.id}/preview`)}
                >
                  👁️ Preview
                </button>
                <button 
                  className="action-btn delete-btn"
                  onClick={() => handleDeleteDataset(dataset.id)}
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No datasets uploaded yet</p>
            <p className="hint">Upload CSV, JSON, Parquet, or Excel files for training</p>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Prompt Optimizer - Fine-tune prompts with A/B testing
 */
const PromptOptimizer = () => {
  const [prompts, setPrompts] = useState([]);
  const [editing, setEditing] = useState(null);
  const [newPrompt, setNewPrompt] = useState({ title: '', template: '', description: '' });

  const handleSavePrompt = async () => {
    try {
      const response = await fetch('/api/training/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPrompt)
      });

      if (response.ok) {
        const prompt = await response.json();
        setPrompts(prev => [...prev, prompt]);
        setNewPrompt({ title: '', template: '', description: '' });
      }
    } catch (err) {
      console.error('Save error:', err);
    }
  };

  const handleTestPrompt = async (promptId) => {
    try {
      await fetch(`/api/training/prompts/${promptId}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (err) {
      console.error('Test error:', err);
    }
  };

  return (
    <div className="prompt-optimizer">
      <div className="optimizer-header">
        <h3>Prompt Optimization</h3>
        <p className="hint">Create and test different prompts for better results</p>
      </div>

      <div className="prompt-editor">
        <h4>Create New Prompt</h4>
        <div className="form-group">
          <label>Title</label>
          <input
            type="text"
            value={newPrompt.title}
            onChange={(e) => setNewPrompt(prev => ({ ...prev, title: e.target.value }))}
            placeholder="e.g., Better Code Generation"
          />
        </div>

        <div className="form-group">
          <label>Template</label>
          <textarea
            value={newPrompt.template}
            onChange={(e) => setNewPrompt(prev => ({ ...prev, template: e.target.value }))}
            placeholder="Enter your prompt template here..."
            rows="6"
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <input
            type="text"
            value={newPrompt.description}
            onChange={(e) => setNewPrompt(prev => ({ ...prev, description: e.target.value }))}
            placeholder="What is this prompt for?"
          />
        </div>

        <button 
          className="save-btn"
          onClick={handleSavePrompt}
          disabled={!newPrompt.title || !newPrompt.template}
        >
          💾 Save Prompt
        </button>
      </div>

      <div className="prompts-list">
        <h4>Saved Prompts</h4>
        {prompts.length > 0 ? (
          prompts.map((prompt) => (
            <div key={prompt.id} className="prompt-card">
              <div className="prompt-header">
                <h5>{prompt.title}</h5>
                <div className="prompt-stats">
                  <span className="stat">Accuracy: {prompt.accuracy || 'N/A'}%</span>
                  <span className="stat">Tests: {prompt.test_count || 0}</span>
                </div>
              </div>
              <div className="prompt-description">{prompt.description}</div>
              <div className="prompt-actions">
                <button 
                  className="action-btn test-btn"
                  onClick={() => handleTestPrompt(prompt.id)}
                >
                  🧪 Test
                </button>
                <button 
                  className="action-btn edit-btn"
                  onClick={() => setEditing(prompt.id)}
                >
                  ✏️ Edit
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No prompts created yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Deep Learning Trainer - Configure and run training
 */
const DeepLearningTrainer = () => {
  const [training, setTraining] = useState(null);
  const [config, setConfig] = useState({
    model_type: 'transformer',
    learning_rate: 0.001,
    epochs: 10,
    batch_size: 32,
    validation_split: 0.2
  });

  const handleStartTraining = async () => {
    try {
      const response = await fetch('/api/training/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });

      if (response.ok) {
        const train = await response.json();
        setTraining(train);
      }
    } catch (err) {
      console.error('Training error:', err);
    }
  };

  return (
    <div className="trainer-container">
      <div className="trainer-header">
        <h3>Deep Learning Training</h3>
        <p className="hint">Configure and start model training</p>
      </div>

      <div className="trainer-config">
        <h4>Training Configuration</h4>

        <div className="config-group">
          <label>Model Type</label>
          <select 
            value={config.model_type}
            onChange={(e) => setConfig(prev => ({ ...prev, model_type: e.target.value }))}
          >
            <option value="transformer">Transformer</option>
            <option value="lstm">LSTM</option>
            <option value="cnn">CNN</option>
            <option value="gpt">GPT-Based</option>
          </select>
        </div>

        <div className="config-group">
          <label>Learning Rate</label>
          <input
            type="number"
            step="0.0001"
            value={config.learning_rate}
            onChange={(e) => setConfig(prev => ({ ...prev, learning_rate: parseFloat(e.target.value) }))}
          />
        </div>

        <div className="config-group">
          <label>Epochs</label>
          <input
            type="number"
            min="1"
            max="100"
            value={config.epochs}
            onChange={(e) => setConfig(prev => ({ ...prev, epochs: parseInt(e.target.value) }))}
          />
        </div>

        <div className="config-group">
          <label>Batch Size</label>
          <input
            type="number"
            min="1"
            max="256"
            value={config.batch_size}
            onChange={(e) => setConfig(prev => ({ ...prev, batch_size: parseInt(e.target.value) }))}
          />
        </div>

        <div className="config-group">
          <label>Validation Split</label>
          <input
            type="number"
            min="0.1"
            max="0.9"
            step="0.1"
            value={config.validation_split}
            onChange={(e) => setConfig(prev => ({ ...prev, validation_split: parseFloat(e.target.value) }))}
          />
        </div>

        <button 
          className="train-btn"
          onClick={handleStartTraining}
          disabled={training && training.status === 'running'}
        >
          🚀 Start Training
        </button>
      </div>

      {training && (
        <div className="training-status">
          <h4>Training Status</h4>
          <div className={`training-card training-${training.status}`}>
            <div className="status-header">
              <span className="status-icon">
                {training.status === 'running' ? '⏳' : training.status === 'completed' ? '✅' : '❌'}
              </span>
              <span className="status-text">{training.status.toUpperCase()}</span>
            </div>

            {training.progress !== undefined && (
              <div className="training-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${training.progress}%` }}
                  ></div>
                </div>
                <span className="progress-text">{training.progress}%</span>
              </div>
            )}

            {training.metrics && (
              <div className="training-metrics-display">
                <div className="metric-item">
                  <div className="metric-label">Loss</div>
                  <div className="metric-value">{training.metrics.loss?.toFixed(4)}</div>
                </div>
                <div className="metric-item">
                  <div className="metric-label">Accuracy</div>
                  <div className="metric-value">{training.metrics.accuracy?.toFixed(2)}%</div>
                </div>
                <div className="metric-item">
                  <div className="metric-label">ETA</div>
                  <div className="metric-value">{training.eta || 'Calculating...'}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Model Evaluator - Test and evaluate trained models
 */
const ModelEvaluator = () => {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [evaluation, setEvaluation] = useState(null);

  const handleEvaluateModel = async (modelId) => {
    try {
      const response = await fetch(`/api/training/models/${modelId}/evaluate`, {
        method: 'POST'
      });

      if (response.ok) {
        const result = await response.json();
        setEvaluation(result);
      }
    } catch (err) {
      console.error('Evaluation error:', err);
    }
  };

  return (
    <div className="evaluator-container">
      <div className="evaluator-header">
        <h3>Model Evaluation</h3>
        <p className="hint">Test and evaluate your trained models</p>
      </div>

      <div className="models-list">
        <h4>Trained Models</h4>
        {models.length > 0 ? (
          models.map((model) => (
            <div 
              key={model.id} 
              className={`model-card ${selectedModel === model.id ? 'selected' : ''}`}
              onClick={() => setSelectedModel(model.id)}
            >
              <div className="model-name">{model.name}</div>
              <div className="model-version">v{model.version}</div>
              <div className="model-size">{model.size}</div>
              <button 
                className="eval-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleEvaluateModel(model.id);
                }}
              >
                📊 Evaluate
              </button>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No trained models available</p>
          </div>
        )}
      </div>

      {evaluation && (
        <div className="evaluation-results">
          <h4>Evaluation Results</h4>
          <div className="eval-card">
            <div className="eval-metric">
              <div className="eval-label">Accuracy</div>
              <div className="eval-value">{evaluation.accuracy?.toFixed(2)}%</div>
            </div>
            <div className="eval-metric">
              <div className="eval-label">Precision</div>
              <div className="eval-value">{evaluation.precision?.toFixed(2)}</div>
            </div>
            <div className="eval-metric">
              <div className="eval-label">Recall</div>
              <div className="eval-value">{evaluation.recall?.toFixed(2)}</div>
            </div>
            <div className="eval-metric">
              <div className="eval-label">F1 Score</div>
              <div className="eval-value">{evaluation.f1_score?.toFixed(2)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Training History - View past training runs
 */
const TrainingHistory = () => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch('/api/training/history');
        if (response.ok) {
          const data = await response.json();
          setHistory(data.trainings || []);
        }
      } catch (err) {
        console.error('History fetch error:', err);
      }
    };

    fetchHistory();
  }, []);

  return (
    <div className="history-container">
      <div className="history-header">
        <h3>Training History</h3>
        <p className="hint">View and compare past training runs</p>
      </div>

      <div className="history-list">
        {history.length > 0 ? (
          history.map((run, idx) => (
            <div key={idx} className={`history-item history-${run.status}`}>
              <div className="history-info">
                <div className="history-title">{run.name}</div>
                <div className="history-date">{new Date(run.timestamp).toLocaleString()}</div>
              </div>
              <div className="history-stats">
                <span className="stat">Duration: {run.duration}</span>
                <span className="stat">Accuracy: {run.final_accuracy?.toFixed(2)}%</span>
                <span className="stat">Status: {run.status}</span>
              </div>
              <button className="view-btn">📖 View Details</button>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No training history yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Main Training Container
 */
const TrainingContainer = () => {
  const [activeTab, setActiveTab] = useState('dataset');

  const tabs = [
    { id: 'dataset', label: 'Datasets', icon: '📊' },
    { id: 'prompts', label: 'Prompts', icon: '💬' },
    { id: 'training', label: 'Training', icon: '🚀' },
    { id: 'evaluation', label: 'Evaluation', icon: '📈' },
    { id: 'history', label: 'History', icon: '📋' }
  ];

  return (
    <div className="training-container">
      <div className="training-header">
        <h1>AI Training & Fine-Tuning</h1>
        <p className="subtitle">Train, evaluate, and optimize your AI models</p>
      </div>

      <TrainingTabs activeTab={activeTab} onTabChange={setActiveTab} tabs={tabs} />

      <div className="training-content">
        {activeTab === 'dataset' && <DatasetManager />}
        {activeTab === 'prompts' && <PromptOptimizer />}
        {activeTab === 'training' && <DeepLearningTrainer />}
        {activeTab === 'evaluation' && <ModelEvaluator />}
        {activeTab === 'history' && <TrainingHistory />}
      </div>
    </div>
  );
};

export default TrainingContainer;
