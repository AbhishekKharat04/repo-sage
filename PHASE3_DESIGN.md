# Phase 3: Real-Time Collaboration Features - Design Document

## Overview
Phase 3 adds real-time collaboration capabilities to ShipSage, enabling teams to work together on DevOps analysis and configuration generation.

## Architecture Design

### 1. WebSocket Infrastructure

#### Technology Stack
- **FastAPI WebSocket** - Built-in WebSocket support
- **Redis** - Message broker and session storage
- **SQLite/PostgreSQL** - Persistent storage for sessions and comments

#### WebSocket Manager
```python
class ConnectionManager:
    - active_connections: Dict[str, List[WebSocket]]
    - connect(session_id: str, websocket: WebSocket)
    - disconnect(session_id: str, websocket: WebSocket)
    - broadcast(session_id: str, message: dict)
    - send_personal(websocket: WebSocket, message: dict)
```

#### Message Types
```json
{
  "type": "user_joined|user_left|cursor_move|comment_added|analysis_updated",
  "session_id": "uuid",
  "user_id": "uuid",
  "data": {}
}
```

---

### 2. Session Management

#### Session Model
```python
class Session:
    id: str (UUID)
    repo_url: str
    created_at: datetime
    expires_at: datetime
    owner_id: str
    analysis_data: dict
    configs: dict
    share_token: str (for public links)
    is_public: bool
```

#### Session Storage
- **Redis**: Active sessions (TTL: 24 hours)
- **Database**: Persistent sessions (optional long-term storage)

#### Session Operations
- Create session on analysis completion
- Generate shareable link
- Join existing session
- Update session data in real-time
- Auto-cleanup expired sessions

---

### 3. Comment System

#### Comment Model
```python
class Comment:
    id: str (UUID)
    session_id: str
    user_id: str
    username: str
    target_type: str (file|section|line)
    target_id: str
    content: str
    created_at: datetime
    resolved: bool
```

#### Comment Features
- Add comments to specific files/sections
- Reply to comments (threaded)
- Resolve/unresolve comments
- Real-time comment notifications
- Comment persistence

---

### 4. User Presence

#### User Model
```python
class User:
    id: str (UUID)
    username: str
    color: str (for cursor/avatar)
    last_seen: datetime
    cursor_position: dict
```

#### Presence Features
- Show active users in session
- Display user cursors/selections
- User join/leave notifications
- Idle timeout (5 minutes)

---

### 5. Shareable Links

#### Link Generation
```
https://shipsage.com/session/{session_id}?token={share_token}
```

#### Link Types
- **Private**: Requires authentication
- **Public**: Anyone with link can view
- **Expiring**: Auto-expire after N hours

#### Link Features
- Copy to clipboard
- QR code generation
- Access control (view-only vs edit)
- Link analytics (views, users)

---

## Database Schema

### Sessions Table
```sql
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY,
    repo_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    owner_id VARCHAR(36),
    analysis_data JSON,
    configs JSON,
    share_token VARCHAR(64) UNIQUE,
    is_public BOOLEAN DEFAULT FALSE
);
```

### Comments Table
```sql
CREATE TABLE comments (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) REFERENCES sessions(id),
    user_id VARCHAR(36),
    username VARCHAR(100),
    target_type VARCHAR(20),
    target_id VARCHAR(100),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE
);
```

### Users Table
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Endpoints

### Session Management
```
POST   /api/sessions              # Create new session
GET    /api/sessions/{id}         # Get session details
PUT    /api/sessions/{id}         # Update session
DELETE /api/sessions/{id}         # Delete session
GET    /api/sessions/{id}/share   # Get shareable link
```

### WebSocket
```
WS     /ws/{session_id}           # WebSocket connection
```

### Comments
```
POST   /api/sessions/{id}/comments        # Add comment
GET    /api/sessions/{id}/comments        # List comments
PUT    /api/comments/{id}                 # Update comment
DELETE /api/comments/{id}                 # Delete comment
POST   /api/comments/{id}/resolve         # Resolve comment
```

### Users
```
POST   /api/users/register        # Register user
POST   /api/users/login           # Login user
GET    /api/users/me              # Get current user
```

---

## Frontend Components

### 1. Session View
- Active users list
- User avatars with colors
- Join/leave notifications
- Session info panel

### 2. Comment Panel
- Comment list (filterable)
- Add comment button
- Comment threads
- Resolve/unresolve actions
- Real-time updates

### 3. Collaboration Toolbar
- Share button
- Copy link button
- User presence indicators
- Session settings

### 4. Real-time Indicators
- Typing indicators
- Cursor positions
- Selection highlights
- Activity feed

---

## WebSocket Message Flow

### User Joins Session
```
Client -> Server: connect(session_id, user_info)
Server -> All:    broadcast({type: "user_joined", user: {...}})
Server -> Client: send_personal({type: "session_state", data: {...}})
```

### Comment Added
```
Client -> Server: send({type: "comment_added", comment: {...}})
Server -> DB:     save_comment(comment)
Server -> All:    broadcast({type: "comment_added", comment: {...}})
```

### Analysis Updated
```
Client -> Server: send({type: "analysis_updated", data: {...}})
Server -> Redis:  update_session(data)
Server -> All:    broadcast({type: "analysis_updated", data: {...}})
```

---

## Security Considerations

### Authentication
- JWT tokens for API authentication
- WebSocket token validation
- Session ownership verification

### Authorization
- Owner can edit/delete
- Viewers can only comment
- Public links are read-only by default

### Rate Limiting
- WebSocket message rate limits
- API endpoint rate limits
- Comment spam prevention

### Data Privacy
- Encrypt sensitive session data
- Auto-expire sessions
- GDPR compliance (data deletion)

---

## Performance Optimization

### Redis Caching
- Cache active sessions
- Cache user presence
- Cache recent comments

### WebSocket Optimization
- Message batching
- Compression for large payloads
- Connection pooling

### Database Optimization
- Index on session_id, user_id
- Pagination for comments
- Cleanup old sessions (cron job)

---

## Implementation Priority

### Phase 3.1: Core Infrastructure (Week 1)
1. WebSocket manager
2. Session storage (Redis)
3. Basic session CRUD
4. Database schema

### Phase 3.2: Collaboration Features (Week 2)
1. User presence
2. Comment system
3. Real-time updates
4. Frontend integration

### Phase 3.3: Sharing & Polish (Week 3)
1. Shareable links
2. Access control
3. UI polish
4. Testing & documentation

---

## Dependencies

### New Python Packages
```txt
redis>=5.0.0              # Redis client
python-jose>=3.3.0        # JWT tokens
passlib>=1.7.4            # Password hashing
python-multipart>=0.0.6   # Form data
websockets>=12.0          # WebSocket support
aioredis>=2.0.1           # Async Redis
sqlalchemy>=2.0.0         # ORM (optional)
```

### Infrastructure
- Redis server (local or cloud)
- PostgreSQL (optional, can use SQLite)

---

## Testing Strategy

### Unit Tests
- Session CRUD operations
- Comment CRUD operations
- WebSocket message handling
- Authentication/authorization

### Integration Tests
- Multi-user scenarios
- Real-time message delivery
- Session expiration
- Link sharing

### Load Tests
- 100+ concurrent WebSocket connections
- Message broadcast performance
- Redis performance under load

---

## Monitoring & Logging

### Metrics
- Active WebSocket connections
- Messages per second
- Session creation rate
- Comment activity

### Logging
- User join/leave events
- Comment creation/deletion
- Session lifecycle events
- Error tracking

---

## Future Enhancements

### Phase 4 (Future)
- Video/audio chat integration
- Screen sharing
- Collaborative editing (CRDT)
- AI-powered suggestions in comments
- Integration with Slack/Teams
- Mobile app support

---

## Success Metrics

### Technical
- WebSocket latency < 100ms
- Support 1000+ concurrent users
- 99.9% uptime
- Message delivery rate > 99.9%

### User Experience
- Session creation < 2 seconds
- Real-time updates < 500ms
- Comment load time < 1 second
- Share link generation instant

---

## Risk Mitigation

### Scalability
- Horizontal scaling with Redis Cluster
- Load balancer for WebSocket connections
- Database read replicas

### Reliability
- WebSocket reconnection logic
- Message queue for failed deliveries
- Session backup/restore

### Security
- Regular security audits
- Penetration testing
- Dependency updates

---

## Conclusion

Phase 3 transforms ShipSage from a single-user tool into a collaborative platform, enabling teams to work together on DevOps analysis and configuration generation in real-time.

**Estimated Implementation Time**: 3-4 weeks
**Complexity**: High
**Impact**: Very High - Enables team collaboration