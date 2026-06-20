import React, { useState, useEffect, useRef } from 'react';
import { Bell, Heart, MessageCircle, Reply, Trash2, Clock, ArrowRight, Share2, Send, MessageSquare, User, CheckSquare, Square } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { notificationApi, chatApi } from '../services/api';
import type { Notification, ChatConversation, ChatMessage } from '../types';

type Tab = 'notifications' | 'chat';

const Notifications: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<ChatConversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageInput, setMessageInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [selectedNotificationIds, setSelectedNotificationIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tabParam = params.get('tab');
    if (tabParam === 'chat' || tabParam === 'notifications') {
      setActiveTab(tabParam);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'notifications') {
      fetchNotifications();
    } else {
      fetchConversations();
    }
  }, [activeTab]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchNotifications = async () => {
    try {
      const data = await notificationApi.getNotifications(1, 50);
      setNotifications(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchConversations = async () => {
    try {
      const data = await chatApi.getConversations();
      setConversations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (conversation: ChatConversation) => {
    try {
      setChatLoading(true);
      const data = await chatApi.getMessages(conversation.id);
      setMessages(Array.isArray(data) ? data : []);
      setSelectedConversation(conversation);
    } catch (err) {
      console.error('Failed to fetch messages:', err);
      setMessages([]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!messageInput.trim() || !selectedConversation) return;

    try {
      await chatApi.sendMessage(selectedConversation.otherUserId, messageInput.trim());
      setMessageInput('');
      fetchMessages(selectedConversation);
      fetchConversations();
    } catch (err) {
      console.error('Failed to send message:', err);
      alert('发送失败: ' + (err as any).response?.data?.message || '请等待对方回复或互相关注后继续');
    }
  };

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.isRead) {
      await notificationApi.markAsRead(notification.id);
      setNotifications(prev => prev.map(n =>
        n.id === notification.id ? { ...n, isRead: true } : n
      ));
    }

    if (notification.postId) {
      navigate(`/post/${notification.postId}`);
    }
  };

  const handleDeleteNotification = async (e: React.MouseEvent, notificationId: number) => {
    e.stopPropagation();
    if (window.confirm('确定要删除这条通知吗？')) {
      try {
        await notificationApi.deleteNotification(notificationId);
        setNotifications(prev => prev.filter(n => n.id !== notificationId));
      } catch (err) {
        console.error('Failed to delete notification:', err);
      }
    }
  };

  const toggleNotificationSelection = (notificationId: number) => {
    const newSelected = new Set(selectedNotificationIds);
    if (newSelected.has(notificationId)) {
      newSelected.delete(notificationId);
    } else {
      newSelected.add(notificationId);
    }
    setSelectedNotificationIds(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedNotificationIds.size === notifications.length) {
      setSelectedNotificationIds(new Set());
    } else {
      setSelectedNotificationIds(new Set(notifications.map(n => n.id)));
    }
  };

  const handleMarkMultipleAsRead = async () => {
    if (selectedNotificationIds.size === 0) {
      alert('请先选择要标记为已读的通知');
      return;
    }
    try {
      await notificationApi.markMultipleAsRead([...selectedNotificationIds]);
      setNotifications(prev => prev.map(n => 
        selectedNotificationIds.has(n.id) ? { ...n, isRead: true } : n
      ));
      setSelectedNotificationIds(new Set());
    } catch (err) {
      console.error('Failed to mark as read:', err);
      alert('标记失败');
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, isRead: true })));
      setSelectedNotificationIds(new Set());
    } catch (err) {
      console.error('Failed to mark all as read:', err);
      alert('标记失败');
    }
  };

  const handleDeleteMultipleNotifications = async () => {
    if (selectedNotificationIds.size === 0) {
      alert('请先选择要删除的通知');
      return;
    }
    if (window.confirm(`确定要删除选中的 ${selectedNotificationIds.size} 条通知吗？`)) {
      try {
        await notificationApi.deleteMultipleNotifications([...selectedNotificationIds]);
        setNotifications(prev => prev.filter(n => !selectedNotificationIds.has(n.id)));
        setSelectedNotificationIds(new Set());
      } catch (err) {
        console.error('Failed to delete notifications:', err);
        alert('删除失败');
      }
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;

    return date.toLocaleDateString('zh-CN');
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'POST_LIKE':
      case 'COMMENT_LIKE':
        return <Heart size={18} fill="#ef4444" color="#ef4444" />;
      case 'POST_COMMENT':
        return <MessageCircle size={18} color="#333333" />;
      case 'COMMENT_REPLY':
        return <Reply size={18} color="#10b981" />;
      case 'POST_SHARE':
        return <Share2 size={18} color="#64748b" />;
      default:
        return <Bell size={18} color="#64748b" />;
    }
  };

  const getIconBgColor = (type: string) => {
    switch (type) {
      case 'POST_LIKE':
      case 'COMMENT_LIKE':
        return '#fef2f2';
      case 'POST_COMMENT':
        return '#e2e8f0';
      case 'COMMENT_REPLY':
        return '#f0fdf4';
      case 'POST_SHARE':
        return '#faf5ff';
      default:
        return '#f1f5f9';
    }
  };

  const getAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return avatarUrl;
  };

  const totalUnreadCount = conversations.reduce((sum, conv) => sum + (conv.unreadCount || 0), 0);
  const unreadNotificationCount = notifications.filter(n => !n.isRead).length;
  const combinedUnreadCount = totalUnreadCount + unreadNotificationCount;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>
          <MessageSquare size={24} />
          <span>消息与通知</span>
        </h1>
      </div>

      <div style={styles.tabContainer}>
        <button
          style={{ ...styles.tab, ...(activeTab === 'chat' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('chat')}
        >
          <div style={styles.tabContent}>
            <MessageSquare size={18} />
            <span>消息</span>
            {totalUnreadCount > 0 && (
              <span style={styles.tabBadge}>{totalUnreadCount > 99 ? '99+' : totalUnreadCount}</span>
            )}
          </div>
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'notifications' ? styles.tabActive : {}) }}
          onClick={() => setActiveTab('notifications')}
        >
          <div style={styles.tabContent}>
            <Bell size={18} />
            <span>通知</span>
            {unreadNotificationCount > 0 && (
              <span style={styles.tabBadge}>{unreadNotificationCount > 99 ? '99+' : unreadNotificationCount}</span>
            )}
          </div>
        </button>
      </div>

      {activeTab === 'notifications' ? (
        <div style={styles.contentArea}>
          {loading ? (
            <div style={styles.loading}>
              <div style={styles.spinner}></div>
              <span>加载中...</span>
            </div>
          ) : notifications.length === 0 ? (
            <div style={styles.emptyState}>
              <Bell size={48} color="#94a3b8" />
              <p>暂无通知</p>
              <p style={styles.emptyDesc}>当有人点赞或评论你的帖子时，你会在这里收到通知</p>
            </div>
          ) : (
            <>
              <div style={styles.batchActions}>
                <button
                  style={styles.selectAllButton}
                  onClick={toggleSelectAll}
                >
                  {selectedNotificationIds.size === notifications.length ? (
                    <CheckSquare size={16} />
                  ) : (
                    <Square size={16} />
                  )}
                  <span>
                    {selectedNotificationIds.size === notifications.length 
                      ? '取消全选' 
                      : selectedNotificationIds.size > 0 
                        ? `已选 ${selectedNotificationIds.size} 项` 
                        : '全选'}
                  </span>
                </button>
                
                {selectedNotificationIds.size > 0 && (
                  <div style={styles.actionButtons}>
                    <button
                      style={styles.actionButton}
                      onClick={handleMarkMultipleAsRead}
                    >
                      标记已读
                    </button>
                    <button
                      style={{ ...styles.actionButton, ...styles.deleteActionButton }}
                      onClick={handleDeleteMultipleNotifications}
                    >
                      删除选中
                    </button>
                  </div>
                )}
                
                {selectedNotificationIds.size === 0 && unreadNotificationCount > 0 && (
                  <button
                    style={styles.actionButton}
                    onClick={handleMarkAllAsRead}
                  >
                    全部已读
                  </button>
                )}
              </div>
              
              <div style={styles.notificationsList}>
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    style={{
                      ...styles.notificationItem,
                      backgroundColor: selectedNotificationIds.has(notification.id)
                        ? '#e2e8f0'
                        : notification.isRead ? '#ffffff' : '#fef3c7',
                      borderLeftColor: notification.isRead ? '#e2e8f0' : '#f59e0b'
                    }}
                  >
                    <button
                      style={styles.checkboxButton}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleNotificationSelection(notification.id);
                      }}
                    >
                      {selectedNotificationIds.has(notification.id) ? (
                        <CheckSquare size={20} color="#333333" fill="#333333" />
                      ) : (
                        <Square size={20} color="#94a3b8" />
                      )}
                    </button>
                    
                    <div 
                      style={styles.notificationMain}
                      onClick={() => handleNotificationClick(notification)}
                    >
                      <div style={{ ...styles.notificationIcon, backgroundColor: getIconBgColor(notification.type) }}>
                        {getNotificationIcon(notification.type)}
                      </div>

                      <div style={styles.notificationContent}>
                        <p style={styles.notificationText}>{notification.content}</p>
                        <div style={styles.notificationMeta}>
                          <span style={styles.notificationTime}>
                            <Clock size={12} />
                            {formatTime(notification.createdAt)}
                          </span>
                        </div>
                      </div>

                      <div style={styles.notificationActions}>
                        {notification.postId && (
                          <button 
                            style={styles.navigateButton}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ArrowRight size={14} />
                            <span>查看</span>
                          </button>
                        )}
                        <button
                          style={styles.deleteButton}
                          onClick={(e) => handleDeleteNotification(e, notification.id)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      ) : (
        <div style={styles.chatContainer}>
          <div style={styles.conversationList}>
            {loading ? (
              <div style={styles.loading}>
                <div style={styles.spinner}></div>
                <span>加载中...</span>
              </div>
            ) : conversations.length === 0 ? (
              <div style={styles.emptyState}>
                <MessageSquare size={48} color="#94a3b8" />
                <p>暂无聊天</p>
                <p style={styles.emptyDesc}>当有人回复你时，你们的对话会显示在这里</p>
              </div>
            ) : (
              <div style={styles.conversationsList}>
                {conversations.map((conversation) => (
                  <div
                    key={conversation.id}
                    style={{
                      ...styles.conversationItem,
                      backgroundColor: selectedConversation?.id === conversation.id ? '#f1f5f9' : '#ffffff'
                    }}
                    onClick={() => fetchMessages(conversation)}
                  >
                    <div style={styles.avatarContainer}>
                      <button
                        style={{
                          ...styles.avatar,
                          ...(getAvatarUrl(conversation.otherUser.avatarUrl) ? {
                            backgroundImage: `url(${getAvatarUrl(conversation.otherUser.avatarUrl)})`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                          } : {})
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/user/${conversation.otherUserId}`);
                        }}
                      >
                        {!getAvatarUrl(conversation.otherUser.avatarUrl) && (
                          (conversation.otherUser.displayName?.charAt(0) || conversation.otherUser.username.charAt(0)).toUpperCase()
                        )}
                      </button>
                      {conversation.unreadCount > 0 && (
                        <div style={styles.unreadBadge}>
                          {conversation.unreadCount}
                        </div>
                      )}
                    </div>

                    <div style={styles.conversationInfo}>
                      <div style={styles.conversationHeader}>
                        <span style={styles.conversationName}>
                          {conversation.otherUser.displayName || conversation.otherUser.username}
                        </span>
                        {conversation.lastMessageTime && (
                          <span style={styles.conversationTime}>
                            {formatTime(conversation.lastMessageTime)}
                          </span>
                        )}
                      </div>
                      <p style={styles.conversationLastMessage}>
                        {conversation.lastMessage || '开始聊天吧'}
                      </p>
                      {!conversation.isMutualFollow && (
                        <p style={styles.limitMessage}>
                          {conversation.messageLimit}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={styles.chatArea}>
            {!selectedConversation ? (
              <div style={styles.noChatSelected}>
                <MessageSquare size={64} color="#cbd5e1" />
                <p>选择一个会话开始聊天</p>
              </div>
            ) : (
              <>
                <div style={styles.chatHeader}>
                  <div style={styles.chatHeaderInfo}>
                    <button
                      style={{
                        ...styles.chatAvatar,
                        ...(getAvatarUrl(selectedConversation.otherUser.avatarUrl) ? {
                          backgroundImage: `url(${getAvatarUrl(selectedConversation.otherUser.avatarUrl)})`,
                          backgroundSize: 'cover',
                          backgroundPosition: 'center',
                        } : {})
                      }}
                      onClick={() => navigate(`/user/${selectedConversation.otherUserId}`)}
                    >
                      {!getAvatarUrl(selectedConversation.otherUser.avatarUrl) && (
                        (selectedConversation.otherUser.displayName?.charAt(0) || selectedConversation.otherUser.username.charAt(0)).toUpperCase()
                      )}
                    </button>
                    <div style={styles.chatUserInfo}>
                      <span style={styles.chatUserName}>
                        {selectedConversation.otherUser.displayName || selectedConversation.otherUser.username}
                      </span>
                      <span style={styles.mutualFollowText}>
                        {selectedConversation.isMutualFollow ? '已互相关注' : '未互关'}
                      </span>
                    </div>
                  </div>
                </div>

                <div style={styles.messagesArea}>
                  {chatLoading ? (
                    <div style={styles.loading}>
                      <div style={styles.spinner}></div>
                      <span>加载中...</span>
                    </div>
                  ) : (
                    <>
                      {messages.map((message) => (
                        message.isSystemMessage ? (
                          <div key={message.id} style={styles.systemMessage}>
                            <p>{message.content}</p>
                          </div>
                        ) : (
                          <div
                            key={message.id}
                            style={{
                              ...styles.message,
                              justifyContent: message.senderId === selectedConversation.otherUserId ? 'flex-start' : 'flex-end'
                            }}
                          >
                            <div
                              style={{
                                ...styles.messageBubble,
                                backgroundColor: message.senderId === selectedConversation.otherUserId ? '#ffffff' : '#333333',
                                color: message.senderId === selectedConversation.otherUserId ? '#0f172a' : '#ffffff',
                              }}
                            >
                              {message.content && <p style={styles.messageText}>{message.content}</p>}
                              
                              {/* 分享的计划 */}
                              {message.sharedPlan && (
                                <div 
                                  style={styles.sharedContent}
                                  onClick={() => navigate(`/plan/${message.sharedPlanId}`)}
                                >
                                  <div style={styles.sharedIcon}>📋</div>
                                  <div style={styles.sharedInfo}>
                                    <span style={styles.sharedTitle}>{message.sharedPlan.title}</span>
                                    {message.sharedPlan.description && (
                                      <span style={styles.sharedDesc}>
                                        {message.sharedPlan.description.length > 50 
                                          ? message.sharedPlan.description.substring(0, 50) + '...' 
                                          : message.sharedPlan.description}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                              
                              {/* 分享的帖子 */}
                              {message.sharedPost && (
                                <div 
                                  style={styles.sharedContent}
                                  onClick={() => navigate(`/post/${message.sharedPostId}`)}
                                >
                                  <div style={styles.sharedIcon}>💬</div>
                                  <div style={styles.sharedInfo}>
                                    <span style={styles.sharedTitle}>
                                      {message.sharedPost.content.length > 30 
                                        ? message.sharedPost.content.substring(0, 30) + '...' 
                                        : message.sharedPost.content}
                                    </span>
                                    {message.sharedPost.user && (
                                      <span style={styles.sharedUser}>
                                        @{message.sharedPost.user.displayName || message.sharedPost.user.username}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                              
                              <span style={styles.messageTime}>
                                {formatTime(message.createdAt)}
                              </span>
                            </div>
                          </div>
                        )
                      ))}
                      <div ref={messagesEndRef} />
                    </>
                  )}
                </div>

                <div style={styles.inputArea}>
                  {!selectedConversation.canSend ? (
                    <div style={styles.disabledInput}>
                      <p style={styles.disabledText}>
                        {selectedConversation.messageLimit}
                      </p>
                    </div>
                  ) : (
                    <>
                      <input
                        type="text"
                        value={messageInput}
                        onChange={(e) => setMessageInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        placeholder="输入消息..."
                        style={styles.chatInput}
                      />
                      <button
                        onClick={handleSendMessage}
                        disabled={!messageInput.trim()}
                        style={{
                          ...styles.sendButton,
                          opacity: !messageInput.trim() ? 0.5 : 1
                        }}
                      >
                        <Send size={18} />
                      </button>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '24px',
    minHeight: '100vh',
    backgroundColor: '#f8fafc',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  title: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#0f172a',
  },
  tabContainer: {
    display: 'flex',
    gap: '8px',
    marginBottom: '24px',
    borderBottom: '1px solid #e2e8f0',
    paddingBottom: '8px',
  },
  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 20px',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: '8px',
    color: '#64748b',
    fontSize: '15px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  tabActive: {
    backgroundColor: '#ffffff',
    color: '#333333',
    fontWeight: 'bold',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  tabContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    position: 'relative',
  },
  tabBadge: {
    position: 'absolute',
    top: '-6px',
    right: '-12px',
    backgroundColor: '#ef4444',
    color: '#ffffff',
    fontSize: '11px',
    fontWeight: 'bold',
    minWidth: '18px',
    height: '18px',
    borderRadius: '9px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 4px',
  },
  contentArea: {
    minHeight: '500px',
  },
  batchActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 0',
    marginBottom: '16px',
  },
  selectAllButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#374151',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  actionButtons: {
    display: 'flex',
    gap: '8px',
  },
  actionButton: {
    padding: '8px 16px',
    backgroundColor: '#333333',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#ffffff',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  deleteActionButton: {
    backgroundColor: '#ef4444',
  },
  notificationItem: {
    display: 'flex',
    gap: '12px',
    padding: '16px',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    borderLeft: '4px solid #e2e8f0',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.04)',
  },
  checkboxButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: '4px',
  },
  notificationMain: {
    display: 'flex',
    flex: 1,
    gap: '16px',
  },
  chatContainer: {
    display: 'flex',
    gap: '16px',
    height: '70vh',
    minHeight: '600px',
  },
  conversationList: {
    width: '320px',
    background: '#ffffff',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    overflow: 'hidden',
  },
  chatArea: {
    flex: 1,
    background: '#ffffff',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 0',
    gap: '16px',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid #e2e8f0',
    borderTopColor: '#333333',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    gap: '12px',
    color: '#64748b',
    textAlign: 'center',
  },
  emptyDesc: {
    fontSize: '14px',
    color: '#94a3b8',
    marginTop: '4px',
  },
  notificationsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  notificationIcon: {
    width: '40px',
    height: '40px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  notificationContent: {
    flex: 1,
    minWidth: 0,
  },
  notificationText: {
    fontSize: '15px',
    color: '#0f172a',
    marginBottom: '8px',
    lineHeight: '1.5',
  },
  notificationMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  notificationTime: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    color: '#94a3b8',
  },
  notificationActions: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    alignItems: 'flex-end',
  },
  navigateButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    background: '#f1f5f9',
    border: 'none',
    borderRadius: '6px',
    color: '#333333',
    fontSize: '12px',
    cursor: 'pointer',
  },
  deleteButton: {
    padding: '6px',
    background: 'none',
    border: 'none',
    borderRadius: '6px',
    color: '#94a3b8',
    cursor: 'pointer',
    transition: 'color 0.2s ease',
  },
  conversationsList: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflowY: 'auto',
  },
  conversationItem: {
    display: 'flex',
    gap: '12px',
    padding: '16px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    borderBottom: '1px solid #f1f5f9',
  },
  avatarContainer: {
    position: 'relative',
    flexShrink: 0,
  },
  avatar: {
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    backgroundColor: '#e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#64748b',
    border: 'none',
    cursor: 'pointer',
    padding: 0,
  },
  unreadBadge: {
    position: 'absolute',
    top: '-4px',
    right: '-4px',
    backgroundColor: '#ef4444',
    color: '#ffffff',
    fontSize: '12px',
    fontWeight: 'bold',
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  conversationInfo: {
    flex: 1,
    minWidth: 0,
  },
  conversationHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
  },
  conversationName: {
    fontSize: '15px',
    fontWeight: 'bold',
    color: '#0f172a',
  },
  conversationTime: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  conversationLastMessage: {
    fontSize: '14px',
    color: '#64748b',
    margin: 0,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  limitMessage: {
    fontSize: '12px',
    color: '#f59e0b',
    margin: '4px 0 0 0',
  },
  noChatSelected: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#94a3b8',
    gap: '12px',
  },
  chatHeader: {
    padding: '16px 20px',
    borderBottom: '1px solid #e2e8f0',
    backgroundColor: '#ffffff',
  },
  chatHeaderInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  chatAvatar: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    backgroundColor: '#e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#64748b',
    border: 'none',
    cursor: 'pointer',
    padding: 0,
  },
  chatUserInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  chatUserName: {
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#0f172a',
  },
  mutualFollowText: {
    fontSize: '12px',
    color: '#64748b',
  },
  messagesArea: {
    flex: 1,
    padding: '20px',
    overflowY: 'auto',
    backgroundColor: '#f8fafc',
  },
  systemMessage: {
    display: 'flex',
    justifyContent: 'center',
    margin: '12px 0',
  },
  systemMessageBubble: {
    backgroundColor: '#f1f5f9',
    padding: '8px 16px',
    borderRadius: '16px',
    color: '#64748b',
    fontSize: '13px',
  },
  message: {
    display: 'flex',
    marginBottom: '12px',
  },
  messageBubble: {
    maxWidth: '70%',
    padding: '10px 14px',
    borderRadius: '16px',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)',
  },
  messageText: {
    fontSize: '15px',
    margin: 0,
    marginBottom: '4px',
    lineHeight: '1.5',
  },
  messageTime: {
    fontSize: '11px',
    opacity: 0.7,
  },
  inputArea: {
    display: 'flex',
    gap: '12px',
    padding: '16px 20px',
    borderTop: '1px solid #e2e8f0',
    backgroundColor: '#ffffff',
  },
  chatInput: {
    flex: 1,
    padding: '12px 16px',
    border: '1px solid #e2e8f0',
    borderRadius: '24px',
    fontSize: '15px',
    outline: 'none',
    transition: 'border-color 0.2s ease',
  },
  sendButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '44px',
    height: '44px',
    backgroundColor: '#333333',
    border: 'none',
    borderRadius: '50%',
    color: '#ffffff',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  disabledInput: {
    flex: 1,
    padding: '16px',
    backgroundColor: '#f1f5f9',
    borderRadius: '8px',
  },
  disabledText: {
    margin: 0,
    fontSize: '14px',
    color: '#64748b',
    textAlign: 'center',
  },
  sharedContent: {
    display: 'flex',
    gap: '12px',
    padding: '12px',
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    borderRadius: '8px',
    cursor: 'pointer',
    marginTop: '8px',
    transition: 'background-color 0.2s ease',
  },
  sharedIcon: {
    fontSize: '24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sharedInfo: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  sharedTitle: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '2px',
  },
  sharedDesc: {
    fontSize: '12px',
    opacity: 0.8,
  },
  sharedUser: {
    fontSize: '12px',
    opacity: 0.7,
  },
};

export default Notifications;
