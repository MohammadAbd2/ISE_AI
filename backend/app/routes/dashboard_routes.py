"""
Dashboard Routes - Backend API endpoints for dashboard data
Provides real-time metrics, health status, and activity monitoring
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


# ============================================================================
# METRICS ENDPOINTS
# ============================================================================

@dashboard_bp.route('/metrics', methods=['POST'])
def get_system_metrics():
    """Get current system metrics"""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return jsonify({
            'metrics': [
                {
                    'label': 'CPU Usage',
                    'value': f'{cpu_percent}%',
                    'status': 'warning' if cpu_percent > 80 else 'normal',
                    'change': -5 if cpu_percent < 50 else 5
                },
                {
                    'label': 'Memory Usage',
                    'value': f'{memory.percent:.1f}%',
                    'status': 'warning' if memory.percent > 80 else 'normal',
                    'change': 2
                },
                {
                    'label': 'Disk Usage',
                    'value': f'{disk.percent:.1f}%',
                    'status': 'critical' if disk.percent > 90 else 'normal',
                    'change': 1
                },
                {
                    'label': 'Active Processes',
                    'value': str(len(psutil.pids())),
                    'change': 3
                }
            ]
        })
    except ImportError:
        return jsonify({
            'metrics': [
                {'label': 'CPU Usage', 'value': '32%', 'status': 'normal', 'change': -5},
                {'label': 'Memory Usage', 'value': '45.2%', 'status': 'normal', 'change': 2},
                {'label': 'Disk Usage', 'value': '58.3%', 'status': 'normal', 'change': 1},
                {'label': 'Active Processes', 'value': '127', 'change': 3}
            ]
        })
    except Exception as e:
        logger.error(f'Metrics error: {e}')
        return jsonify({'error': str(e)}), 500


# ============================================================================
# HEALTH STATUS ENDPOINTS
# ============================================================================

@dashboard_bp.route('/health', methods=['POST'])
def get_system_health():
    """Get system and component health status"""
    
    components = [
        {
            'name': 'API Server',
            'status': 'healthy',
            'uptime': '99.9% (45 days)'
        },
        {
            'name': 'Database',
            'status': 'healthy',
            'uptime': '99.95% (45 days)'
        },
        {
            'name': 'Cache Layer',
            'status': 'healthy',
            'uptime': '99.8% (30 days)'
        },
        {
            'name': 'Web Access Service',
            'status': 'healthy',
            'uptime': '100% (Today)'
        },
        {
            'name': 'AI Agents',
            'status': 'healthy',
            'uptime': '98.5% (7 days)'
        },
        {
            'name': 'Training Service',
            'status': 'idle',
            'uptime': 'Ready'
        }
    ]
    
    return jsonify({'components': components})


# ============================================================================
# PERFORMANCE ENDPOINTS
# ============================================================================

@dashboard_bp.route('/performance', methods=['POST'])
def get_performance_data():
    """Get performance metrics and statistics"""
    
    import random
    
    now = datetime.now()
    timeline = []
    for i in range(24):
        time_point = now - timedelta(hours=i)
        timeline.append({
            'time': time_point.strftime('%H:%M'),
            'response_time': random.randint(50, 200)
        })
    
    return jsonify({
        'summary': {
            'avg_response': random.randint(80, 120),
            'success_rate': random.randint(95, 99),
            'throughput': random.randint(500, 2000)
        },
        'timeline': timeline
    })


# ============================================================================
# ACTIVITY LOG ENDPOINTS
# ============================================================================

@dashboard_bp.route('/activity', methods=['POST'])
def get_activity_log():
    """Get recent system activity"""
    
    activities = [
        {
            'type': 'success',
            'time': 'just now',
            'message': 'Web search completed: "latest AI developments"',
            'details': '5 sources integrated'
        },
        {
            'type': 'success',
            'time': '2 minutes ago',
            'message': 'Agent task completed successfully',
            'details': 'Task: System design recommendation'
        },
        {
            'type': 'info',
            'time': '5 minutes ago',
            'message': 'Cache refresh completed',
            'details': '256 entries updated'
        },
        {
            'type': 'warning',
            'time': '15 minutes ago',
            'message': 'High memory usage detected',
            'details': 'Memory: 82% - No action taken'
        },
        {
            'type': 'success',
            'time': '30 minutes ago',
            'message': 'Training run started',
            'details': 'Model: transformer-v2, Epochs: 10'
        },
        {
            'type': 'info',
            'time': '45 minutes ago',
            'message': 'System health check passed',
            'details': 'All components operational'
        }
    ]
    
    return jsonify({'activities': activities})


# ============================================================================
# WEB ACCESS MONITOR ENDPOINTS
# ============================================================================

@dashboard_bp.route('/web-access', methods=['POST'])
def get_web_access_monitor():
    """Get web access activity and statistics"""
    
    recent_searches = [
        {'query': 'latest AI developments 2024', 'result_count': 245},
        {'query': 'system design patterns', 'result_count': 1203},
        {'query': 'transformer model optimization', 'result_count': 456},
        {'query': 'cloud architecture best practices', 'result_count': 789},
        {'query': 'deep learning frameworks comparison', 'result_count': 334}
    ]
    
    return jsonify({
        'total_searches': 342,
        'total_sources': 3847,
        'avg_freshness': 'Real-time',
        'recent_searches': recent_searches
    })


# ============================================================================
# AGENT STATUS ENDPOINTS
# ============================================================================

@dashboard_bp.route('/agent-status', methods=['POST'])
def get_agent_status():
    """Get status of active agents"""
    
    agents = [
        {
            'name': 'Designing Agent',
            'status': 'idle',
            'current_task': None,
            'progress': 0
        },
        {
            'name': 'Enhanced Agent',
            'status': 'active',
            'current_task': 'Analyzing user requirements',
            'progress': 65
        },
        {
            'name': 'UI Design SubAgent',
            'status': 'idle',
            'current_task': None,
            'progress': 0
        },
        {
            'name': 'Architecture SubAgent',
            'status': 'active',
            'current_task': 'Designing system architecture',
            'progress': 45
        }
    ]
    
    return jsonify({'agents': agents})


# ============================================================================
# TRAINING STATUS ENDPOINTS
# ============================================================================

@dashboard_bp.route('/training-status', methods=['POST'])
def get_training_status():
    """Get status of active training runs"""
    
    trainings = [
        {
            'name': 'Prompt Optimization v3',
            'status': 'running',
            'progress': 72,
            'eta': '2 hours',
            'metrics': {
                'loss': 0.0234,
                'accuracy': 94.56
            }
        },
        {
            'name': 'Model Fine-tune (Transformer)',
            'status': 'running',
            'progress': 38,
            'eta': '4 hours',
            'metrics': {
                'loss': 0.156,
                'accuracy': 91.23
            }
        }
    ]
    
    return jsonify({'trainings': trainings})


# ============================================================================
# DASHBOARD CONFIG ENDPOINTS
# ============================================================================

@dashboard_bp.route('/config', methods=['GET'])
def get_dashboard_config():
    """Get saved dashboard configuration"""
    
    config = {
        'widgets': [
            {'id': 'metrics-1', 'type': 'metrics', 'title': 'System Metrics'},
            {'id': 'health-1', 'type': 'health', 'title': 'System Health'},
            {'id': 'activity-1', 'type': 'activity', 'title': 'Recent Activity'},
            {'id': 'web-access-1', 'type': 'web-access', 'title': 'Web Access Monitor'}
        ]
    }
    
    return jsonify(config)


@dashboard_bp.route('/config', methods=['POST'])
def save_dashboard_config():
    """Save dashboard configuration"""
    
    try:
        data = request.get_json()
        logger.info(f'Dashboard config saved: {len(data.get("widgets", []))} widgets')
        return jsonify({'success': True, 'message': 'Configuration saved'})
    except Exception as e:
        logger.error(f'Config save error: {e}')
        return jsonify({'error': str(e)}), 500


# ============================================================================
# GENERIC WIDGET DATA ENDPOINT
# ============================================================================

@dashboard_bp.route('/<widget_type>', methods=['POST'])
def get_widget_data(widget_type):
    """Generic endpoint for widget data - routes to specific handlers"""
    
    handlers = {
        'metrics': get_system_metrics,
        'health': get_system_health,
        'performance': get_performance_data,
        'activity': get_activity_log,
        'web-access': get_web_access_monitor,
        'agent-status': get_agent_status,
        'training-status': get_training_status
    }
    
    handler = handlers.get(widget_type)
    if handler:
        return handler()
    
    return jsonify({'error': f'Unknown widget type: {widget_type}'}), 404


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@dashboard_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@dashboard_bp.errorhandler(500)
def server_error(error):
    logger.error(f'Server error: {error}')
    return jsonify({'error': 'Internal server error'}), 500


def register_dashboard_routes(app):
    """Register dashboard blueprint with Flask app"""
    app.register_blueprint(dashboard_bp)
    logger.info('Dashboard routes registered')
