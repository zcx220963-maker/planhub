import React, { useState, useEffect } from 'react';
import { Search as SearchIcon, Users, ClipboardList, Hash, ArrowRight, X } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { searchApi, postApi } from '../services/api';
import type { SearchResponse, SearchUserResult, SearchPostResult, SearchPlanResult } from '../types';

const Search: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [trendingTopics, setTrendingTopics] = useState<string[]>([]);

  const getAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return `http://localhost:8080/${avatarUrl}`;
  };

  useEffect(() => {
    const q = searchParams.get('q');
    const type = searchParams.get('type');
    if (q) {
      setSearchTerm(q);
    }
    if (type && ['all', 'posts', 'plans', 'users', 'topics'].includes(type)) {
      setActiveTab(type);
    }
  }, []);

  useEffect(() => {
    if (searchTerm.trim()) {
      performSearch();
    } else {
      setSearchResults(null);
    }
  }, [searchTerm, activeTab]);

  useEffect(() => {
    if (searchTerm.trim()) {
      setSearchParams({ q: searchTerm, type: activeTab });
    } else {
      setSearchParams({});
    }
  }, [searchTerm, activeTab, setSearchParams]);

  useEffect(() => {
    loadTrendingTopics();
  }, []);

  const loadTrendingTopics = async () => {
    try {
      const data = await postApi.getTrendingHashtags();
      if (data.length > 0) {
        setTrendingTopics(data.map(t => t.replace('#', '')));
      } else {
        setTrendingTopics(['年度计划', '学习计划', '健身计划', '旅行计划', '工作计划']);
      }
    } catch {
      setTrendingTopics(['年度计划', '学习计划', '健身计划', '旅行计划', '工作计划']);
    }
  };

  const performSearch = async () => {
    setLoading(true);
    try {
      const results = await searchApi.search(searchTerm, activeTab);
      setSearchResults(results);
    } catch (error) {
      console.error('Search failed:', error);
      setSearchResults(null);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { key: 'all', label: '全部', icon: SearchIcon },
    { key: 'posts', label: '帖子', icon: ClipboardList },
    { key: 'plans', label: '计划', icon: ClipboardList },
    { key: 'users', label: '用户', icon: Users },
    { key: 'topics', label: '话题', icon: Hash },
  ];

  const renderUsers = (users: SearchUserResult[]) => {
    if (!users || users.length === 0) return null;
    
    return (
      <div style={styles.resultsSection}>
        <h3 style={styles.resultsTitle}>用户</h3>
        <div style={styles.resultsList}>
          {users.map((user) => (
            <div key={user.id} style={styles.resultItem} onClick={() => navigate(`/user/${user.id}`)}>
              <div 
                style={{
                  ...styles.userIcon,
                  ...(getAvatarUrl(user.avatarUrl) ? {
                    backgroundImage: `url(${getAvatarUrl(user.avatarUrl)})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                  } : {})
                }}
              >
                {!getAvatarUrl(user.avatarUrl) && (user.displayName?.charAt(0) || user.username.charAt(0) || 'U')}
              </div>
              <div style={styles.resultInfo}>
                <h4 
                  style={styles.resultTitle} 
                  onClick={() => navigate(`/user/${user.id}`)}
                >
                  {user.displayName || user.username}
                </h4>
                <p style={styles.resultDescription}>{user.description || 'PlanHub 用户'}</p>
              </div>
              <ArrowRight size={20} style={styles.resultArrow} />
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderPosts = (posts: SearchPostResult[]) => {
    if (!posts || posts.length === 0) return null;
    
    return (
      <div style={styles.resultsSection}>
        <h3 style={styles.resultsTitle}>帖子</h3>
        <div style={styles.resultsList}>
          {posts.map((post) => (
            <div key={post.id} style={styles.postResultItem} onClick={() => navigate(`/post/${post.id}`)}>
              <div 
                style={{
                  ...styles.userIcon,
                  width: '40px',
                  height: '40px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  ...(getAvatarUrl(post.avatarUrl) ? {
                    backgroundImage: `url(${getAvatarUrl(post.avatarUrl)})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                  } : {})
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  post.userId && navigate(`/user/${post.userId}`);
                }}
              >
                {!getAvatarUrl(post.avatarUrl) && (post.user?.charAt(0) || 'U')}
              </div>
              <div style={styles.resultInfo}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h4 
                    style={styles.resultTitle}
                    onClick={(e) => {
                      e.stopPropagation();
                      post.userId && navigate(`/user/${post.userId}`);
                    }}
                  >
                    {post.user || '用户'}
                  </h4>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>
                    {new Date(post.time).toLocaleDateString('zh-CN')}
                  </span>
                </div>
                <p style={styles.resultDescription}>{post.content}</p>
                {post.tags && post.tags.length > 0 && (
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
                    {post.tags.slice(0, 3).map((tag, index) => (
                      <span
                        key={index}
                        style={{
                          fontSize: '12px',
                          color: '#374151',
                          background: 'transparent',
                          border: '1px solid #e2e8f0',
                          padding: '4px 10px',
                          borderRadius: '12px',
                          cursor: 'pointer',
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/hashtag/${tag}`);
                        }}
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <ArrowRight size={20} style={styles.resultArrow} />
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderPlans = (plans: SearchPlanResult[]) => {
    if (!plans || plans.length === 0) return null;
    
    return (
      <div style={styles.resultsSection}>
        <h3 style={styles.resultsTitle}>计划</h3>
        <div style={styles.resultsList}>
          {plans.map((plan) => (
            <div key={plan.id} style={styles.resultItem} onClick={() => navigate(`/plan/${plan.id}`)}>
              <div style={styles.resultIcon}>
                <ClipboardList size={20} />
              </div>
              <div style={styles.resultInfo}>
                <h4 style={styles.resultTitle}>{plan.title}</h4>
                <p style={styles.resultDescription}>{plan.description || ''}</p>
                {plan.user?.name && (
                  <p style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                    by <span 
                      style={{ cursor: 'pointer', color: '#667eea' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        plan.userId && navigate(`/user/${plan.userId}`);
                      }}
                    >
                      {plan.user.name}
                    </span>
                  </p>
                )}
              </div>
              <ArrowRight size={20} style={styles.resultArrow} />
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderTopics = (topics: string[]) => {
    if (!topics || topics.length === 0) return null;
    
    return (
      <div style={styles.resultsSection}>
        <h3 style={styles.resultsTitle}>话题</h3>
        <div style={styles.tagsList}>
          {topics.map((tag, index) => (
            <button
              key={index}
              style={styles.tagItem}
              onClick={() => navigate(`/hashtag/${tag}`)}
            >
              <Hash size={16} />
              <span>{tag}</span>
            </button>
          ))}
        </div>
      </div>
    );
  };

  const getResults = () => {
    if (!searchResults) {
      return (
        <div style={styles.noResults}>
          <p>暂无搜索结果</p>
        </div>
      );
    }

    const content = [];

    if (activeTab === 'all' || activeTab === 'users') {
      content.push(renderUsers(searchResults.users));
    }
    if (activeTab === 'all' || activeTab === 'posts') {
      content.push(renderPosts(searchResults.posts));
    }
    if (activeTab === 'all' || activeTab === 'plans') {
      content.push(renderPlans(searchResults.plans));
    }
    if (activeTab === 'all' || activeTab === 'topics') {
      content.push(renderTopics(searchResults.topics));
    }

    const hasResults = content.some(section => section !== null);
    if (!hasResults) {
      return (
        <div style={styles.noResults}>
          <p>暂无搜索结果</p>
        </div>
      );
    }

    return content;
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>搜索</h1>
        <p style={styles.subtitle}>查找计划、帖子、用户和话题</p>
      </div>

      <div style={styles.searchBox}>
        <SearchIcon size={20} style={styles.searchIcon} />
        <input
          type="text"
          placeholder="输入关键词搜索..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={styles.searchInput}
        />
        {searchTerm && (
          <button style={styles.clearButton} onClick={() => setSearchTerm('')}>
            <X size={18} />
          </button>
        )}
      </div>

      <div style={styles.tabsContainer}>
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                ...styles.tabButton,
                ...(activeTab === tab.key ? styles.tabButtonActive : {}),
              }}
            >
              <Icon size={18} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {loading ? (
        <div style={styles.loading}>搜索中...</div>
      ) : searchTerm.trim() ? (
        getResults()
      ) : (
        <div style={styles.popularSection}>
          <h3 style={styles.popularTitle}>热门搜索</h3>
          <div style={styles.popularTags}>
            {trendingTopics.map((topic, index) => (
              <button
                key={index}
                onClick={() => setSearchTerm(topic)}
                style={styles.popularTag}
              >
                <Hash size={16} />
                <span>{topic}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100%',
  },
  header: {
    marginBottom: '24px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '8px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#64748b',
  },
  searchBox: {
    position: 'relative',
    marginBottom: '24px',
  },
  searchIcon: {
    position: 'absolute',
    left: '20px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: '#64748b',
  },
  searchInput: {
    width: '100%',
    padding: '18px 20px 18px 56px',
    border: '1px solid #e2e8f0',
    borderRadius: '14px',
    fontSize: '16px',
    background: 'white',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
  },
  clearButton: {
    position: 'absolute',
    right: '16px',
    top: '50%',
    transform: 'translateY(-50%)',
    background: '#333333',
    border: 'none',
    borderRadius: '50%',
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#ffffff',
    cursor: 'pointer',
  },
  tabsContainer: {
    display: 'flex',
    gap: '12px',
    marginBottom: '24px',
  },
  tabButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 20px',
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    fontSize: '15px',
    color: '#333333',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  tabButtonActive: {
    background: '#333333',
    borderColor: '#333333',
    color: '#ffffff',
  },
  loading: {
    textAlign: 'center',
    padding: '40px',
    color: '#64748b',
  },
  resultsSection: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
    marginBottom: '24px',
  },
  resultsTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '20px',
  },
  resultsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  resultItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  postResultItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '16px',
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  resultIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#e2e8f0',
    color: '#475569',
  },
  userIcon: {
    width: '48px',
    height: '48px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '18px',
    fontWeight: 'bold',
  },
  resultInfo: {
    flex: 1,
  },
  resultTitle: {
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '4px',
  },
  resultDescription: {
    fontSize: '14px',
    color: '#64748b',
    marginBottom: '4px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  resultArrow: {
    color: '#64748b',
  },
  noResults: {
    textAlign: 'center',
    padding: '40px',
    background: 'white',
    borderRadius: '16px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
    color: '#64748b',
  },
  tagsList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
  },
  tagItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '20px',
    fontSize: '14px',
    color: '#374151',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  popularSection: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
  },
  popularTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '20px',
  },
  popularTags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
  },
  popularTag: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 20px',
    background: '#f1f5f9',
    border: 'none',
    borderRadius: '25px',
    fontSize: '15px',
    color: '#0f172a',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
};

export default Search;
