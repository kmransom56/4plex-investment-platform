"""
Real-time Processing Status System for 4-plex Investment Platform
Provides live status updates, progress tracking, and WebSocket communication
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import weakref
import threading
from concurrent.futures import ThreadPoolExecutor
import queue

# WebSocket support (optional - graceful degradation)
try:
    import websockets
    import websocket_server
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logging.warning("WebSocket libraries not available. Real-time updates will use polling.")

# Redis support for distributed systems (optional)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available. Using in-memory status tracking.")

from models import ProcessingJob
from database.connection import DatabaseManager

class StatusType(Enum):
    """Status update types"""
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_PROGRESS = "job_progress"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    DOCUMENT_PROCESSED = "document_processed"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_STATUS = "system_status"

class Priority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class StatusUpdate:
    """Status update message structure"""
    id: str
    type: StatusType
    priority: Priority
    timestamp: datetime
    property_id: Optional[str] = None
    job_id: Optional[str] = None
    message: str = ""
    progress: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['type'] = self.type.value
        result['priority'] = self.priority.value
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusUpdate':
        """Create from dictionary"""
        data['type'] = StatusType(data['type'])
        data['priority'] = Priority(data['priority'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class StatusSubscription:
    """Represents a client subscription to status updates"""
    
    def __init__(
        self,
        subscription_id: str,
        callback: Callable[[StatusUpdate], None],
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        self.id = subscription_id
        self.callback = callback
        self.filters = filters or {}
        self.user_id = user_id
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True
    
    def matches(self, status_update: StatusUpdate) -> bool:
        """Check if status update matches subscription filters"""
        if not self.is_active:
            return False
        
        # Check property filter
        if 'property_ids' in self.filters:
            if status_update.property_id not in self.filters['property_ids']:
                return False
        
        # Check job filter
        if 'job_ids' in self.filters:
            if status_update.job_id not in self.filters['job_ids']:
                return False
        
        # Check status type filter
        if 'status_types' in self.filters:
            if status_update.type not in self.filters['status_types']:
                return False
        
        # Check priority filter
        if 'min_priority' in self.filters:
            if status_update.priority.value < self.filters['min_priority'].value:
                return False
        
        # Check user filter
        if 'user_id' in self.filters:
            if status_update.user_id != self.filters['user_id']:
                return False
        
        return True

class StatusSystemCore:
    """Core status system without WebSocket dependencies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager(config.get('database', {}))
        
        # Subscription management
        self.subscriptions: Dict[str, StatusSubscription] = {}
        self.subscription_lock = threading.Lock()
        
        # Message queuing
        self.message_queue = queue.PriorityQueue()
        self.message_history: List[StatusUpdate] = []
        self.max_history = config.get('status_system', {}).get('max_history', 1000)
        
        # Configuration
        self.cleanup_interval = config.get('status_system', {}).get('cleanup_interval_minutes', 15)
        self.max_subscription_age_hours = config.get('status_system', {}).get('max_subscription_age_hours', 24)
        
        # Background processing
        self.is_running = False
        self.background_thread = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Redis connection (if available)
        self.redis_client = None
        if REDIS_AVAILABLE:
            redis_config = config.get('redis', {})
            if redis_config:
                try:
                    self.redis_client = redis.Redis(
                        host=redis_config.get('host', 'localhost'),
                        port=redis_config.get('port', 6379),
                        db=redis_config.get('db', 0),
                        decode_responses=True
                    )
                    self.redis_client.ping()
                    self.logger.info("Connected to Redis for distributed status updates")
                except Exception as e:
                    self.logger.warning(f"Failed to connect to Redis: {e}")
                    self.redis_client = None
    
    def start(self):
        """Start the status system background processing"""
        if self.is_running:
            return
        
        self.is_running = True
        self.background_thread = threading.Thread(target=self._background_worker, daemon=True)
        self.background_thread.start()
        
        self.logger.info("Status system started")
    
    def stop(self):
        """Stop the status system"""
        self.is_running = False
        
        if self.background_thread:
            self.background_thread.join(timeout=5.0)
        
        self.executor.shutdown(wait=True)
        
        # Close Redis connection
        if self.redis_client:
            self.redis_client.close()
        
        self.logger.info("Status system stopped")
    
    def publish_status(
        self,
        status_type: StatusType,
        message: str,
        priority: Priority = Priority.NORMAL,
        property_id: Optional[str] = None,
        job_id: Optional[str] = None,
        progress: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Publish a status update
        
        Args:
            status_type: Type of status update
            message: Human-readable message
            priority: Message priority
            property_id: Associated property ID
            job_id: Associated job ID
            progress: Progress percentage (0-100)
            data: Additional data payload
            user_id: User who initiated the action
            
        Returns:
            Status update ID
        """
        try:
            status_update = StatusUpdate(
                id=f"status_{uuid.uuid4().hex[:12]}",
                type=status_type,
                priority=priority,
                timestamp=datetime.now(),
                property_id=property_id,
                job_id=job_id,
                message=message,
                progress=progress,
                data=data,
                user_id=user_id
            )
            
            # Add to message queue for processing with timestamp for uniqueness
            import time
            priority_value = priority.value * -1  # Higher priority = lower number
            timestamp = time.time()
            self.message_queue.put((priority_value, timestamp, status_update))
            
            # Add to history
            self.message_history.append(status_update)
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)
            
            # Publish to Redis if available
            if self.redis_client:
                try:
                    self.redis_client.publish('status_updates', json.dumps(status_update.to_dict()))
                except Exception as e:
                    self.logger.warning(f"Failed to publish to Redis: {e}")
            
            # Update database if it's a job update
            if job_id and status_type in [StatusType.JOB_PROGRESS, StatusType.JOB_COMPLETED, StatusType.JOB_FAILED]:
                self._update_job_status(job_id, status_update)
            
            self.logger.debug(f"Published status: {status_type.value} - {message}")
            return status_update.id
            
        except Exception as e:
            self.logger.error(f"Error publishing status: {e}")
            raise
    
    def subscribe(
        self,
        callback: Callable[[StatusUpdate], None],
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Subscribe to status updates
        
        Args:
            callback: Function to call with status updates
            filters: Optional filters for updates
            user_id: User ID for the subscription
            session_id: Session ID for the subscription
            
        Returns:
            Subscription ID
        """
        try:
            subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
            
            subscription = StatusSubscription(
                subscription_id=subscription_id,
                callback=callback,
                filters=filters,
                user_id=user_id,
                session_id=session_id
            )
            
            with self.subscription_lock:
                self.subscriptions[subscription_id] = subscription
            
            self.logger.info(f"New subscription created: {subscription_id}")
            return subscription_id
            
        except Exception as e:
            self.logger.error(f"Error creating subscription: {e}")
            raise
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from status updates
        
        Args:
            subscription_id: Subscription to remove
            
        Returns:
            True if subscription was found and removed
        """
        try:
            with self.subscription_lock:
                if subscription_id in self.subscriptions:
                    self.subscriptions[subscription_id].is_active = False
                    del self.subscriptions[subscription_id]
                    self.logger.info(f"Subscription removed: {subscription_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing subscription {subscription_id}: {e}")
            return False
    
    def get_recent_status(
        self,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent status updates
        
        Args:
            limit: Maximum number of updates to return
            filters: Optional filters to apply
            
        Returns:
            List of recent status updates
        """
        try:
            filtered_updates = []
            
            for update in reversed(self.message_history):
                if filters:
                    # Apply filters
                    if 'property_ids' in filters and update.property_id not in filters['property_ids']:
                        continue
                    if 'job_ids' in filters and update.job_id not in filters['job_ids']:
                        continue
                    if 'status_types' in filters and update.type not in filters['status_types']:
                        continue
                    if 'min_priority' in filters and update.priority.value < filters['min_priority'].value:
                        continue
                
                filtered_updates.append(update.to_dict())
                
                if len(filtered_updates) >= limit:
                    break
            
            return filtered_updates
            
        except Exception as e:
            self.logger.error(f"Error getting recent status: {e}")
            return []
    
    def get_job_status_stream(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get all status updates for a specific job
        
        Args:
            job_id: Job ID to get updates for
            
        Returns:
            List of status updates for the job
        """
        try:
            job_updates = []
            
            for update in self.message_history:
                if update.job_id == job_id:
                    job_updates.append(update.to_dict())
            
            # Sort by timestamp
            job_updates.sort(key=lambda x: x['timestamp'])
            
            return job_updates
            
        except Exception as e:
            self.logger.error(f"Error getting job status stream for {job_id}: {e}")
            return []
    
    def get_property_status_stream(self, property_id: str) -> List[Dict[str, Any]]:
        """
        Get all status updates for a specific property
        
        Args:
            property_id: Property ID to get updates for
            
        Returns:
            List of status updates for the property
        """
        try:
            property_updates = []
            
            for update in self.message_history:
                if update.property_id == property_id:
                    property_updates.append(update.to_dict())
            
            # Sort by timestamp
            property_updates.sort(key=lambda x: x['timestamp'])
            
            return property_updates
            
        except Exception as e:
            self.logger.error(f"Error getting property status stream for {property_id}: {e}")
            return []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics
        
        Returns:
            Dictionary of system statistics
        """
        try:
            with self.subscription_lock:
                active_subscriptions = len([s for s in self.subscriptions.values() if s.is_active])
            
            return {
                'active_subscriptions': active_subscriptions,
                'total_messages': len(self.message_history),
                'queue_size': self.message_queue.qsize(),
                'uptime_seconds': (datetime.now() - getattr(self, 'start_time', datetime.now())).total_seconds(),
                'redis_connected': self.redis_client is not None,
                'websocket_available': WEBSOCKET_AVAILABLE
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {}
    
    def _background_worker(self):
        """Background thread for processing status updates"""
        self.start_time = datetime.now()
        last_cleanup = datetime.now()
        
        while self.is_running:
            try:
                # Process message queue
                try:
                    priority, timestamp, status_update = self.message_queue.get(timeout=1.0)
                    self._process_status_update(status_update)
                except queue.Empty:
                    pass
                
                # Periodic cleanup
                if datetime.now() - last_cleanup > timedelta(minutes=self.cleanup_interval):
                    self._cleanup_subscriptions()
                    last_cleanup = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error in background worker: {e}")
    
    def _process_status_update(self, status_update: StatusUpdate):
        """Process and distribute a status update"""
        try:
            # Send to matching subscriptions
            with self.subscription_lock:
                for subscription in list(self.subscriptions.values()):
                    if subscription.matches(status_update):
                        try:
                            subscription.callback(status_update)
                            subscription.last_activity = datetime.now()
                        except Exception as e:
                            self.logger.warning(f"Error in subscription callback {subscription.id}: {e}")
                            # Remove broken subscription
                            subscription.is_active = False
            
        except Exception as e:
            self.logger.error(f"Error processing status update: {e}")
    
    def _cleanup_subscriptions(self):
        """Remove old or inactive subscriptions"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.max_subscription_age_hours)
            removed_count = 0
            
            with self.subscription_lock:
                subscription_ids_to_remove = []
                
                for sub_id, subscription in self.subscriptions.items():
                    if (not subscription.is_active or 
                        subscription.last_activity < cutoff_time):
                        subscription_ids_to_remove.append(sub_id)
                
                for sub_id in subscription_ids_to_remove:
                    del self.subscriptions[sub_id]
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} inactive subscriptions")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up subscriptions: {e}")
    
    def _update_job_status(self, job_id: str, status_update: StatusUpdate):
        """Update job status in database"""
        try:
            if status_update.type == StatusType.JOB_PROGRESS:
                self.db_manager.update_job_status(
                    job_id, 
                    'processing', 
                    status_update.progress
                )
            elif status_update.type == StatusType.JOB_COMPLETED:
                self.db_manager.update_job_status(
                    job_id, 
                    'completed', 
                    100,
                    results=status_update.data
                )
            elif status_update.type == StatusType.JOB_FAILED:
                self.db_manager.update_job_status(
                    job_id, 
                    'failed', 
                    status_update.progress or 0,
                    error=status_update.message
                )
                
        except Exception as e:
            self.logger.warning(f"Error updating job status in database: {e}")

# WebSocket Server Implementation (if available)
if WEBSOCKET_AVAILABLE:
    class WebSocketStatusServer:
        """WebSocket server for real-time status updates"""
        
        def __init__(self, status_system: StatusSystemCore, port: int = 8765):
            self.status_system = status_system
            self.port = port
            self.server = None
            self.clients: Set[websockets.WebSocketServerProtocol] = set()
            self.client_subscriptions: Dict[str, str] = {}  # websocket id -> subscription id
        
        async def start_server(self):
            """Start the WebSocket server"""
            try:
                self.server = await websockets.serve(
                    self.handle_client,
                    "localhost",
                    self.port
                )
                self.status_system.logger.info(f"WebSocket server started on port {self.port}")
                
            except Exception as e:
                self.status_system.logger.error(f"Failed to start WebSocket server: {e}")
                raise
        
        async def stop_server(self):
            """Stop the WebSocket server"""
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self.status_system.logger.info("WebSocket server stopped")
        
        async def handle_client(self, websocket, path):
            """Handle WebSocket client connection"""
            client_id = f"ws_{id(websocket)}"
            self.clients.add(websocket)
            
            try:
                self.status_system.logger.info(f"WebSocket client connected: {client_id}")
                
                # Send initial status
                await self.send_to_client(websocket, {
                    'type': 'connection_established',
                    'client_id': client_id,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Handle client messages
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self.handle_client_message(websocket, data)
                    except json.JSONDecodeError:
                        await self.send_error(websocket, "Invalid JSON message")
                    except Exception as e:
                        await self.send_error(websocket, f"Error processing message: {e}")
                
            except websockets.exceptions.ConnectionClosed:
                self.status_system.logger.info(f"WebSocket client disconnected: {client_id}")
            except Exception as e:
                self.status_system.logger.error(f"Error handling WebSocket client {client_id}: {e}")
            finally:
                self.clients.discard(websocket)
                # Clean up subscription
                if client_id in self.client_subscriptions:
                    self.status_system.unsubscribe(self.client_subscriptions[client_id])
                    del self.client_subscriptions[client_id]
        
        async def handle_client_message(self, websocket, data: Dict[str, Any]):
            """Handle message from WebSocket client"""
            message_type = data.get('type')
            client_id = f"ws_{id(websocket)}"
            
            if message_type == 'subscribe':
                # Create subscription
                filters = data.get('filters', {})
                
                def callback(status_update: StatusUpdate):
                    # Send status update to client
                    asyncio.create_task(
                        self.send_to_client(websocket, {
                            'type': 'status_update',
                            'data': status_update.to_dict()
                        })
                    )
                
                subscription_id = self.status_system.subscribe(
                    callback=callback,
                    filters=filters,
                    session_id=client_id
                )
                
                self.client_subscriptions[client_id] = subscription_id
                
                await self.send_to_client(websocket, {
                    'type': 'subscription_created',
                    'subscription_id': subscription_id
                })
            
            elif message_type == 'get_recent_status':
                # Send recent status updates
                limit = data.get('limit', 50)
                filters = data.get('filters', {})
                
                recent_updates = self.status_system.get_recent_status(limit=limit, filters=filters)
                
                await self.send_to_client(websocket, {
                    'type': 'recent_status',
                    'data': recent_updates
                })
            
            elif message_type == 'get_job_status':
                # Send job-specific status updates
                job_id = data.get('job_id')
                if job_id:
                    job_updates = self.status_system.get_job_status_stream(job_id)
                    await self.send_to_client(websocket, {
                        'type': 'job_status',
                        'job_id': job_id,
                        'data': job_updates
                    })
                else:
                    await self.send_error(websocket, "job_id is required")
            
            elif message_type == 'ping':
                # Respond to ping
                await self.send_to_client(websocket, {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                })
        
        async def send_to_client(self, websocket, data: Dict[str, Any]):
            """Send data to WebSocket client"""
            try:
                await websocket.send(json.dumps(data))
            except websockets.exceptions.ConnectionClosed:
                pass  # Client disconnected
            except Exception as e:
                self.status_system.logger.error(f"Error sending to WebSocket client: {e}")
        
        async def send_error(self, websocket, error_message: str):
            """Send error message to client"""
            await self.send_to_client(websocket, {
                'type': 'error',
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            })
        
        def broadcast_message(self, data: Dict[str, Any]):
            """Broadcast message to all connected clients"""
            if not self.clients:
                return
            
            message = json.dumps(data)
            disconnected_clients = set()
            
            for client in self.clients:
                try:
                    asyncio.create_task(client.send(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
                except Exception as e:
                    self.status_system.logger.error(f"Error broadcasting to client: {e}")
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            self.clients -= disconnected_clients

# Main Status System Class
class StatusSystem:
    """Complete real-time processing status system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize core system
        self.core = StatusSystemCore(config)
        
        # Initialize WebSocket server if available
        self.websocket_server = None
        if WEBSOCKET_AVAILABLE:
            websocket_config = config.get('websocket', {})
            if websocket_config.get('enabled', True):
                port = websocket_config.get('port', 8765)
                self.websocket_server = WebSocketStatusServer(self.core, port)
    
    async def start(self):
        """Start the complete status system"""
        # Start core system
        self.core.start()
        
        # Start WebSocket server
        if self.websocket_server:
            await self.websocket_server.start_server()
        
        self.logger.info("Status system fully started")
    
    async def stop(self):
        """Stop the status system"""
        # Stop WebSocket server
        if self.websocket_server:
            await self.websocket_server.stop_server()
        
        # Stop core system
        self.core.stop()
        
        self.logger.info("Status system stopped")
    
    # Delegate all other methods to core system
    def __getattr__(self, name):
        return getattr(self.core, name)

# Helper Classes for Easy Integration

class JobStatusTracker:
    """Helper class for tracking job status throughout processing"""
    
    def __init__(self, status_system: StatusSystem, job_id: str, property_id: Optional[str] = None):
        self.status_system = status_system
        self.job_id = job_id
        self.property_id = property_id
        self.start_time = datetime.now()
        self.current_progress = 0
    
    def update_progress(self, progress: int, message: str, data: Optional[Dict[str, Any]] = None):
        """Update job progress"""
        self.current_progress = progress
        self.status_system.publish_status(
            StatusType.JOB_PROGRESS,
            message,
            Priority.NORMAL,
            property_id=self.property_id,
            job_id=self.job_id,
            progress=progress,
            data=data
        )
    
    def mark_completed(self, message: str = "Job completed successfully", data: Optional[Dict[str, Any]] = None):
        """Mark job as completed"""
        elapsed = datetime.now() - self.start_time
        completion_data = {
            'elapsed_seconds': elapsed.total_seconds(),
            'completed_at': datetime.now().isoformat()
        }
        if data:
            completion_data.update(data)
        
        self.status_system.publish_status(
            StatusType.JOB_COMPLETED,
            message,
            Priority.HIGH,
            property_id=self.property_id,
            job_id=self.job_id,
            progress=100,
            data=completion_data
        )
    
    def mark_failed(self, error_message: str, data: Optional[Dict[str, Any]] = None):
        """Mark job as failed"""
        elapsed = datetime.now() - self.start_time
        failure_data = {
            'elapsed_seconds': elapsed.total_seconds(),
            'failed_at': datetime.now().isoformat(),
            'error': error_message
        }
        if data:
            failure_data.update(data)
        
        self.status_system.publish_status(
            StatusType.JOB_FAILED,
            error_message,
            Priority.HIGH,
            property_id=self.property_id,
            job_id=self.job_id,
            progress=self.current_progress,
            data=failure_data
        )
    
    def log_milestone(self, milestone: str, data: Optional[Dict[str, Any]] = None):
        """Log an important milestone"""
        self.status_system.publish_status(
            StatusType.DOCUMENT_PROCESSED,
            milestone,
            Priority.NORMAL,
            property_id=self.property_id,
            job_id=self.job_id,
            data=data
        )

class PropertyStatusTracker:
    """Helper class for tracking property-level status updates"""
    
    def __init__(self, status_system: StatusSystem, property_id: str):
        self.status_system = status_system
        self.property_id = property_id
    
    def log_stage_change(self, old_stage: str, new_stage: str, message: Optional[str] = None):
        """Log property stage change"""
        default_message = f"Property stage changed from {old_stage} to {new_stage}"
        self.status_system.publish_status(
            StatusType.SYSTEM_STATUS,
            message or default_message,
            Priority.NORMAL,
            property_id=self.property_id,
            data={'old_stage': old_stage, 'new_stage': new_stage}
        )
    
    def log_analysis_started(self, analysis_type: str):
        """Log analysis start"""
        self.status_system.publish_status(
            StatusType.ANALYSIS_STARTED,
            f"Started {analysis_type} analysis",
            Priority.NORMAL,
            property_id=self.property_id,
            data={'analysis_type': analysis_type}
        )
    
    def log_analysis_completed(self, analysis_type: str, results: Dict[str, Any]):
        """Log analysis completion"""
        self.status_system.publish_status(
            StatusType.ANALYSIS_COMPLETED,
            f"Completed {analysis_type} analysis",
            Priority.HIGH,
            property_id=self.property_id,
            data={'analysis_type': analysis_type, 'results': results}
        )