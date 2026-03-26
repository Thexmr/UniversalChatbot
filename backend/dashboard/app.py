"""
UniversalChatbot - Dashboard App
Flask-based web dashboard with WebSocket support
"""
import json
import os
from datetime import datetime, date
from pathlib import Path
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import threading

# Global reference to chat_manager (set from main.py)
chat_manager_ref = None
llm_client_ref = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'universal-chatbot-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


def log_file_path():
    """Get path to log file"""
    # Look for logs directory in various locations
    possible_paths = [
        Path(__file__).parent.parent / "logs" / "chat.log",
        Path(__file__).parent.parent.parent / "logs" / "chat.log",
        Path.cwd() / "logs" / "chat.log",
    ]
    for path in possible_paths:
        if path.exists() or path.parent.exists():
            return str(path)
    return str(possible_paths[0])


def get_chat_manager():
    """Get chat manager reference"""
    return chat_manager_ref


def get_llm_client():
    """Get LLM client reference""""
    return llm_client_ref


@app.route("/")
def index():
    """Main dashboard page"""
    return render_template("index.html")


@app.route("/api/logs")
def get_logs():
    """Get last 100 log entries"""
    logs = []
    log_path = log_file_path()
    
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-100:]:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Handle non-JSON lines
                            logs.append({
                                "timestamp": datetime.now().isoformat(),
                                "level": "INFO",
                                "component": "legacy",
                                "message": line
                            })
    except Exception as e:
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "component": "dashboard",
            "message": f"Failed to read logs: {str(e)}"
        })
    
    return jsonify(logs)


@app.route("/api/stats")
def get_stats():
    """Get dashboard stats"""
    stats = {
        "sessions": 0,
        "messages_today": 0,
        "llm_status": False,
        "timestamp": datetime.now().isoformat()
    }
    
    # Get session count
    cm = get_chat_manager()
    if cm:
        stats["sessions"] = len(cm.sessions)
    
    # Get message count for today
    stats["messages_today"] = get_today_message_count()
    
    # Get LLM status
    llm = get_llm_client()
    if llm:
        try:
            stats["llm_status"] = llm.is_configured() if hasattr(llm, 'is_configured') else True
        except:
            stats["llm_status"] = False
    
    return jsonify(stats)


@app.route("/api/sessions")
def get_sessions():
    """Get active sessions"""
    cm = get_chat_manager()
    if not cm:
        return jsonify([])
    
    sessions = []
    for session_id, session_data in cm.sessions.items():
        sessions.append({
            "id": session_id,
            "created_at": session_data.get("created_at", "unknown"),
            "message_count": len(session_data.get("messages", [])),
            "platform": session_data.get("platform", "unknown")
        })
    
    return jsonify(sessions)


def get_today_message_count():
    """Count messages from today's logs"""
    log_path = log_file_path()
    count = 0
    today = date.today().isoformat()
    
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and today in line:
                        count += 1
    except:
        pass
    
    return count


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print("Dashboard client connected")
    socketio.emit('status', {'message': 'Connected to UniversalChatbot dashboard'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print("Dashboard client disconnected")


def broadcast_log(log_entry):
    """Broadcast new log entry to all connected clients"""
    try:
        socketio.emit('new_log', log_entry)
    except:
        pass


def start_dashboard(host='0.0.0.0', port=5000, debug=False, chat_manager=None, llm_client=None):
    """
    Start the dashboard server
    
    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
        chat_manager: Reference to chat manager instance
        llm_client: Reference to LLM client instance
    """
    global chat_manager_ref, llm_client_ref
    
    chat_manager_ref = chat_manager
    llm_client_ref = llm_client
    
    print(f"Starting dashboard on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)


def start_dashboard_thread(chat_manager=None, llm_client=None, port=5000):
    """
    Start dashboard in a background thread
    
    Returns:
        threading.Thread: The dashboard thread
    """
    global chat_manager_ref, llm_client_ref
    
    chat_manager_ref = chat_manager
    llm_client_ref = llm_client
    
    dashboard_thread = threading.Thread(
        target=lambda: socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True),
        daemon=True
    )
    dashboard_thread.start()
    print(f"Dashboard started on http://localhost:{port}")
    return dashboard_thread


if __name__ == "__main__":
    start_dashboard(debug=True)
