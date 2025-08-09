"""
Notifications System - Real-time alerts and updates
"""
import json
import sqlite3
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class NotificationType(Enum):
    TEST_COMPLETED = "test_completed"
    MODEL_ADDED = "model_added"
    SHARE_VIEWED = "share_viewed"
    COMMENT_ADDED = "comment_added"
    WORKSPACE_INVITE = "workspace_invite"
    SYSTEM_ALERT = "system_alert"
    LEADERBOARD_UPDATE = "leaderboard_update"

class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationManager:
    """Manages notifications and alerts"""
    
    def __init__(self, db_path: str = "notifications.db"):
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize notifications database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Notifications table (enhanced from auth.py)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                data TEXT DEFAULT '{}',
                is_read BOOLEAN DEFAULT 0,
                is_email_sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        # Notification preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                email_enabled BOOLEAN DEFAULT 1,
                push_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, notification_type)
            )
        """)
        
        # Notification templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_type TEXT NOT NULL UNIQUE,
                title_template TEXT NOT NULL,
                message_template TEXT NOT NULL,
                email_subject_template TEXT,
                email_body_template TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Email queue for batch processing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email_address TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize default templates
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Create default notification templates"""
        default_templates = [
            {
                "notification_type": NotificationType.TEST_COMPLETED.value,
                "title_template": "Test Completed: {test_name}",
                "message_template": "Your test '{test_name}' on model '{model_name}' has completed with a score of {score:.2f}.",
                "email_subject_template": "AI Safety Test Results Available",
                "email_body_template": "Hi {user_name},\n\nYour test '{test_name}' on model '{model_name}' has completed.\n\nFinal Score: {score:.2f}\nExecution Time: {execution_time:.2f}s\n\nView detailed results: {results_url}\n\nBest regards,\nAI Safety Benchmark Team"
            },
            {
                "notification_type": NotificationType.MODEL_ADDED.value,
                "title_template": "New Model Added: {model_name}",
                "message_template": "A new model '{model_name}' from {provider} has been added to the leaderboard.",
                "email_subject_template": "New Model Available for Testing",
                "email_body_template": "Hi {user_name},\n\nA new model is now available:\n\nModel: {model_name}\nProvider: {provider}\nDescription: {description}\n\nStart testing: {model_url}\n\nBest regards,\nAI Safety Benchmark Team"
            },
            {
                "notification_type": NotificationType.SHARE_VIEWED.value,
                "title_template": "Your Share Was Viewed",
                "message_template": "'{share_title}' has been viewed {view_count} times.",
                "email_subject_template": "Your Shared Content Has New Views",
                "email_body_template": "Hi {user_name},\n\nYour shared content '{share_title}' has been viewed {view_count} times.\n\nView analytics: {share_url}\n\nBest regards,\nAI Safety Benchmark Team"
            },
            {
                "notification_type": NotificationType.COMMENT_ADDED.value,
                "title_template": "New Comment on '{content_title}'",
                "message_template": "Someone commented on your shared content: '{comment_preview}'",
                "email_subject_template": "New Comment on Your Shared Content",
                "email_body_template": "Hi {user_name},\n\nYou have a new comment on '{content_title}':\n\n\"{comment_text}\"\n\nReply to comment: {content_url}\n\nBest regards,\nAI Safety Benchmark Team"
            },
            {
                "notification_type": NotificationType.WORKSPACE_INVITE.value,
                "title_template": "Workspace Invitation: {workspace_name}",
                "message_template": "You've been invited to join workspace '{workspace_name}' as a {role}.",
                "email_subject_template": "Team Workspace Invitation",
                "email_body_template": "Hi {user_name},\n\nYou've been invited to join the workspace '{workspace_name}' as a {role}.\n\nWorkspace Description: {workspace_description}\n\nAccept invitation: {workspace_url}\n\nBest regards,\nAI Safety Benchmark Team"
            },
            {
                "notification_type": NotificationType.SYSTEM_ALERT.value,
                "title_template": "System Alert: {alert_title}",
                "message_template": "{alert_message}",
                "email_subject_template": "System Alert - {alert_title}",
                "email_body_template": "Hi {user_name},\n\nSystem Alert: {alert_title}\n\n{alert_message}\n\nFor support, contact: support@aisafety.example.com\n\nBest regards,\nAI Safety Benchmark Team"
            },
            {
                "notification_type": NotificationType.LEADERBOARD_UPDATE.value,
                "title_template": "Leaderboard Update",
                "message_template": "New leaderboard rankings are available. Your model '{model_name}' is now ranked #{rank}.",
                "email_subject_template": "Leaderboard Rankings Updated",
                "email_body_template": "Hi {user_name},\n\nThe leaderboard has been updated!\n\nYour model '{model_name}' is now ranked #{rank} with a score of {score:.2f}.\n\n{rank_change_message}\n\nView leaderboard: {leaderboard_url}\n\nBest regards,\nAI Safety Benchmark Team"
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for template in default_templates:
            cursor.execute("""
                INSERT OR REPLACE INTO notification_templates 
                (notification_type, title_template, message_template, 
                 email_subject_template, email_body_template)
                VALUES (?, ?, ?, ?, ?)
            """, (
                template["notification_type"],
                template["title_template"],
                template["message_template"],
                template["email_subject_template"],
                template["email_body_template"]
            ))
        
        conn.commit()
        conn.close()
    
    def create_notification(self, user_id: int, notification_type: NotificationType,
                           data: Dict[str, Any], priority: NotificationPriority = NotificationPriority.MEDIUM,
                           expires_in_days: Optional[int] = 30) -> int:
        """Create a new notification"""
        # Get template
        template = self._get_notification_template(notification_type)
        if not template:
            raise ValueError(f"No template found for notification type: {notification_type}")
        
        # Format title and message
        try:
            title = template["title_template"].format(**data)
            message = template["message_template"].format(**data)
        except KeyError as e:
            raise ValueError(f"Missing data for template formatting: {e}")
        
        # Set expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Insert notification
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notifications 
            (user_id, notification_type, title, message, priority, data, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, notification_type.value, title, message, priority.value, 
              json.dumps(data), expires_at))
        
        notification_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Check if email notification should be sent
        if self._should_send_email(user_id, notification_type):
            self._queue_email_notification(notification_id, user_id, notification_type, data)
        
        return notification_id
    
    def _get_notification_template(self, notification_type: NotificationType) -> Optional[Dict[str, Any]]:
        """Get notification template"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title_template, message_template, email_subject_template, email_body_template
            FROM notification_templates
            WHERE notification_type = ? AND is_active = 1
        """, (notification_type.value,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "title_template": row[0],
                "message_template": row[1],
                "email_subject_template": row[2],
                "email_body_template": row[3]
            }
        return None
    
    def _should_send_email(self, user_id: int, notification_type: NotificationType) -> bool:
        """Check if email notification should be sent based on user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT email_enabled FROM notification_preferences
            WHERE user_id = ? AND notification_type = ?
        """, (user_id, notification_type.value))
        
        row = cursor.fetchone()
        conn.close()
        
        # Default to enabled if no preference set
        return row[0] if row else True
    
    def _queue_email_notification(self, notification_id: int, user_id: int, 
                                 notification_type: NotificationType, data: Dict[str, Any]):
        """Queue email notification for sending"""
        # Get user email (would need to integrate with user management)
        user_email = data.get('user_email', f'user{user_id}@example.com')  # Placeholder
        
        # Get email template
        template = self._get_notification_template(notification_type)
        if not template or not template.get("email_subject_template"):
            return
        
        try:
            subject = template["email_subject_template"].format(**data)
            body = template["email_body_template"].format(**data)
        except KeyError:
            return  # Skip if template formatting fails
        
        # Queue email
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO email_queue (user_id, email_address, subject, body, priority)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, user_email, subject, body, "medium"))
        
        conn.commit()
        conn.close()
    
    def get_user_notifications(self, user_id: int, unread_only: bool = False,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT id, notification_type, title, message, priority, data,
                   is_read, created_at, read_at, expires_at
            FROM notifications
            WHERE user_id = ?
        """
        
        if unread_only:
            query += " AND is_read = 0"
        
        # Filter out expired notifications
        query += " AND (expires_at IS NULL OR expires_at > datetime('now'))"
        query += " ORDER BY created_at DESC LIMIT ?"
        
        cursor.execute(query, (user_id, limit))
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                "id": row[0],
                "notification_type": row[1],
                "title": row[2],
                "message": row[3],
                "priority": row[4],
                "data": json.loads(row[5]),
                "is_read": bool(row[6]),
                "created_at": row[7],
                "read_at": row[8],
                "expires_at": row[9]
            })
        
        conn.close()
        return notifications
    
    def mark_notification_read(self, notification_id: int, user_id: int):
        """Mark notification as read"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE notifications 
            SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (notification_id, user_id))
        
        conn.commit()
        conn.close()
    
    def mark_all_read(self, user_id: int):
        """Mark all notifications as read for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE notifications 
            SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND is_read = 0
        """, (user_id,))
        
        conn.commit()
        conn.close()
    
    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM notifications
            WHERE user_id = ? AND is_read = 0 
            AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (user_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def update_notification_preferences(self, user_id: int, notification_type: NotificationType,
                                      email_enabled: bool = True, push_enabled: bool = True):
        """Update user notification preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO notification_preferences
            (user_id, notification_type, email_enabled, push_enabled, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, notification_type.value, email_enabled, push_enabled))
        
        conn.commit()
        conn.close()
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Dict[str, bool]]:
        """Get user notification preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT notification_type, email_enabled, push_enabled
            FROM notification_preferences
            WHERE user_id = ?
        """, (user_id,))
        
        preferences = {}
        for row in cursor.fetchall():
            preferences[row[0]] = {
                "email_enabled": bool(row[1]),
                "push_enabled": bool(row[2])
            }
        
        conn.close()
        return preferences
    
    def send_system_alert(self, message: str, title: str = "System Alert",
                         priority: NotificationPriority = NotificationPriority.HIGH,
                         target_users: Optional[List[int]] = None):
        """Send system-wide alert to users"""
        # If no target users specified, send to all active users
        if target_users is None:
            # Would integrate with user management to get active users
            target_users = [1, 2, 3]  # Placeholder
        
        for user_id in target_users:
            self.create_notification(
                user_id=user_id,
                notification_type=NotificationType.SYSTEM_ALERT,
                data={
                    "alert_title": title,
                    "alert_message": message,
                    "user_name": f"User{user_id}",  # Would get real name
                    "user_email": f"user{user_id}@example.com"  # Would get real email
                },
                priority=priority
            )

def render_notifications_panel():
    """Render notifications panel in sidebar"""
    if 'user' not in st.session_state:
        return
    
    if 'notification_manager' not in st.session_state:
        st.session_state.notification_manager = NotificationManager()
    
    notif_manager = st.session_state.notification_manager
    user = st.session_state.user
    
    # Get unread count
    unread_count = notif_manager.get_unread_count(user["id"])
    
    # Notifications header with badge
    if unread_count > 0:
        st.sidebar.markdown(f"### 🔔 Notifications ({unread_count})")
    else:
        st.sidebar.markdown("### 🔔 Notifications")
    
    # Quick actions
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔔 View All", key="view_all_notifications"):
            st.session_state.show_notifications_page = True
    
    with col2:
        if unread_count > 0:
            if st.button("✅ Mark All Read", key="mark_all_read"):
                notif_manager.mark_all_read(user["id"])
                st.rerun()
    
    # Recent notifications preview
    recent_notifications = notif_manager.get_user_notifications(user["id"], limit=3)
    
    if recent_notifications:
        for notification in recent_notifications:
            with st.sidebar.container():
                # Priority indicator
                priority_icons = {
                    "low": "🔵",
                    "medium": "🟡", 
                    "high": "🟠",
                    "urgent": "🔴"
                }
                priority_icon = priority_icons.get(notification["priority"], "🔵")
                
                # Read/unread indicator
                read_icon = "📖" if notification["is_read"] else "🆕"
                
                st.sidebar.write(f"{priority_icon} {read_icon} **{notification['title'][:30]}...**")
                st.sidebar.write(f"*{notification['message'][:50]}...*")
                st.sidebar.write(f"*{notification['created_at'][:16]}*")
                
                if not notification["is_read"]:
                    if st.sidebar.button(f"Mark Read", key=f"read_{notification['id']}"):
                        notif_manager.mark_notification_read(notification["id"], user["id"])
                        st.rerun()
                
                st.sidebar.divider()
    else:
        st.sidebar.info("No notifications")

def render_notifications_page():
    """Render full notifications management page"""
    st.title("🔔 Notifications")
    
    if 'user' not in st.session_state:
        st.warning("Please log in to view notifications.")
        return
    
    if 'notification_manager' not in st.session_state:
        st.session_state.notification_manager = NotificationManager()
    
    notif_manager = st.session_state.notification_manager
    user = st.session_state.user
    
    # Tabs for different notification views
    tab1, tab2, tab3 = st.tabs(["📬 All Notifications", "⚙️ Preferences", "📊 Statistics"])
    
    with tab1:
        render_notifications_list(notif_manager, user)
    
    with tab2:
        render_notification_preferences(notif_manager, user)
    
    with tab3:
        render_notification_statistics(notif_manager, user)

def render_notifications_list(notif_manager: NotificationManager, user: Dict[str, Any]):
    """Render notifications list"""
    st.subheader("Your Notifications")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_unread_only = st.checkbox("Unread only")
    
    with col2:
        priority_filter = st.selectbox("Priority", ["All", "Low", "Medium", "High", "Urgent"])
    
    with col3:
        if st.button("🗑️ Clear All Read"):
            # Would implement clear read notifications
            st.info("Clear read notifications functionality would be implemented here")
    
    # Get notifications
    notifications = notif_manager.get_user_notifications(
        user["id"], 
        unread_only=show_unread_only,
        limit=100
    )
    
    # Filter by priority if specified
    if priority_filter != "All":
        notifications = [n for n in notifications if n["priority"].lower() == priority_filter.lower()]
    
    if notifications:
        st.write(f"**{len(notifications)} notifications**")
        
        for notification in notifications:
            with st.expander(f"{'🆕' if not notification['is_read'] else '📖'} {notification['title']}", 
                           expanded=not notification['is_read']):
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Priority and type badges
                    priority_colors = {
                        "low": "🔵",
                        "medium": "🟡",
                        "high": "🟠", 
                        "urgent": "🔴"
                    }
                    priority_icon = priority_colors.get(notification["priority"], "🔵")
                    
                    st.write(f"{priority_icon} **{notification['priority'].title()} Priority** | Type: {notification['notification_type']}")
                    st.write(notification["message"])
                    
                    # Additional data if available
                    if notification["data"]:
                        with st.expander("Additional Details"):
                            st.json(notification["data"])
                
                with col2:
                    st.write(f"**Created:** {notification['created_at'][:16]}")
                    if notification["read_at"]:
                        st.write(f"**Read:** {notification['read_at'][:16]}")
                    
                    if not notification["is_read"]:
                        if st.button("Mark as Read", key=f"mark_read_{notification['id']}"):
                            notif_manager.mark_notification_read(notification["id"], user["id"])
                            st.rerun()
    else:
        if show_unread_only:
            st.success("🎉 No unread notifications!")
        else:
            st.info("No notifications to display.")

def render_notification_preferences(notif_manager: NotificationManager, user: Dict[str, Any]):
    """Render notification preferences"""
    st.subheader("Notification Preferences")
    
    # Get current preferences
    preferences = notif_manager.get_user_preferences(user["id"])
    
    # Notification types configuration
    st.write("### Configure Notification Types")
    
    notification_types = [
        (NotificationType.TEST_COMPLETED, "Test Completed", "When your tests finish running"),
        (NotificationType.MODEL_ADDED, "New Models", "When new models are added to the platform"),
        (NotificationType.SHARE_VIEWED, "Share Views", "When someone views your shared content"),
        (NotificationType.COMMENT_ADDED, "New Comments", "When someone comments on your content"),
        (NotificationType.WORKSPACE_INVITE, "Workspace Invites", "When you're invited to join a workspace"),
        (NotificationType.SYSTEM_ALERT, "System Alerts", "Important system notifications"),
        (NotificationType.LEADERBOARD_UPDATE, "Leaderboard Updates", "When rankings are updated")
    ]
    
    with st.form("notification_preferences"):
        for notif_type, display_name, description in notification_types:
            st.write(f"**{display_name}**")
            st.write(f"*{description}*")
            
            current_prefs = preferences.get(notif_type.value, {"email_enabled": True, "push_enabled": True})
            
            col1, col2 = st.columns(2)
            with col1:
                email_enabled = st.checkbox(
                    "Email notifications", 
                    value=current_prefs["email_enabled"],
                    key=f"email_{notif_type.value}"
                )
            
            with col2:
                push_enabled = st.checkbox(
                    "In-app notifications",
                    value=current_prefs["push_enabled"], 
                    key=f"push_{notif_type.value}"
                )
            
            st.divider()
        
        if st.form_submit_button("Save Preferences"):
            # Update preferences for each notification type
            for notif_type, _, _ in notification_types:
                email_enabled = st.session_state[f"email_{notif_type.value}"]
                push_enabled = st.session_state[f"push_{notif_type.value}"]
                
                notif_manager.update_notification_preferences(
                    user["id"], notif_type, email_enabled, push_enabled
                )
            
            st.success("Preferences updated successfully!")
            st.rerun()

def render_notification_statistics(notif_manager: NotificationManager, user: Dict[str, Any]):
    """Render notification statistics"""
    st.subheader("Notification Statistics")
    
    # Get all notifications for statistics
    all_notifications = notif_manager.get_user_notifications(user["id"], limit=1000)
    
    if not all_notifications:
        st.info("No notification data available.")
        return
    
    # Statistics overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_count = len(all_notifications)
        st.metric("Total Notifications", total_count)
    
    with col2:
        unread_count = sum(1 for n in all_notifications if not n["is_read"])
        st.metric("Unread", unread_count)
    
    with col3:
        high_priority_count = sum(1 for n in all_notifications if n["priority"] in ["high", "urgent"])
        st.metric("High Priority", high_priority_count)
    
    with col4:
        # Calculate response rate (read within 24 hours)
        quick_responses = sum(1 for n in all_notifications 
                            if n["is_read"] and n["read_at"] and 
                            (datetime.fromisoformat(n["read_at"]) - datetime.fromisoformat(n["created_at"])).days < 1)
        response_rate = (quick_responses / total_count * 100) if total_count > 0 else 0
        st.metric("24h Response Rate", f"{response_rate:.1f}%")
    
    # Notification types distribution
    st.write("### Notifications by Type")
    type_counts = {}
    for notification in all_notifications:
        notif_type = notification["notification_type"]
        type_counts[notif_type] = type_counts.get(notif_type, 0) + 1
    
    if type_counts:
        import pandas as pd
        df = pd.DataFrame(list(type_counts.items()), columns=["Type", "Count"])
        st.bar_chart(df.set_index("Type"))
    
    # Priority distribution
    st.write("### Notifications by Priority")
    priority_counts = {}
    for notification in all_notifications:
        priority = notification["priority"]
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    if priority_counts:
        df_priority = pd.DataFrame(list(priority_counts.items()), columns=["Priority", "Count"])
        st.bar_chart(df_priority.set_index("Priority"))