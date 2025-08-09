"""
Collaboration Features - Sharing and teamwork capabilities
"""
import json
import sqlite3
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import uuid
from enum import Enum

class ShareType(Enum):
    MODEL_EVALUATION = "model_evaluation"
    TEST_RESULT = "test_result"
    CUSTOM_TEST = "custom_test"
    ANALYTICS_REPORT = "analytics_report"

class PermissionLevel(Enum):
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"
    ADMIN = "admin"

@dataclass
class ShareLink:
    """Shared content link"""
    id: str
    content_type: ShareType
    content_id: int
    owner_id: int
    title: str
    description: str
    permission_level: PermissionLevel
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    view_count: int = 0

class CollaborationManager:
    """Manages sharing and collaboration features"""
    
    def __init__(self, db_path: str = "collaboration.db"):
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize collaboration database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Shared content links
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_links (
                id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                content_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                permission_level TEXT NOT NULL,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                view_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Collaboration comments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collaboration_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                share_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                comment_text TEXT NOT NULL,
                parent_comment_id INTEGER,
                is_resolved BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (share_id) REFERENCES shared_links (id),
                FOREIGN KEY (parent_comment_id) REFERENCES collaboration_comments (id)
            )
        """)
        
        # Team workspaces
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER NOT NULL,
                is_public BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Workspace members
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspace_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workspace_id) REFERENCES workspaces (id),
                UNIQUE(workspace_id, user_id)
            )
        """)
        
        # Shared evaluations/experiments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                configuration TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
            )
        """)
        
        # Activity feed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_feed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_share_link(self, content_type: ShareType, content_id: int, 
                         owner_id: int, title: str, description: str = "",
                         permission_level: PermissionLevel = PermissionLevel.VIEW,
                         expires_in_days: Optional[int] = None) -> str:
        """Create a shareable link for content"""
        share_id = str(uuid.uuid4())
        expires_at = None
        
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO shared_links 
            (id, content_type, content_id, owner_id, title, description, 
             permission_level, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (share_id, content_type.value, content_id, owner_id, title, 
              description, permission_level.value, expires_at, True))
        
        conn.commit()
        conn.close()
        
        return share_id
    
    def get_share_link(self, share_id: str) -> Optional[ShareLink]:
        """Get shared content by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, content_type, content_id, owner_id, title, description,
                   permission_level, expires_at, is_active, created_at, view_count
            FROM shared_links
            WHERE id = ? AND is_active = 1
        """, (share_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Check if expired
        if row[7] and datetime.fromisoformat(row[7]) < datetime.utcnow():
            return None
        
        return ShareLink(
            id=row[0],
            content_type=ShareType(row[1]),
            content_id=row[2],
            owner_id=row[3],
            title=row[4],
            description=row[5],
            permission_level=PermissionLevel(row[6]),
            expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
            is_active=bool(row[8]),
            created_at=datetime.fromisoformat(row[9]),
            view_count=row[10]
        )
    
    def increment_view_count(self, share_id: str):
        """Increment view count for shared content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE shared_links 
            SET view_count = view_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (share_id,))
        
        conn.commit()
        conn.close()
    
    def get_user_shares(self, user_id: int) -> List[ShareLink]:
        """Get all shares created by a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, content_type, content_id, owner_id, title, description,
                   permission_level, expires_at, is_active, created_at, view_count
            FROM shared_links
            WHERE owner_id = ? AND is_active = 1
            ORDER BY created_at DESC
        """, (user_id,))
        
        shares = []
        for row in cursor.fetchall():
            shares.append(ShareLink(
                id=row[0],
                content_type=ShareType(row[1]),
                content_id=row[2],
                owner_id=row[3],
                title=row[4],
                description=row[5],
                permission_level=PermissionLevel(row[6]),
                expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
                is_active=bool(row[8]),
                created_at=datetime.fromisoformat(row[9]),
                view_count=row[10]
            ))
        
        conn.close()
        return shares
    
    def add_comment(self, share_id: str, user_id: int, comment_text: str,
                   parent_comment_id: Optional[int] = None) -> int:
        """Add a comment to shared content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO collaboration_comments 
            (share_id, user_id, comment_text, parent_comment_id)
            VALUES (?, ?, ?, ?)
        """, (share_id, user_id, comment_text, parent_comment_id))
        
        comment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return comment_id
    
    def get_comments(self, share_id: str) -> List[Dict[str, Any]]:
        """Get comments for shared content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cc.id, cc.user_id, cc.comment_text, cc.parent_comment_id,
                   cc.is_resolved, cc.created_at
            FROM collaboration_comments cc
            WHERE cc.share_id = ?
            ORDER BY cc.created_at ASC
        """, (share_id,))
        
        comments = []
        for row in cursor.fetchall():
            comments.append({
                "id": row[0],
                "user_id": row[1],
                "comment_text": row[2],
                "parent_comment_id": row[3],
                "is_resolved": bool(row[4]),
                "created_at": row[5]
            })
        
        conn.close()
        return comments
    
    def create_workspace(self, name: str, description: str, owner_id: int,
                        is_public: bool = False) -> int:
        """Create a team workspace"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO workspaces (name, description, owner_id, is_public)
            VALUES (?, ?, ?, ?)
        """, (name, description, owner_id, is_public))
        
        workspace_id = cursor.lastrowid
        
        # Add owner as admin member
        cursor.execute("""
            INSERT INTO workspace_members (workspace_id, user_id, role)
            VALUES (?, ?, 'admin')
        """, (workspace_id, owner_id))
        
        conn.commit()
        conn.close()
        
        return workspace_id
    
    def add_workspace_member(self, workspace_id: int, user_id: int, 
                           role: str = "member") -> bool:
        """Add member to workspace"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO workspace_members (workspace_id, user_id, role)
                VALUES (?, ?, ?)
            """, (workspace_id, user_id, role))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # User already in workspace
        finally:
            conn.close()
    
    def get_user_workspaces(self, user_id: int) -> List[Dict[str, Any]]:
        """Get workspaces user is a member of"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT w.id, w.name, w.description, w.owner_id, w.is_public,
                   w.created_at, wm.role
            FROM workspaces w
            JOIN workspace_members wm ON w.id = wm.workspace_id
            WHERE wm.user_id = ?
            ORDER BY w.created_at DESC
        """, (user_id,))
        
        workspaces = []
        for row in cursor.fetchall():
            workspaces.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "owner_id": row[3],
                "is_public": bool(row[4]),
                "created_at": row[5],
                "user_role": row[6]
            })
        
        conn.close()
        return workspaces
    
    def log_activity(self, workspace_id: Optional[int], user_id: int,
                    activity_type: str, title: str, description: str = "",
                    metadata: Dict = None):
        """Log activity to feed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO activity_feed 
            (workspace_id, user_id, activity_type, title, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (workspace_id, user_id, activity_type, title, description, 
              json.dumps(metadata or {})))
        
        conn.commit()
        conn.close()
    
    def get_activity_feed(self, workspace_id: Optional[int] = None,
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Get activity feed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if workspace_id:
            cursor.execute("""
                SELECT af.id, af.user_id, af.activity_type, af.title,
                       af.description, af.metadata, af.created_at
                FROM activity_feed af
                WHERE af.workspace_id = ?
                ORDER BY af.created_at DESC
                LIMIT ?
            """, (workspace_id, limit))
        else:
            cursor.execute("""
                SELECT af.id, af.user_id, af.activity_type, af.title,
                       af.description, af.metadata, af.created_at
                FROM activity_feed af
                WHERE af.workspace_id IS NULL
                ORDER BY af.created_at DESC
                LIMIT ?
            """, (limit,))
        
        activities = []
        for row in cursor.fetchall():
            activities.append({
                "id": row[0],
                "user_id": row[1],
                "activity_type": row[2],
                "title": row[3],
                "description": row[4],
                "metadata": json.loads(row[5]),
                "created_at": row[6]
            })
        
        conn.close()
        return activities

def render_collaboration_page():
    """Render collaboration features page"""
    st.title("🤝 Collaboration Hub")
    
    # Initialize collaboration manager
    if 'collab_manager' not in st.session_state:
        st.session_state.collab_manager = CollaborationManager()
    
    collab = st.session_state.collab_manager
    
    # Check if user is logged in
    if 'user' not in st.session_state:
        st.warning("Please log in to access collaboration features.")
        return
    
    user = st.session_state.user
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔗 My Shares",
        "👥 Workspaces", 
        "📊 Shared Content",
        "💬 Comments",
        "📈 Activity Feed"
    ])
    
    with tab1:
        render_shares_management(collab, user)
    
    with tab2:
        render_workspaces(collab, user)
    
    with tab3:
        render_shared_content_viewer(collab, user)
    
    with tab4:
        render_comments_section(collab, user)
    
    with tab5:
        render_activity_feed(collab, user)

def render_shares_management(collab: CollaborationManager, user: Dict[str, Any]):
    """Render shares management interface"""
    st.subheader("My Shared Content")
    
    # Create new share
    with st.expander("➕ Create New Share"):
        with st.form("create_share"):
            col1, col2 = st.columns(2)
            
            with col1:
                content_type = st.selectbox("Content Type", [
                    "Model Evaluation",
                    "Test Result",
                    "Custom Test",
                    "Analytics Report"
                ])
                
                # Map display names to enum values
                content_type_map = {
                    "Model Evaluation": ShareType.MODEL_EVALUATION,
                    "Test Result": ShareType.TEST_RESULT,
                    "Custom Test": ShareType.CUSTOM_TEST,
                    "Analytics Report": ShareType.ANALYTICS_REPORT
                }
                
                content_id = st.number_input("Content ID", min_value=1, step=1)
            
            with col2:
                title = st.text_input("Share Title")
                permission = st.selectbox("Permission Level", [
                    "View Only",
                    "View + Comment",
                    "Edit"
                ])
                
                permission_map = {
                    "View Only": PermissionLevel.VIEW,
                    "View + Comment": PermissionLevel.COMMENT,
                    "Edit": PermissionLevel.EDIT
                }
            
            description = st.text_area("Description", max_chars=500)
            expires_in = st.selectbox("Expires in", [
                "Never", "1 day", "1 week", "1 month", "3 months"
            ])
            
            expire_days_map = {
                "Never": None,
                "1 day": 1,
                "1 week": 7,
                "1 month": 30,
                "3 months": 90
            }
            
            submitted = st.form_submit_button("Create Share Link")
            
            if submitted and title and content_id:
                try:
                    share_id = collab.create_share_link(
                        content_type=content_type_map[content_type],
                        content_id=content_id,
                        owner_id=user["id"],
                        title=title,
                        description=description,
                        permission_level=permission_map[permission],
                        expires_in_days=expire_days_map[expires_in]
                    )
                    
                    # Create shareable URL (in production, would be full domain)
                    share_url = f"https://yourapp.replit.app/shared/{share_id}"
                    
                    st.success("Share link created successfully!")
                    st.code(share_url, language="text")
                    
                    # Log activity
                    collab.log_activity(
                        None, user["id"], "share_created", 
                        f"Created share: {title}",
                        f"Shared {content_type} with {permission} permissions"
                    )
                    
                except Exception as e:
                    st.error(f"Error creating share: {str(e)}")
    
    # Existing shares
    user_shares = collab.get_user_shares(user["id"])
    
    if user_shares:
        st.write("### Your Shared Content")
        
        for share in user_shares:
            with st.expander(f"🔗 {share.title} ({share.content_type.value})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Views:** {share.view_count}")
                    st.write(f"**Created:** {share.created_at.strftime('%Y-%m-%d')}")
                
                with col2:
                    st.write(f"**Permission:** {share.permission_level.value}")
                    if share.expires_at:
                        st.write(f"**Expires:** {share.expires_at.strftime('%Y-%m-%d')}")
                    else:
                        st.write("**Expires:** Never")
                
                with col3:
                    share_url = f"https://yourapp.replit.app/shared/{share.id}"
                    st.code(share_url, language="text")
                    
                    if st.button(f"Copy Link", key=f"copy_{share.id}"):
                        st.info("Link copied to clipboard!")
                
                if share.description:
                    st.write(f"**Description:** {share.description}")
    else:
        st.info("You haven't shared any content yet.")

def render_workspaces(collab: CollaborationManager, user: Dict[str, Any]):
    """Render workspaces management"""
    st.subheader("Team Workspaces")
    
    # Create new workspace
    with st.expander("➕ Create New Workspace"):
        with st.form("create_workspace"):
            workspace_name = st.text_input("Workspace Name")
            workspace_desc = st.text_area("Description")
            is_public = st.checkbox("Public Workspace")
            
            if st.form_submit_button("Create Workspace"):
                if workspace_name:
                    try:
                        workspace_id = collab.create_workspace(
                            name=workspace_name,
                            description=workspace_desc,
                            owner_id=user["id"],
                            is_public=is_public
                        )
                        
                        st.success(f"Workspace '{workspace_name}' created! (ID: {workspace_id})")
                        
                        collab.log_activity(
                            workspace_id, user["id"], "workspace_created",
                            f"Created workspace: {workspace_name}"
                        )
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating workspace: {str(e)}")
    
    # User's workspaces
    workspaces = collab.get_user_workspaces(user["id"])
    
    if workspaces:
        st.write("### Your Workspaces")
        
        for workspace in workspaces:
            with st.expander(f"👥 {workspace['name']} ({workspace['user_role']})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Role:** {workspace['user_role']}")
                    st.write(f"**Public:** {'Yes' if workspace['is_public'] else 'No'}")
                
                with col2:
                    st.write(f"**Created:** {workspace['created_at']}")
                    st.write(f"**Owner ID:** {workspace['owner_id']}")
                
                if workspace['description']:
                    st.write(f"**Description:** {workspace['description']}")
                
                # Workspace actions for admins
                if workspace['user_role'] in ['admin', 'owner']:
                    st.write("**Admin Actions:**")
                    
                    with st.form(f"add_member_{workspace['id']}"):
                        new_member_id = st.number_input(
                            "Add Member (User ID)", 
                            min_value=1, 
                            step=1,
                            key=f"member_{workspace['id']}"
                        )
                        member_role = st.selectbox(
                            "Role", 
                            ["member", "admin"],
                            key=f"role_{workspace['id']}"
                        )
                        
                        if st.form_submit_button("Add Member"):
                            if collab.add_workspace_member(workspace['id'], new_member_id, member_role):
                                st.success("Member added successfully!")
                                
                                collab.log_activity(
                                    workspace['id'], user["id"], "member_added",
                                    f"Added user {new_member_id} as {member_role}"
                                )
                                st.rerun()
                            else:
                                st.error("Failed to add member (may already exist)")
    else:
        st.info("You're not a member of any workspaces yet.")

def render_shared_content_viewer(collab: CollaborationManager, user: Dict[str, Any]):
    """Render shared content viewer"""
    st.subheader("View Shared Content")
    
    # Enter share ID to view
    share_id_input = st.text_input(
        "Enter Share ID or paste share URL",
        help="Enter the share ID or full share URL"
    )
    
    if share_id_input:
        # Extract share ID from URL if full URL provided
        if "shared/" in share_id_input:
            share_id = share_id_input.split("shared/")[-1]
        else:
            share_id = share_id_input
        
        share_link = collab.get_share_link(share_id)
        
        if share_link:
            # Increment view count
            collab.increment_view_count(share_id)
            
            st.success("✅ Shared content found!")
            
            # Content header
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Title:** {share_link.title}")
                st.write(f"**Type:** {share_link.content_type.value}")
            
            with col2:
                st.write(f"**Shared by:** User {share_link.owner_id}")
                st.write(f"**Views:** {share_link.view_count + 1}")
            
            if share_link.description:
                st.write(f"**Description:** {share_link.description}")
            
            st.divider()
            
            # Content display (placeholder - would load actual content)
            st.write("### Shared Content")
            
            if share_link.content_type == ShareType.MODEL_EVALUATION:
                st.info(f"Model Evaluation Results (ID: {share_link.content_id})")
                st.write("This would show the actual model evaluation results...")
                
            elif share_link.content_type == ShareType.TEST_RESULT:
                st.info(f"Test Results (ID: {share_link.content_id})")
                st.write("This would show the detailed test results...")
                
            elif share_link.content_type == ShareType.CUSTOM_TEST:
                st.info(f"Custom Test Definition (ID: {share_link.content_id})")
                st.write("This would show the custom test configuration...")
                
            elif share_link.content_type == ShareType.ANALYTICS_REPORT:
                st.info(f"Analytics Report (ID: {share_link.content_id})")
                st.write("This would show the analytics dashboard...")
            
            # Comments section (if permission allows)
            if share_link.permission_level in [PermissionLevel.COMMENT, PermissionLevel.EDIT]:
                st.divider()
                render_comments_for_share(collab, share_id, user)
            
        else:
            st.error("❌ Share not found, expired, or inactive.")

def render_comments_for_share(collab: CollaborationManager, share_id: str, user: Dict[str, Any]):
    """Render comments section for shared content"""
    st.write("### Comments & Discussion")
    
    # Add new comment
    with st.form(f"add_comment_{share_id}"):
        comment_text = st.text_area("Add a comment", max_chars=1000)
        
        if st.form_submit_button("Post Comment"):
            if comment_text.strip():
                try:
                    comment_id = collab.add_comment(share_id, user["id"], comment_text)
                    st.success("Comment added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding comment: {str(e)}")
    
    # Display existing comments
    comments = collab.get_comments(share_id)
    
    if comments:
        st.write(f"**{len(comments)} Comments:**")
        
        for comment in comments:
            with st.container():
                st.write(f"**User {comment['user_id']}** - {comment['created_at']}")
                st.write(comment['comment_text'])
                
                if comment['is_resolved']:
                    st.success("✅ Resolved")
                
                st.divider()
    else:
        st.info("No comments yet. Be the first to comment!")

def render_comments_section(collab: CollaborationManager, user: Dict[str, Any]):
    """Render general comments management"""
    st.subheader("Comments & Discussions")
    st.info("This section would show all comments across your shared content and workspaces.")
    
    # Would implement comprehensive comments view here
    st.write("**Recent Comments:**")
    st.info("Implementation would show recent comments from all your shared content")

def render_activity_feed(collab: CollaborationManager, user: Dict[str, Any]):
    """Render activity feed"""
    st.subheader("Activity Feed")
    
    # Get activity feed
    activities = collab.get_activity_feed(limit=50)
    
    if activities:
        for activity in activities:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Activity icon based on type
                    icon_map = {
                        "share_created": "🔗",
                        "workspace_created": "👥",
                        "member_added": "➕",
                        "test_executed": "🧪",
                        "model_submitted": "🤖",
                        "comment_added": "💬"
                    }
                    icon = icon_map.get(activity['activity_type'], "📝")
                    
                    st.write(f"{icon} **{activity['title']}**")
                    if activity['description']:
                        st.write(f"*{activity['description']}*")
                
                with col2:
                    st.write(f"User {activity['user_id']}")
                    st.write(activity['created_at'][:10])  # Show date only
                
                st.divider()
    else:
        st.info("No recent activity.")